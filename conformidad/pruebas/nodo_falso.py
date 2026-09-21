#!/usr/bin/env python3
"""Un nodo que no es Vereda, a propósito: sirve por HTTP en localhost para
probar que la suite no se rompe con lo que le llegue. No es parte de
validar.py ni corre en CI; es la evidencia manual de cada PR de
`conformidad/`: "corré la suite contra algo real aunque falle todo".

Uso:
    python3 conformidad/pruebas/nodo_falso.py [puerto]
    # en otra terminal:
    python3 -m conformidad http://127.0.0.1:<puerto> --nivel a
    python3 -m conformidad http://127.0.0.1:<puerto> --nivel b --sesion sesion-de-prueba --mandato mandato-de-prueba
    python3 -m conformidad http://127.0.0.1:<puerto> --nivel c

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

Para el nivel B hay una sesión de prueba fija (SESION_VALIDA) y un mandato
de prueba fijo (MANDATO_VALIDO, scopes 'armar' + 'pedir_semanal:5000') --
el nivel B nunca los genera solo, los recibe por flag, así que alguien
tiene que conocerlos: son estos. El ciclo carrito -> confirmar -> aceptar
-> listo -> entregar -> reseña, con efectivo y retiro (sin PSP ni
repartidor), funciona de punta a punta salvo cuatro roturas puntuales:
- 'listo' no chequea que todos los ítems estén resueltos (defecto nº1).
- el tope del mandato se calcula pero nunca se aplica: confirmar nunca
  responde 402 fuera_de_mandato (defecto nº2).
- POST /yo/claves/rotar acepta un token de mandato como si fuera de sesión
  -- openapi.yaml lo declara `security: [{sesion: []}]`, sin mandato, y
  este nodo falso no distingue de qué esquema vino el bearer (defecto nº3,
  el que más le importa a Leo).
- una reseña repetida para el mismo par pedido/autor/destinatario no
  responde 409: se acepta de nuevo (defecto nº4).
"""
import base64
import hashlib
import json
import os
import re
import sys
import time
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


# --- nivel B: sesión y mandato de prueba fijos, nunca generados solos -----
SESION_VALIDA = "sesion-de-prueba"
MANDATO_VALIDO = "mandato-de-prueba"
MANDATO_SCOPES = ["armar", "pedir_semanal:5000"]
USUARIO_IDENTIDAD = "cliente-de-prueba@nodo-falso.test"
COMERCIO_B_IDENTIDAD = "super-barrio-b@nodo-falso.test"

OFERTAS_B = {
    "01920000-0000-7000-8000-0000000000b1": {"nombre": "Pan casero", "centavos": 3000},
    "01920000-0000-7000-8000-0000000000b2": {"nombre": "Torta especial", "centavos": 4000},
}
OFERTA_B_BARATA, OFERTA_B_CARA = list(OFERTAS_B)

ERROR_NO_AUTENTICADO = {"codigo": "no_autenticado", "mensaje": "Falta un token válido.", "estado_http": 401}

_carritos = {}          # id -> {"items": [...], "modalidad": {...} | None}
_pedidos = {}           # id -> pedido.json-shaped dict, mutado en cada transición
_resenas_vistas = set()  # (pedido_id, autor, destinatario) -- se llena pero, a propósito, no se usa para bloquear
_mandatos_revocados = set()
_gasto_mandato = {}     # token -> centavos acumulados en "el período" (la corrida entera, no hay reloj de prueba)
_clave_actual = {"clave_publica": "clave-original-de-prueba", "desde": "2026-01-01T00:00:00-03:00", "estado": "activa"}


def _id_v7():
    ahora_ms = int(time.time() * 1000)
    b = bytearray(ahora_ms.to_bytes(6, "big") + os.urandom(10))
    b[6] = 0x70 | (b[6] & 0x0F)
    b[8] = 0x80 | (b[8] & 0x3F)
    h = b.hex()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def _instante():
    return time.strftime("%Y-%m-%dT%H:%M:%S-03:00", time.gmtime())


def _monto(centavos):
    return {"centavos": centavos, "moneda": "ARS"}


def _tope_de(scopes):
    for s in scopes:
        m = re.match(r"^pedir(?:_diario|_semanal|_mensual)?:(\d+)$", s)
        if m:
            return int(m.group(1))
    return None


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
            m = re.match(r"^/v1/pedidos/([^/]+)$", p)
            if m:
                estado, cuerpo = self._ver_pedido(self._actor(), m.group(1))
                self._json(estado, cuerpo)
                return
            self._json(404, {"codigo": "ruta_no_reconocida", "mensaje": f"el nodo falso no sirve {p}", "estado_http": 404})

    def _responder_con_cache(self, cuerpo, etag):
        if self.headers.get("If-None-Match") == f'"{etag}"':
            self._enviar(304, cabeceras={"ETag": f'"{etag}"', "Cache-Control": "public, max-age=60"})
        else:
            self._json(200, cuerpo, {"ETag": f'"{etag}"', "Cache-Control": "public, max-age=60"})

    def _actor(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[len("Bearer "):]
        if token == SESION_VALIDA:
            return {"tipo": "sesion", "identidad": USUARIO_IDENTIDAD}
        if token == MANDATO_VALIDO and token not in _mandatos_revocados:
            return {"tipo": "mandato", "token": token, "scopes": MANDATO_SCOPES, "identidad": USUARIO_IDENTIDAD}
        return None

    def _cuerpo(self):
        crudo = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            return json.loads(crudo) if crudo else {}
        except ValueError:
            return {}

    def do_POST(self):
        p = self.path
        actor = self._actor()
        if p == "/v1/federacion/entrantes":
            cuerpo = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            estado, obj = self._recibir_federacion(cuerpo)
            self._enviar(estado) if obj is None else self._json(estado, obj)
            return
        if p == "/v1/carritos":
            estado, obj = self._crear_carrito(actor, self._cuerpo())
        elif re.match(r"^/v1/carritos/[^/]+/items$", p):
            estado, obj = self._agregar_item(actor, p.split("/")[3], self._cuerpo())
        elif re.match(r"^/v1/carritos/[^/]+/confirmar$", p):
            estado, obj = self._confirmar_carrito(actor, p.split("/")[3])
        elif re.match(r"^/v1/pedidos/[^/]+/aceptar$", p):
            estado, obj = self._aceptar_pedido(actor, p.split("/")[3])
        elif re.match(r"^/v1/pedidos/[^/]+/listo$", p):
            estado, obj = self._marcar_listo(actor, p.split("/")[3])
        elif re.match(r"^/v1/pedidos/[^/]+/entregar$", p):
            estado, obj = self._entregar_pedido(actor, p.split("/")[3], self._cuerpo())
        elif p == "/v1/resenas":
            estado, obj = self._crear_resena(actor, self._cuerpo())
        elif re.match(r"^/v1/mandatos/[^/]+/revocar$", p):
            estado, obj = self._revocar_mandato(actor, p.split("/")[3])
        elif p == "/v1/yo/claves/rotar":
            estado, obj = self._rotar_clave(actor)
        else:
            estado, obj = 404, {"codigo": "ruta_no_reconocida", "mensaje": f"el nodo falso no sirve POST {p}", "estado_http": 404}
        self._enviar(estado) if obj is None else self._json(estado, obj)

    def do_PUT(self):
        p = self.path
        actor = self._actor()
        m = re.match(r"^/v1/carritos/([^/]+)/modalidad$", p)
        if m:
            estado, obj = self._elegir_modalidad(actor, m.group(1), self._cuerpo())
        else:
            estado, obj = 404, {"codigo": "ruta_no_reconocida", "mensaje": f"el nodo falso no sirve PUT {p}", "estado_http": 404}
        self._enviar(estado) if obj is None else self._json(estado, obj)

    def do_PATCH(self):
        p = self.path
        actor = self._actor()
        m = re.match(r"^/v1/pedidos/([^/]+)/items/([^/]+)$", p)
        if m:
            estado, obj = self._resolver_item(actor, m.group(1), m.group(2), self._cuerpo())
        else:
            estado, obj = 404, {"codigo": "ruta_no_reconocida", "mensaje": f"el nodo falso no sirve PATCH {p}", "estado_http": 404}
        self._enviar(estado) if obj is None else self._json(estado, obj)

    # -- nivel B: carrito -------------------------------------------------
    def _carrito_publico(self, carrito_id):
        c = _carritos[carrito_id]
        estado = "valido" if c["items"] and c["modalidad"] else "incompleto"
        return {
            "id": carrito_id, "estado": estado, "items": c["items"],
            "modalidad": c["modalidad"] or {"tipo": "retiro"}, "vence": _instante(),
        }

    def _crear_carrito(self, actor, cuerpo):
        if actor is None:
            return 401, ERROR_NO_AUTENTICADO
        carrito_id = _id_v7()
        _carritos[carrito_id] = {"items": [], "modalidad": None}
        return 201, self._carrito_publico(carrito_id)

    def _agregar_item(self, actor, carrito_id, cuerpo):
        if actor is None:
            return 401, ERROR_NO_AUTENTICADO
        if carrito_id not in _carritos:
            return 410, {"codigo": "carrito_vencido", "mensaje": "el carrito no existe o venció.", "estado_http": 410}
        oferta = OFERTAS_B.get(cuerpo.get("oferta_id"))
        if oferta is None:
            pub = self._carrito_publico(carrito_id)
            pub["estado"] = "no_disponible"
            return 200, pub
        item = {
            "id": _id_v7(), "oferta_id": cuerpo["oferta_id"], "nombre": oferta["nombre"],
            "cantidad": cuerpo.get("cantidad") or {"valor": 1, "unidad": "unidad"},
            "precio_unitario": _monto(oferta["centavos"]), "estado": "pendiente",
        }
        _carritos[carrito_id]["items"].append(item)
        return 200, self._carrito_publico(carrito_id)

    def _elegir_modalidad(self, actor, carrito_id, cuerpo):
        if actor is None:
            return 401, ERROR_NO_AUTENTICADO
        if carrito_id not in _carritos:
            return 410, {"codigo": "carrito_vencido", "mensaje": "el carrito no existe o venció.", "estado_http": 410}
        _carritos[carrito_id]["modalidad"] = cuerpo or {"tipo": "retiro"}
        return 200, self._carrito_publico(carrito_id)

    def _confirmar_carrito(self, actor, carrito_id):
        if actor is None:
            return 401, ERROR_NO_AUTENTICADO
        c = _carritos.get(carrito_id)
        if c is None:
            return 410, {"codigo": "carrito_vencido", "mensaje": "el carrito no existe o venció.", "estado_http": 410}
        total = sum(it["precio_unitario"]["centavos"] * it["cantidad"]["valor"] for it in c["items"])
        if actor["tipo"] == "mandato":
            tope = _tope_de(actor["scopes"])
            gasto_previo = _gasto_mandato.get(actor["token"], 0)
            # DEFECTO plantado nº2: se calcula gasto_previo + total contra el
            # tope, pero a propósito nunca se lo usa para rechazar. Un nodo
            # conforme respondería 402 fuera_de_mandato acá si se pasa.
            _gasto_mandato[actor["token"]] = gasto_previo + total
        pedido_id = _id_v7()
        ahora = _instante()
        pedido = {
            "id": pedido_id, "nodo": "127.0.0.1", "creado": ahora, "actualizado": ahora, "version_esquema": "1.0",
            "usuario": actor["identidad"], "comercio": COMERCIO_B_IDENTIDAD,
            "items": [dict(it) for it in c["items"]],
            "modalidad": c["modalidad"] or {"tipo": "retiro"},
            "estado": "creado",
            "historial": [{"estado": "creado", "instante": ahora, "actor": actor["identidad"]}],
            "totales": {"productos": _monto(total), "envio": _monto(0), "total": _monto(total)},
            "reparto": [{"destinatario": "comercio", "concepto": "productos", "monto": _monto(total)}],
            "via": {"canal": "agente" if actor["tipo"] == "mandato" else "app"},
            "codigo_retiro": "482913",
        }
        _pedidos[pedido_id] = pedido
        return 201, pedido

    # -- nivel B: pedido ----------------------------------------------------
    def _ver_pedido(self, actor, pedido_id):
        if actor is None:
            return 401, ERROR_NO_AUTENTICADO
        p = _pedidos.get(pedido_id)
        if p is None:
            return 404, {"codigo": "pedido_no_encontrado", "mensaje": "no existe ese pedido.", "estado_http": 404}
        return 200, p

    def _aceptar_pedido(self, actor, pedido_id):
        if actor is None:
            return 401, ERROR_NO_AUTENTICADO
        p = _pedidos.get(pedido_id)
        if p is None:
            return 404, {"codigo": "pedido_no_encontrado", "mensaje": "no existe ese pedido.", "estado_http": 404}
        p["estado"] = "aceptado"
        p["historial"].append({"estado": "aceptado", "instante": _instante(), "actor": COMERCIO_B_IDENTIDAD})
        return 200, None

    def _resolver_item(self, actor, pedido_id, item_id, cuerpo):
        if actor is None:
            return 401, ERROR_NO_AUTENTICADO
        p = _pedidos.get(pedido_id)
        if p is None:
            return 404, {"codigo": "pedido_no_encontrado", "mensaje": "no existe ese pedido.", "estado_http": 404}
        for it in p["items"]:
            if it["id"] == item_id:
                it["estado"] = cuerpo.get("estado", "confirmado")
        return 200, None

    def _marcar_listo(self, actor, pedido_id):
        if actor is None:
            return 401, ERROR_NO_AUTENTICADO
        p = _pedidos.get(pedido_id)
        if p is None:
            return 404, {"codigo": "pedido_no_encontrado", "mensaje": "no existe ese pedido.", "estado_http": 404}
        # DEFECTO plantado nº1: openapi.yaml exige 409 si queda algún ítem sin
        # resolver ("pendiente"); este nodo falso no lo comprueba.
        p["estado"] = "listo"
        p["historial"].append({"estado": "listo", "instante": _instante(), "actor": COMERCIO_B_IDENTIDAD})
        return 200, None

    def _entregar_pedido(self, actor, pedido_id, cuerpo):
        if actor is None:
            return 401, ERROR_NO_AUTENTICADO
        p = _pedidos.get(pedido_id)
        if p is None:
            return 404, {"codigo": "pedido_no_encontrado", "mensaje": "no existe ese pedido.", "estado_http": 404}
        if p["modalidad"].get("tipo") == "retiro" and cuerpo.get("codigo_retiro") != p.get("codigo_retiro"):
            return 422, {"codigo": "codigo_retiro_invalido", "mensaje": "el código de retiro no coincide.", "estado_http": 422}
        p["estado"] = "entregado"
        p["historial"].append({"estado": "entregado", "instante": _instante(), "actor": COMERCIO_B_IDENTIDAD})
        return 200, None

    def _crear_resena(self, actor, cuerpo):
        if actor is None:
            return 401, ERROR_NO_AUTENTICADO
        p = _pedidos.get(cuerpo.get("pedido_id"))
        if p is None or p.get("estado") != "entregado":
            return 409, {"codigo": "pedido_no_entregado", "mensaje": "solo se reseña un pedido entregado.", "estado_http": 409}
        # DEFECTO plantado nº4: debería ser 409 si (pedido_id, autor,
        # destinatario) ya se reseñó; se acepta de nuevo, a propósito.
        _resenas_vistas.add((cuerpo.get("pedido_id"), cuerpo.get("autor"), cuerpo.get("destinatario")))
        return 201, None

    # -- nivel B: mandato y claves -------------------------------------------
    def _revocar_mandato(self, actor, mandato_id):
        if actor is None or actor["tipo"] != "sesion":
            return 401, ERROR_NO_AUTENTICADO
        _mandatos_revocados.add(mandato_id)
        return 200, None

    def _rotar_clave(self, actor):
        if actor is None:
            return 401, ERROR_NO_AUTENTICADO
        # DEFECTO plantado nº3, el importante: openapi.yaml declara esta ruta
        # `security: [{sesion: []}]`, sin mandato. Un nodo conforme tiene que
        # rechazar un bearer de mandato acá aunque sea válido en otro lado.
        # Este nodo falso no distingue de qué esquema vino el token.
        _clave_actual["clave_publica"] = "clave-rotada-" + _id_v7()[:8]
        return 200, [dict(_clave_actual)]

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
