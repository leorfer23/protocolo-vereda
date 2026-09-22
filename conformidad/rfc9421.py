"""Firma HTTP RFC 9421: el único mecanismo de firma entre nodos (docs/
federacion.md, docs/claves-y-firmas.md), sin variantes ni fallback a
draft-cavage. Reproduce byte a byte la base de firma de `ejemplos/vectores-
firma.json#/rfc9421`, y su firma verifica contra la clave publicada -- ver
conformidad/pruebas/verificar_rfc9421_con_vectores.py.
"""
import base64
import hashlib
import time

COMPONENTES = ("@method", "@target-uri", "content-digest", "content-type", "vereda-version")


def content_digest(cuerpo: bytes) -> str:
    return "sha-256=:" + base64.b64encode(hashlib.sha256(cuerpo).digest()).decode() + ":"


def base_de_firma(*, metodo, url, digest, content_type, vereda_version, created, keyid):
    valores = {
        "@method": metodo.upper(),
        "@target-uri": url,
        "content-digest": digest,
        "content-type": content_type,
        "vereda-version": vereda_version,
    }
    params = (
        "(" + " ".join(f'"{c}"' for c in COMPONENTES) + ")"
        f';created={created};keyid="{keyid}";alg="ed25519"'
    )
    lineas = [f'"{c}": {valores[c]}' for c in COMPONENTES] + [f'"@signature-params": {params}']
    return "\n".join(lineas), params


def firmar_pedido(*, metodo, url, cuerpo: bytes, vereda_version, clave_privada, keyid, etiqueta="sig1", created=None, content_type="application/json"):
    """Devuelve las cabeceras (Content-Type, Vereda-Version, Content-Digest,
    Signature-Input, Signature) para un POST a `url` con este `cuerpo`,
    firmado con `clave_privada` (una Ed25519PrivateKey)."""
    created = int(time.time()) if created is None else created
    digest = content_digest(cuerpo)
    base, params = base_de_firma(metodo=metodo, url=url, digest=digest, content_type=content_type, vereda_version=vereda_version, created=created, keyid=keyid)
    firma = clave_privada.sign(base.encode())
    return {
        "Content-Type": content_type,
        "Vereda-Version": vereda_version,
        "Content-Digest": digest,
        "Signature-Input": f"{etiqueta}={params}",
        "Signature": f"{etiqueta}=:{base64.b64encode(firma).decode()}:",
    }
