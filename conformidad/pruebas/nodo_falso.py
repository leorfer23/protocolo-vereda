#!/usr/bin/env python3
"""Un nodo que no es Vereda, a propósito: sirve por HTTP en localhost para
probar que el nivel A no se rompe con lo que le llegue. No es parte de
validar.py ni corre en CI; es la evidencia manual de que pide el PR de
`conformidad/`: "corré el nivel A contra algo real aunque falle todo".

Uso:
    python3 conformidad/pruebas/nodo_falso.py [puerto]
    # en otra terminal:
    python3 -m conformidad http://127.0.0.1:<puerto>

Cada ruta rompe una cosa distinta a propósito:
- /.well-known/vereda.json: 200 pero el cuerpo no es JSON, y sin ETag/Cache-Control.
- /v1/comercios: cabeceras de caché presentes pero la revalidación no funciona
  (siempre 200, nunca 304), y al comercio le falta 'ubicacion' (esquema roto).
- /v1/buscar: cabeceras y revalidación correctas, pero el cuerpo es un objeto
  donde tendría que ser un array.
- /v1/rondas: cuerpo válido (array vacío) pero sin ninguna cabecera de caché.
- /v1/comercios/{id}: 404 en vez del 200 que le tocaba.
- /v1/comercios/{id}/ofertas: todo bien salvo que a la oferta le falta 'disponible'.
- /v1/comercios/{id}/promociones: todo bien (para tener también casos en verde).
- /v1/catalogo/{ean real}: 200 con Content-Type JSON pero cuerpo truncado (no parsea).
- /v1/catalogo/0000000000000: 404 con esquemas/error.json, como corresponde.
- /v1/actores/{identidad}/claves: todo bien.
- /v1/actores/.../claves para la identidad inexistente: 404 con esquemas/error.json.
- /v1/actores/{identidad}/mudanza: 404 (no se mudó), el caso esperable.
- /v1/actores/{identidad}/resenas: una reseña bien formada mas una firma que
  no verifica (no es una firma real -- eso se prueba aparte, contra los
  vectores publicados, en verificar_firma_con_vectores.py).

POST /v1/federacion/entrantes (para el nivel C) SÍ verifica de verdad: RFC
9421 completo (Content-Digest, base de firma, Ed25519) contra la identidad
de prueba de nodo.rosario.coop (ejemplos/vectores-firma.json), idempotencia
y orden de secuencia con estado en memoria. Y rompe tres cosas puntuales,
una por chequeo del nivel C:
- no verifica 'firma_nodo' (adentro del evento) -- solo la firma HTTP del
  transporte. Un evento con firma_nodo corrupta pero transporte válido se
  acepta igual (defecto nº1).
- un mismo id con otro contenido lo pisa en silencio con 202 en vez de
  responder 409 (defecto nº2).
- 400 version_no_soportada sin 'detalle.versiones' (defecto nº3).
"""
import base64
import hashlib
import json
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

IDENTIDAD = "verduleria-falsa.conformidad"
EAN_REAL = "7790000000001"
COMERCIO_ID = "01920000-0000-7000-8000-00000000c001"

COMERCIO_ROTO = {
    # a propósito le falta 'ubicacion', 'modalidades', 'politica_cancelacion',
    # 'verificacion' y 'reputacion': todos requeridos por esquemas/comercio.json.
    "id": COMERCIO_ID, "nodo": "127.0.0.1", "creado": "2026-01-01T00:00:00-03:00",
    "actualizado": "2026-01-01T00:00:00-03:00", "version_esquema": "1.0",
    "identidad": IDENTIDAD, "nombre": "Verdulería falsa", "tipo": "verduleria",
}

OFERTA_ROTA = {
    # a propósito le falta 'disponible', requerido por esquemas/oferta.json.
    "id": "01920000-0000-7000-8000-00000000o001", "nodo": "127.0.0.1", "creado": "2026-01-01T00:00:00-03:00",
    "actualizado": "2026-01-01T00:00:00-03:00", "version_esquema": "1.0",
    "comercio_id": COMERCIO_ID, "tipo": "producto", "nombre": "Tomate",
    "precio": {"modo": "fijo", "centavos": 100000, "moneda": "ARS"},
    "cantidad": {"valor": 1, "unidad": "kg"}, "ean": EAN_REAL,
}

RESENA_MAL_FIRMADA = {
    "id": "01920000-0000-7000-8000-00000000r001", "nodo": "127.0.0.1", "creado": "2026-01-01T00:00:00-03:00",
    "actualizado": "2026-01-01T00:00:00-03:00", "version_esquema": "1.0",
    "pedido_id": "01920000-0000-7000-8000-00000000p001",
    "autor": f"cliente@{IDENTIDAD}", "destinatario": IDENTIDAD, "rol_autor": "usuario", "puntaje": 5,
    "texto": "Reseña de prueba del nodo falso: la firma de abajo NO es real.",
    "firma": {"firmante": f"cliente@{IDENTIDAD}", "clave_publica": "A" * 43, "valor": "B" * 86, "instante": "2026-01-01T00:00:00-03:00"},
}

CLAVES = [{"clave_publica": "C" * 43, "desde": "2026-01-01T00:00:00-03:00", "estado": "activa"}]

ERROR_EAN = {"codigo": "ean_no_encontrado", "mensaje": "Este nodo no tiene ese EAN.", "estado_http": 404}
ERROR_ACTOR = {"codigo": "actor_desconocido", "mensaje": "Este nodo no conoce ese actor.", "estado_http": 404}

# nodo.rosario.coop, ejemplos/vectores-firma.json -- la única identidad de
# federación que este nodo falso confía, a propósito, para poder probar el
# nivel C sin que nadie tenga que entregarle nada.
CLAVE_PUBLICA_CONFIABLE = "xGDj8g3W0IIBhvwEl78mOEMl-2szOTnTrDzTDLfvbqw"
VERSIONES_SOPORTADAS = ["1.0"]

_eventos_vistos = {}    # id de evento -> cuerpo (bytes) ya aplicado
_ultima_secuencia = {}  # id de entidad -> última secuencia aceptada


def _desde_b64u(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _parsear_signature_input(valor):
    """'sig1=("@method" ...);created=...;keyid="...";alg="..."' -> (etiqueta,
    lista de componentes, el resto tal cual -- eso es lo que va después de
    '"@signature-params": ' en la base de firma, sin reformatearlo)."""
    etiqueta, resto = valor.split("=", 1)
    componentes = re.findall(r'"([^"]+)"', resto.split(")", 1)[0])
    return etiqueta, componentes, resto


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("nodo-falso: " + (fmt % args) + "\n")

    def _enviar(self, estado, cuerpo=None, cabeceras=None, content_type="application/json"):
        self.send_response(estado)
        self.send_header("Content-Type", content_type)
        for k, v in (cabeceras or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if cuerpo is not None:
            self.wfile.write(cuerpo if isinstance(cuerpo, bytes) else cuerpo.encode("utf-8"))

    def _json(self, estado, obj, cabeceras=None):
        self._enviar(estado, json.dumps(obj), cabeceras)

    def do_GET(self):
        p = self.path
        if p == "/.well-known/vereda.json":
            self._enviar(200, "<html>esto no es JSON</html>", content_type="text/html")
        elif p.startswith("/v1/comercios?") or p == "/v1/comercios":
            self._json(200, [COMERCIO_ROTO], {"ETag": '"comercios-v1"', "Cache-Control": "public, max-age=60"})
        elif p == f"/v1/comercios/{COMERCIO_ID}":
            self._json(404, {"codigo": "no_declarado", "mensaje": "esto ni siquiera debería pasar", "estado_http": 404})
        elif p == f"/v1/comercios/{COMERCIO_ID}/ofertas":
            self._responder_con_cache([OFERTA_ROTA], "ofertas-v1")
        elif p == f"/v1/comercios/{COMERCIO_ID}/promociones":
            self._responder_con_cache([], "promos-v1")
        elif p.startswith("/v1/buscar?") or p == "/v1/buscar":
            self._responder_con_cache({"esto": "debería ser un array, no un objeto"}, "buscar-v1")
        elif p.startswith("/v1/rondas?") or p == "/v1/rondas":
            self._json(200, [])  # sin ETag ni Cache-Control, a propósito
        elif p == f"/v1/catalogo/{EAN_REAL}":
            self._enviar(200, '{"esto": "no cierra')  # JSON truncado a propósito
        elif p == "/v1/catalogo/0000000000000":
            self._json(404, ERROR_EAN)
        elif p == f"/v1/actores/{IDENTIDAD}/claves":
            self._responder_con_cache(CLAVES, "claves-v1")
        elif p.startswith("/v1/actores/no-existe-conformidad") and p.endswith("/claves"):
            self._json(404, ERROR_ACTOR)
        elif p == f"/v1/actores/{IDENTIDAD}/mudanza":
            self._json(404, {"codigo": "no_mudado", "mensaje": "no se mudó", "estado_http": 404})
        elif p == f"/v1/actores/{IDENTIDAD}/resenas":
            self._responder_con_cache([RESENA_MAL_FIRMADA], "resenas-v1")
        else:
            self._json(404, {"codigo": "ruta_no_reconocida", "mensaje": f"el nodo falso no sirve {p}", "estado_http": 404})

    def _responder_con_cache(self, cuerpo, etag):
        if self.headers.get("If-None-Match") == f'"{etag}"':
            self._enviar(304, cabeceras={"ETag": f'"{etag}"', "Cache-Control": "public, max-age=60"})
        else:
            self._json(200, cuerpo, {"ETag": f'"{etag}"', "Cache-Control": "public, max-age=60"})

    def do_POST(self):
        if self.path != "/v1/federacion/entrantes":
            self._json(404, {"codigo": "ruta_no_reconocida", "mensaje": f"el nodo falso no sirve POST {self.path}", "estado_http": 404})
            return
        cuerpo = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        estado, obj = self._recibir_federacion(cuerpo)
        if obj is None:
            self._enviar(estado)
        else:
            self._json(estado, obj)

    def _recibir_federacion(self, cuerpo: bytes):
        sig_input = self.headers.get("Signature-Input")
        sig = self.headers.get("Signature")
        vereda_version = self.headers.get("Vereda-Version")
        content_type = self.headers.get("Content-Type")
        content_digest = self.headers.get("Content-Digest")
        if not all([sig_input, sig, vereda_version, content_type, content_digest]):
            return 401, {"codigo": "firma_invalida", "mensaje": "faltan cabeceras de firma HTTP", "estado_http": 401}

        digest_real = "sha-256=:" + base64.b64encode(hashlib.sha256(cuerpo).digest()).decode() + ":"
        if digest_real != content_digest:
            return 401, {"codigo": "firma_invalida", "mensaje": "Content-Digest no corresponde al cuerpo recibido", "estado_http": 401}

        etiqueta, componentes, resto = _parsear_signature_input(sig_input)
        m_keyid = re.search(r'keyid="([^"]+)"', resto)
        keyid = m_keyid.group(1) if m_keyid else None
        if keyid != CLAVE_PUBLICA_CONFIABLE:
            return 401, {"codigo": "clave_desconocida", "mensaje": "este nodo de prueba no confía en esa identidad", "estado_http": 401}

        valores = {
            "@method": "POST",
            "@target-uri": f"http://{self.headers.get('Host', '')}{self.path}",
            "content-digest": content_digest,
            "content-type": content_type,
            "vereda-version": vereda_version,
        }
        base = "\n".join([f'"{c}": {valores[c]}' for c in componentes] + [f'"@signature-params": {resto}'])
        m_sig = re.search(rf'{re.escape(etiqueta)}=:([^:]+):', sig)
        if not m_sig:
            return 401, {"codigo": "firma_invalida", "mensaje": "no se pudo leer la cabecera Signature", "estado_http": 401}
        try:
            Ed25519PublicKey.from_public_bytes(_desde_b64u(keyid)).verify(base64.b64decode(m_sig.group(1)), base.encode())
        except (InvalidSignature, ValueError):
            return 401, {"codigo": "firma_invalida", "mensaje": "la firma HTTP RFC 9421 no verifica", "estado_http": 401}

        # A PROPÓSITO no se verifica 'firma_nodo' (adentro del evento) acá --
        # defecto plantado nº1, que conformidad.nivel_c._firma_de_evento_invalida
        # tiene que detectar igual (esperando 401 y sin conseguirlo).
        try:
            evento = json.loads(cuerpo)
        except ValueError:
            return 401, {"codigo": "firma_invalida", "mensaje": "el cuerpo no es JSON", "estado_http": 401}

        if vereda_version not in VERSIONES_SOPORTADAS:
            # defecto plantado nº2: falta 'detalle.versiones', que sí exige openapi.yaml.
            return 400, {"codigo": "version_no_soportada", "mensaje": "versión no soportada por este nodo de prueba", "estado_http": 400}

        eid = evento.get("id")
        entidad_id = (evento.get("entidad") or {}).get("id")
        secuencia = evento.get("secuencia")

        if eid in _eventos_vistos:
            if _eventos_vistos[eid] == cuerpo:
                return 202, None
            # defecto plantado nº3: un mismo id con otro contenido tendría que
            # dar 409, y este nodo falso lo pisa en silencio con 202.
            _eventos_vistos[eid] = cuerpo
            return 202, None

        if entidad_id and secuencia is not None:
            anterior = _ultima_secuencia.get(entidad_id, 0)
            if secuencia > anterior + 1:
                return 409, {"codigo": "secuencia_fuera_de_orden", "mensaje": "salto de secuencia", "estado_http": 409, "detalle": {"ultima_secuencia": anterior}}
            _ultima_secuencia[entidad_id] = secuencia

        _eventos_vistos[eid] = cuerpo
        return 202, None


def main():
    puerto = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), Handler)
    print(f"nodo falso en http://127.0.0.1:{puerto} (Ctrl+C para parar)", file=sys.stderr)
    print(f"probalo con: python3 -m conformidad http://127.0.0.1:{puerto}", file=sys.stderr)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
