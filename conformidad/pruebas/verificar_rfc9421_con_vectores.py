#!/usr/bin/env python3
"""Prueba que conformidad.rfc9421 (la firma HTTP que usa el nivel C para
entregar eventos de federación) reproduce byte a byte el request firmado que
publica ejemplos/vectores-firma.json#/rfc9421 -- antes de usarla para armar
requests reales contra un nodo ajeno. Mismo espíritu que
verificar_firma_con_vectores.py, para la firma de transporte en vez de la de
los objetos.
"""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, BASE)

from conformidad import evento_federacion, rfc9421, vectores  # noqa: E402


def main():
    V = vectores.cargar(BASE)
    r = V["rfc9421"]
    clave_privada, clave_publica = vectores.clave_privada_de(V, "nodo.rosario.coop")
    assert clave_publica == r["keyid"], "el vector rfc9421 está firmado con otra clave que la que deriva vectores.py"

    ev = next(x for x in V["vectores"] if x["nombre"] == "evento-firmado-por-el-nodo")
    firmado, cuerpo_jcs = evento_federacion.firmar_evento(
        ev["objeto_sin_firma"], clave_privada=clave_privada, clave_publica_b64u=clave_publica, dominio_emisor="nodo.rosario.coop"
    )
    assert firmado == ev["objeto_firmado"], "conformidad.evento_federacion no reproduce el evento firmado publicado"
    assert cuerpo_jcs.hex() == r["cuerpo_utf8_hex"], "el cuerpo JCS del evento no coincide con el que firma el vector rfc9421"
    print("✓ conformidad.evento_federacion reproduce 'evento-firmado-por-el-nodo' y su JCS es el cuerpo que firma el vector rfc9421")

    assert cuerpo_jcs.hex() == r["cuerpo_utf8_hex"]  # ya probado arriba; lo reusamos en vez de recalcularlo
    digest = rfc9421.content_digest(cuerpo_jcs)
    assert digest == r["cabeceras"]["Content-Digest"], f"Content-Digest no coincide: {digest!r} != {r['cabeceras']['Content-Digest']!r}"
    print("✓ Content-Digest coincide con el publicado")

    base, params = rfc9421.base_de_firma(
        metodo=r["metodo"], url=r["url"], digest=digest,
        content_type=r["cabeceras"]["Content-Type"], vereda_version=r["cabeceras"]["Vereda-Version"],
        created=r["created"], keyid=r["keyid"],
    )
    assert base == r["base_de_firma"], "la base de firma reconstruida no coincide con la publicada"
    print("✓ base de firma coincide con la publicada")

    cabeceras = rfc9421.firmar_pedido(
        metodo=r["metodo"], url=r["url"], cuerpo=cuerpo_jcs,
        vereda_version=r["cabeceras"]["Vereda-Version"], clave_privada=clave_privada, keyid=r["keyid"],
        etiqueta=r["etiqueta_firma"], created=r["created"], content_type=r["cabeceras"]["Content-Type"],
    )
    for nombre in ("Content-Type", "Vereda-Version", "Content-Digest", "Signature-Input", "Signature"):
        assert cabeceras[nombre] == r["cabeceras"][nombre], f"cabecera {nombre} no coincide:\n  generada:   {cabeceras[nombre]!r}\n  publicada:  {r['cabeceras'][nombre]!r}"
    print("✓ las cinco cabeceras (incluida Signature, que depende del reloj 'created' fijo del vector) coinciden byte a byte")

    print("\nconformidad.rfc9421 reproduce el request RFC 9421 publicado en ejemplos/vectores-firma.json.")


if __name__ == "__main__":
    main()
