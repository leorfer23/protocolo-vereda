#!/usr/bin/env python3
"""Prueba que la propia verificación de firmas de conformidad.nivel_a (JCS +
Ed25519 + historial de claves) es correcta, contra los mismos vectores
publicados y reproducibles que ya usa `validar.py` -- antes de usarla para
juzgar a un nodo ajeno. Es exactamente el punto del diseño: "usar los
vectores de firma para validar la criptografía de la propia suite".

No pega por red: la clave del firmante se arma a mano a partir de la
`clave_publica` del vector, sin llamar a `_claves_de`.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)

from conformidad.nivel_a import NivelA  # noqa: E402


def main():
    vectores = json.load(open(os.path.join(BASE, "ejemplos", "vectores-firma.json")))
    vector = next(v for v in vectores["vectores"] if v["nombre"] == "resena-firmada")
    reseña = vector["objeto_firmado"]
    firma = reseña["firma"]

    n = NivelA("https://esto-no-se-consulta.invalid")  # no hace red: el cache ya trae la clave
    cache = {firma["firmante"]: [{"clave_publica": firma["clave_publica"], "desde": "2020-01-01T00:00:00Z", "estado": "activa"}]}

    ok, motivo = n._verificar_firma(reseña, cache)
    assert ok, f"la reseña firmada del vector publicado debería verificar: {motivo}"
    print(f"✓ {vector['nombre']}: verifica contra el historial de claves de {firma['firmante']}")

    alterada = json.loads(json.dumps(reseña))
    alterada["puntaje"] = 1  # cambia el objeto sin tocar la firma
    ok2, motivo2 = n._verificar_firma(alterada, cache)
    assert not ok2, "una firma no puede seguir valiendo si se altera el objeto"
    print(f"✓ objeto alterado sin volver a firmar: {motivo2}")

    cache_sin_esa_clave = {firma["firmante"]: [{"clave_publica": "distinta", "desde": "2020-01-01T00:00:00Z", "estado": "activa"}]}
    ok3, motivo3 = n._verificar_firma(reseña, cache_sin_esa_clave)
    assert not ok3, "una clave que no está en el historial no puede verificar"
    print(f"✓ clave ausente del historial: {motivo3}")

    print("\nla verificación de firmas de conformidad.nivel_a reproduce el vector publicado.")


if __name__ == "__main__":
    main()
