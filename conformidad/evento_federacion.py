"""Construye y firma un evento tal como viaja en POST /federacion/entrantes.

Dos firmas distintas, en dos capas (docs/claves-y-firmas.md, docs/federacion.md):
1. `firma_nodo`, adentro del propio evento: Ed25519 sobre el JCS del evento
   sin firma. Es la que hace válido al evento como objeto, y sobrevive a
   cómo viajó (SSE, webhook, federación).
2. La firma HTTP RFC 9421 (`conformidad.rfc9421`) sobre el request entero.
   Es la que autentica AL EMISOR de este POST puntual, no al evento.

El cuerpo que se manda por HTTP es el JCS del evento ya firmado: bytes
canónicos, sin la ambigüedad de "cualquier serialización JSON válida".
"""
import base64

import rfc8785


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def firmar_evento(evento_sin_firma: dict, *, clave_privada, clave_publica_b64u: str, dominio_emisor: str) -> tuple[dict, bytes]:
    """Devuelve (objeto_firmado, cuerpo_jcs_bytes)."""
    jcs = rfc8785.dumps(evento_sin_firma)
    firma_nodo = {
        "firmante": dominio_emisor,
        "clave_publica": clave_publica_b64u,
        "valor": _b64u(clave_privada.sign(jcs)),
        "instante": evento_sin_firma["instante"],
    }
    firmado = {**evento_sin_firma, "firma_nodo": firma_nodo}
    return firmado, rfc8785.dumps(firmado)
