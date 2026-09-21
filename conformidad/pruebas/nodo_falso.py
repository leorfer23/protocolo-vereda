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
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

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
