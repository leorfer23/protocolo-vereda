"""Verificación del registro público (docs/claves-y-firmas.md, "Registro público").

La usan validar.py, contra el vector publicado, y el nivel A, contra un nodo real:
la misma cuenta en los dos lados, así la suite no puede aprobar una cadena que el
vector no aprobaría.
"""
import base64
import hashlib
from datetime import datetime

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

CEROS = "0" * 64


def _desde_b64u(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def ref(valor):
    """base64url(SHA-256('vereda:registro:' + valor)[:16]), sin relleno."""
    return base64.urlsafe_b64encode(hashlib.sha256(("vereda:registro:" + valor).encode()).digest()[:16]).rstrip(b"=").decode()


def bytes_de_entrada(entrada):
    """Lo que cubren 'hash' y 'firma': el JCS de la entrada sin esos dos campos."""
    return rfc8785.dumps({k: v for k, v in entrada.items() if k not in ("hash", "firma")})


def verificar_cadena(entradas, anterior=CEROS, secuencia_anterior=0, claves_nodo=None):
    """Recorre entradas en orden. 'anterior' y 'secuencia_anterior' son los de la
    entrada previa a la primera (64 ceros y 0 si la página empieza en 1).
    'claves_nodo': las claves públicas del nodo (base64url); None no verifica
    que la firma sea de una de ellas, solo que verifique con su propia clave.
    Devuelve (errores, hash de la última, secuencia de la última)."""
    errores = []
    instante_previo = None
    for e in entradas:
        s = e.get("secuencia")
        if s != secuencia_anterior + 1:
            errores.append(f"secuencia {s} después de {secuencia_anterior}: el registro no tiene huecos")
        if e.get("anterior") != anterior:
            errores.append(f"secuencia {s}: 'anterior' no es el hash de la entrada previa")
        try:
            b = bytes_de_entrada(e)
        except (TypeError, ValueError) as ex:
            errores.append(f"secuencia {s}: no se pudo canonicalizar (JCS): {ex}")
            break
        calculado = hashlib.sha256(b).hexdigest()
        if e.get("hash") != calculado:
            errores.append(f"secuencia {s}: 'hash' no es el SHA-256 del JCS de la entrada")
        firma = e.get("firma") or {}
        if firma.get("firmante") != e.get("nodo"):
            errores.append(f"secuencia {s}: la firma no es del nodo que lleva el registro")
        try:
            Ed25519PublicKey.from_public_bytes(_desde_b64u(firma["clave_publica"])).verify(_desde_b64u(firma["valor"]), b)
        except (KeyError, InvalidSignature, ValueError):
            errores.append(f"secuencia {s}: la firma del nodo no verifica")
        if claves_nodo is not None and firma.get("clave_publica") not in claves_nodo:
            errores.append(f"secuencia {s}: la firma es de una clave que no está en las claves del nodo")
        try:
            instante = datetime.fromisoformat(e["instante"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError):
            instante = None
            errores.append(f"secuencia {s}: 'instante' no es un instante RFC 3339")
        if instante and instante_previo and instante < instante_previo:
            errores.append(f"secuencia {s}: 'instante' anterior al de la entrada previa")
        instante_previo = instante or instante_previo
        anterior, secuencia_anterior = calculado, s if isinstance(s, int) else secuencia_anterior + 1
    return errores, anterior, secuencia_anterior


def verificar_hecho(entrada, objeto_sin_firma):
    """Que 'hecho' corresponda a un objeto que firmó una persona: misma huella, y
    su firma verifica sobre esos bytes."""
    h = entrada.get("hecho") or {}
    b = rfc8785.dumps(objeto_sin_firma)
    if h.get("sha256") != hashlib.sha256(b).hexdigest():
        return "'hecho.sha256' no es la huella del objeto"
    f = h.get("firma")
    if f:
        try:
            Ed25519PublicKey.from_public_bytes(_desde_b64u(f["clave_publica"])).verify(_desde_b64u(f["valor"]), b)
        except (KeyError, InvalidSignature, ValueError):
            return "'hecho.firma' no verifica sobre el objeto"
    return None
