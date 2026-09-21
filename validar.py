#!/usr/bin/env python3
"""Valida los ejemplos contra los esquemas, el OpenAPI y los vectores de firma."""
import json, sys, glob, os, yaml, hashlib, base64
from openapi_spec_validator import validate
import rfc8785
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization as sz
from cryptography.exceptions import InvalidSignature
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

BASE = os.path.dirname(os.path.abspath(__file__))
ESQ = os.path.join(BASE, "esquemas")
EJ = os.path.join(BASE, "ejemplos")

registry = Registry()
esquemas = {}
for f in glob.glob(os.path.join(ESQ, "*.json")):
    s = json.load(open(f))
    esquemas[os.path.basename(f)] = s
    registry = registry.with_resource(s["$id"], Resource.from_contents(s))

MAPA = {
    "pizzeria-oferta.json": "oferta.json",
    "verduleria-oferta.json": "oferta.json",
    "catering-oferta.json": "oferta.json",
    "viandas-oferta.json": "oferta.json",
    "supermercado-oferta.json": "oferta.json",
    "verduleria-comercio.json": "comercio.json",
    "supermercado-pedido.json": "pedido.json",
    "mandato.json": "mandato.json",
    "ronda-los-alamos.json": "ronda.json",
    "grupo-edificio.json": "grupo.json",
    "carrito.json": "carrito.json",
    "supermercado-promocion.json": "promocion.json",
}

fallos = 0
for ej, esq in MAPA.items():
    doc = json.load(open(os.path.join(EJ, ej)))
    doc = {k: v for k, v in doc.items() if not k.startswith("$")}
    v = Draft202012Validator(esquemas[esq], registry=registry)
    errores = sorted(v.iter_errors(doc), key=lambda e: e.path)
    if errores:
        fallos += 1
        print(f"✗ {ej} contra {esq}")
        for e in errores[:8]:
            print(f"    {'/'.join(map(str, e.path)) or '(raíz)'}: {e.message[:140]}")
    else:
        print(f"✓ {ej} cumple {esq}")
print(f"\n{len(MAPA) - fallos}/{len(MAPA)} ejemplos válidos")

for f in sorted(glob.glob(os.path.join(EJ, "casos", "*.json"))):
    suite = json.load(open(f))
    esq = suite["esquema"]
    ref = {"$ref": "https://vereda.ar/esquemas/v1/" + esq} if "#" in esq else esquemas[esq]
    v = Draft202012Validator(ref, registry=registry)
    mal = [c["porque"] for c in suite["casos"] if v.is_valid(c["doc"]) != (c["espera"] == "valido")]
    fallos += len(mal)
    for m in mal:
        print(f"✗ casos/{os.path.basename(f)}: {m}")
    print(f"{len(suite['casos']) - len(mal)}/{len(suite['casos'])} casos de {suite['esquema']} como se esperaba")

API = os.path.join(BASE, "openapi.yaml")
try:
    api = yaml.safe_load(open(API))
    validate(api, base_uri="file://" + API)
    print("✓ openapi.yaml cumple OpenAPI 3.1")
    METODOS = {"get", "post", "put", "patch", "delete"}
    sin_id = [f"{m.upper()} {p}" for p, item in api["paths"].items() for m, o in item.items() if m in METODOS and "operationId" not in o]
    if sin_id:
        fallos += 1
        print(f"✗ operaciones sin operationId: {', '.join(sin_id)}")
    else:
        print("✓ todas las operaciones tienen operationId")
    sin_cache = [p for p, item in api["paths"].items() for m, o in item.items() if m in METODOS and o.get("security") == []
                 and not (m == "get" and "304" in o["responses"] and {"ETag", "Cache-Control"} <= set(o["responses"]["200"].get("headers", {})))]
    if sin_cache:
        fallos += 1
        print(f"✗ rutas públicas sin ETag, Cache-Control y 304: {', '.join(sin_cache)}")
    else:
        print("✓ todas las rutas públicas son cacheables y revalidables")
except Exception as e:
    fallos += 1
    print(f"✗ openapi.yaml\n    {str(e).splitlines()[0][:200]}")

# --- Vectores de firma: se re-deriva todo desde la semilla publicada ---
b64u = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
desde_b64u = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

def verificar_vectores():
    malos = []
    V = json.load(open(os.path.join(EJ, "vectores-firma.json")))
    publicas = {}
    for c in V["claves"]:
        semilla = hashlib.sha256(c["semilla_sha256_de"].encode()).digest()
        if semilla.hex() != c["semilla_hex"]:
            malos.append(f"la semilla publicada de {c['actor']} no es SHA-256 de {c['semilla_sha256_de']!r}")
            continue
        k = Ed25519PrivateKey.from_private_bytes(semilla)
        pub = b64u(k.public_key().public_bytes(sz.Encoding.Raw, sz.PublicFormat.Raw))
        if pub != c["clave_publica"]:
            malos.append(f"la clave pública de {c['actor']} no se deriva de su semilla")
        publicas[c["clave_publica"]] = pub

    for v in V["vectores"]:
        jcs = rfc8785.dumps(v["objeto_sin_firma"])
        if jcs.hex() != v["jcs_utf8_hex"]:
            malos.append(f"{v['nombre']}: el JCS no reproduce 'jcs_utf8_hex'")
            continue
        if hashlib.sha256(jcs).hexdigest() != v["jcs_sha256_hex"] or len(jcs) != v["jcs_bytes"]:
            malos.append(f"{v['nombre']}: sha256 o largo del JCS no coinciden")
        ref = {"$ref": "https://vereda.ar/esquemas/v1/" + v["esquema"]}
        errs = list(Draft202012Validator(ref, registry=registry).iter_errors(v["objeto_firmado"]))
        if errs:
            malos.append(f"{v['nombre']}: el objeto firmado no cumple {v['esquema']}: {errs[0].message[:80]}")
        firma = v["objeto_firmado"][v["campo_firma"]]
        # el objeto firmado, menos su firma, tiene que ser exactamente el objeto sin firma
        if {k: x for k, x in v["objeto_firmado"].items() if k != v["campo_firma"]} != v["objeto_sin_firma"]:
            malos.append(f"{v['nombre']}: el objeto firmado no coincide con el objeto sin firma")
        try:
            Ed25519PublicKey.from_public_bytes(desde_b64u(firma["clave_publica"])).verify(desde_b64u(firma["valor"]), jcs)
        except (InvalidSignature, ValueError):
            malos.append(f"{v['nombre']}: la firma no verifica contra su clave pública")
        # una firma no puede valer para otros bytes
        try:
            Ed25519PublicKey.from_public_bytes(desde_b64u(firma["clave_publica"])).verify(desde_b64u(firma["valor"]), jcs + b" ")
            malos.append(f"{v['nombre']}: la firma verifica bytes alterados")
        except (InvalidSignature, ValueError):
            pass

    for c in V["casos_jcs"]:
        jcs = rfc8785.dumps(c["objeto"])
        if jcs.hex() != c["jcs_utf8_hex"] or jcs.decode("utf-8") != c["jcs_utf8"]:
            malos.append(f"caso JCS {c['nombre']}: no reproduce los bytes publicados")
        elif hashlib.sha256(jcs).hexdigest() != c["jcs_sha256_hex"]:
            malos.append(f"caso JCS {c['nombre']}: sha256 no coincide")

    r = V["rfc9421"]
    cuerpo = bytes.fromhex(r["cuerpo_utf8_hex"])
    if hashlib.sha256(cuerpo).hexdigest() != r["cuerpo_sha256_hex"]:
        malos.append("rfc9421: el sha256 del cuerpo no coincide")
    esperado = "sha-256=:" + base64.b64encode(hashlib.sha256(cuerpo).digest()).decode() + ":"
    if r["cabeceras"]["Content-Digest"] != esperado:
        malos.append("rfc9421: Content-Digest no corresponde al cuerpo")
    if r["base_de_firma"].encode().hex() != r["base_de_firma_hex"]:
        malos.append("rfc9421: base_de_firma_hex no corresponde al texto de la base")
    params = r["cabeceras"]["Signature-Input"].split("=", 1)[1]
    base = "\n".join([
        '"@method": ' + r["metodo"],
        '"@target-uri": ' + r["url"],
        '"content-digest": ' + r["cabeceras"]["Content-Digest"],
        '"content-type": ' + r["cabeceras"]["Content-Type"],
        '"vereda-version": ' + r["cabeceras"]["Vereda-Version"],
        '"@signature-params": ' + params,
    ])
    if base != r["base_de_firma"]:
        malos.append("rfc9421: la base de firma no se reconstruye desde las cabeceras")
    else:
        sig = r["cabeceras"]["Signature"].split("=", 1)[1].strip(":")
        try:
            Ed25519PublicKey.from_public_bytes(desde_b64u(r["keyid"])).verify(base64.b64decode(sig), base.encode())
        except (InvalidSignature, ValueError):
            malos.append("rfc9421: la firma HTTP no verifica")
    return malos, len(V["vectores"]) + len(V["casos_jcs"]) + 1

malos, total = verificar_vectores()
fallos += len(malos)
for m in malos:
    print(f"✗ {m}")
print(f"{total - len(malos)}/{total} vectores de firma reproducidos exactamente")

sys.exit(1 if fallos else 0)
