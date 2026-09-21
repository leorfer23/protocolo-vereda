"""Deriva las identidades de prueba publicadas en ejemplos/vectores-firma.json:
"las claves de prueba se derivan de una semilla publicada... así que cualquiera
llega a la misma clave privada sin que se la pasemos" (docs/claves-y-firmas.md).

El nivel C las usa como su propia identidad de nodo par -- no hace falta que
nadie le entregue una clave: ya está publicada, a propósito, para esto.
"""
import base64
import hashlib
import json
import os

from cryptography.hazmat.primitives import serialization as sz
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def cargar(base):
    return json.load(open(os.path.join(base, "ejemplos", "vectores-firma.json")))


def clave_privada_de(vectores, actor):
    """actor: 'nodo.rosario.coop', 'marta@vereda.ar', etc. -- el campo 'actor'
    de ejemplos/vectores-firma.json#/claves. Devuelve (clave_privada, clave_publica_b64u)
    y de paso confirma que la semilla publicada deriva la clave publicada
    (si no, es la propia suite la que está mal, no el nodo bajo prueba)."""
    entrada = next(c for c in vectores["claves"] if c["actor"] == actor)
    semilla = hashlib.sha256(entrada["semilla_sha256_de"].encode()).digest()
    if semilla.hex() != entrada["semilla_hex"]:
        raise ValueError(f"la semilla publicada de {actor} no es SHA-256 de {entrada['semilla_sha256_de']!r}")
    clave = Ed25519PrivateKey.from_private_bytes(semilla)
    publica = base64.urlsafe_b64encode(clave.public_key().public_bytes(sz.Encoding.Raw, sz.PublicFormat.Raw)).rstrip(b"=").decode()
    if publica != entrada["clave_publica"]:
        raise ValueError(f"la clave pública derivada de {actor} no coincide con la publicada")
    return clave, publica
