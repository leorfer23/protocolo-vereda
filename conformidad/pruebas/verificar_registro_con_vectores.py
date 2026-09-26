#!/usr/bin/env python3
"""Prueba que el chequeo del registro público de conformidad.nivel_a aprueba la
cadena publicada en ejemplos/vectores-firma.json → registro y rechaza una
reescrita, antes de usarlo para juzgar a un nodo ajeno.

No pega por red: `_get` responde con el vector, partido en dos páginas.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)

from conformidad.cliente import Respuesta  # noqa: E402
from conformidad.nivel_a import NivelA  # noqa: E402

ORIGEN = "https://esto-no-se-consulta.invalid"


def nodo(pagina, clave_nodo):
    entradas = pagina["entradas"]

    def get(url, headers=None):
        if url.endswith("/.well-known/vereda.json"):
            return Respuesta(ok=True, estado=200, cabeceras={}, cuerpo={"clave_publica": clave_nodo}, cuerpo_es_json=True)
        if headers and "If-None-Match" in headers:
            return Respuesta(ok=True, estado=304, cabeceras={"ETag": '"e"', "Cache-Control": "public"}, cuerpo=None)
        desde = int(url.split("desde=")[1])
        parte = entradas[desde - 1:desde + 1]
        cuerpo = {"nodo": pagina["nodo"], "entradas": parte, "cabeza": pagina["cabeza"]}
        if desde + 1 < len(entradas):
            cuerpo["siguiente"] = desde + 2
        return Respuesta(ok=True, estado=200, cabeceras={"ETag": '"e"', "Cache-Control": "public"}, cuerpo=cuerpo, cuerpo_es_json=True)
    return get


def correr(pagina, clave_nodo):
    n = NivelA(ORIGEN)
    n._get = nodo(pagina, clave_nodo)
    n._registro()
    return [c for c in n.casos if c.categoria == "firmas"][0], n.casos


def main():
    V = json.load(open(os.path.join(BASE, "ejemplos", "vectores-firma.json")))
    pagina = V["registro"]["pagina"]
    clave_nodo = next(c["clave_publica"] for c in V["claves"] if c["actor"] == pagina["nodo"])

    caso, casos = correr(pagina, clave_nodo)
    malos = [c for c in casos if c.resultado == "fallo"]
    assert not malos and caso.resultado == "ok", f"la cadena publicada debería verificar: {[c.motivo for c in malos]}"
    print(f"✓ la cadena del vector verifica en dos páginas: {caso.evidencia}")

    reescrita = json.loads(json.dumps(pagina))
    reescrita["entradas"][0]["datos"]["motivo"] = "no_retirado"  # sigue cumpliendo el esquema: solo la cadena lo delata
    caso, _ = correr(reescrita, clave_nodo)
    assert caso.resultado == "fallo", "una entrada reescrita no puede pasar"
    print(f"✓ entrada reescrita: {caso.motivo}")

    caso, _ = correr(pagina, "otra-clave")
    assert caso.resultado == "fallo", "una cadena firmada con una clave que el nodo no publica no puede pasar"
    print(f"✓ clave que no es del nodo: {caso.motivo}")

    print("\nel chequeo del registro de conformidad.nivel_a reproduce el vector publicado.")


if __name__ == "__main__":
    main()
