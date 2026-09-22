#!/usr/bin/env python3
"""Valida los ejemplos contra los esquemas, el OpenAPI y los vectores de firma."""
import json, sys, glob, os, yaml, hashlib, base64
from openapi_spec_validator import validate
import rfc8785
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization as sz
from cryptography.exceptions import InvalidSignature
from jsonschema import Draft202012Validator

from conformidad.oraculo import cargar as cargar_esquemas

BASE = os.path.dirname(os.path.abspath(__file__))
EJ = os.path.join(BASE, "ejemplos")

esquemas, registry = cargar_esquemas(BASE)

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
    "repartidor-bici.json": "repartidor.json",
    "sostenimiento.json": "sostenimiento.json",
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
    # Una escritura pública (pedir un desafío de /acceso) no se cachea: la regla es para las lecturas.
    sin_cache = [p for p, item in api["paths"].items() for m, o in item.items() if m == "get" and o.get("security") == []
                 and not ("304" in o["responses"] and {"ETag", "Cache-Control"} <= set(o["responses"]["200"].get("headers", {})))]
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

# Lo que el firmante no escribió y por eso queda fuera del JCS
# (docs/claves-y-firmas.md): 'respuesta' la agrega el reseñado, 'senales' y
# 'visible' las escribe el nodo al recalcular.
FUERA_DE_LA_FIRMA = ("firma", "firma_nodo", "respuesta", "senales", "visible")

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
        # el objeto firmado, menos lo que su autor no escribió, tiene que ser
        # exactamente el objeto sin firma (docs/claves-y-firmas.md)
        if {k: x for k, x in v["objeto_firmado"].items() if k != v["campo_firma"] and k not in FUERA_DE_LA_FIRMA} != v["objeto_sin_firma"]:
            malos.append(f"{v['nombre']}: el objeto firmado no coincide con el objeto sin firma")
        try:
            Ed25519PublicKey.from_public_bytes(desde_b64u(firma["clave_publica"])).verify(desde_b64u(firma["valor"]), jcs)
        except (InvalidSignature, ValueError):
            malos.append(f"{v['nombre']}: la firma no verifica contra su clave pública")
        # el código de una vinculación sale del mismo JCS que cubre la firma
        # (docs/identidad-y-verificacion.md): los primeros 16 bytes del SHA-256
        if "texto_de_prueba" in v and v["texto_de_prueba"] != "vereda:prueba=" + b64u(hashlib.sha256(jcs).digest()[:16]):
            malos.append(f"{v['nombre']}: 'texto_de_prueba' no sale del SHA-256 del JCS")
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

# --- Vectores de acceso y respaldo (docs/acceso.md): se rehace todo desde la frase y las semillas ---
def verificar_acceso():
    import unicodedata
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.exceptions import InvalidTag

    malos = []
    A = json.load(open(os.path.join(EJ, "vectores-acceso.json")))
    esquema = lambda d: Draft202012Validator({"$ref": "https://vereda.ar/esquemas/v1/acceso.json#/$defs/" + d}, registry=registry)
    publica_ed = lambda s: b64u(Ed25519PrivateKey.from_private_bytes(s).public_key().public_bytes(sz.Encoding.Raw, sz.PublicFormat.Raw))
    publica_x = lambda s: b64u(X25519PrivateKey.from_private_bytes(s).public_key().public_bytes(sz.Encoding.Raw, sz.PublicFormat.Raw))

    c = A["clave"]
    semilla = hashlib.sha256(c["semilla_sha256_de"].encode()).digest()
    if publica_ed(semilla) != c["clave_publica"]:
        malos.append("acceso: la clave pública no se deriva de su semilla")
    if publica_x(hashlib.sha256(c["cifrado_sha256_de"].encode()).digest()) != c["clave_cifrado"]:
        malos.append("acceso: la clave de cifrado no se deriva de su semilla")

    p = A["prueba_de_clave"]
    jcs = rfc8785.dumps(p["objeto"])
    if jcs.hex() != p["jcs_utf8_hex"]:
        malos.append("prueba de clave: el JCS no reproduce 'jcs_utf8_hex'")
    if p["objeto"] != {"clave_publica": c["clave_publica"], "desafio": p["desafio"]["desafio"], "nodo": p["desafio"]["nodo"]}:
        malos.append("prueba de clave: el objeto firmado no sale del desafío y la clave")
    for defn, doc in (("desafio", p["desafio"]), ("prueba_de_clave", p["objeto"]), ("pedido_sesion", p["pedido_sesion"])):
        errs = list(esquema(defn).iter_errors(doc))
        if errs:
            malos.append(f"prueba de clave: {defn} no cumple acceso.json: {errs[0].message[:80]}")
    try:
        Ed25519PublicKey.from_public_bytes(desde_b64u(c["clave_publica"])).verify(desde_b64u(p["pedido_sesion"]["firma"]), jcs)
    except (InvalidSignature, ValueError):
        malos.append("prueba de clave: la firma no verifica")

    i = A["identidad_derivada"]
    local = base64.b32encode(hashlib.sha256(desde_b64u(i["clave_publica"])).digest()[:10]).decode().rstrip("=").lower()
    if i["identidad"] != local + "@vereda.ar":
        malos.append("identidad derivada: no sale del SHA-256 de la clave")

    for r in A["respaldos"]:
        doc = r["respaldo"]
        errs = list(esquema("respaldo").iter_errors(doc))
        if errs:
            malos.append(f"{r['nombre']}: no cumple acceso.json#/$defs/respaldo: {errs[0].message[:80]}")
            continue
        nfc = unicodedata.normalize("NFC", r["frase"]).encode()
        if nfc.hex() != r["frase_nfc_utf8_hex"]:
            malos.append(f"{r['nombre']}: la frase en NFC no da 'frase_nfc_utf8_hex'")
        derivar = lambda f: PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=desde_b64u(doc["kdf"]["sal"]), iterations=doc["kdf"]["iteraciones"]).derive(unicodedata.normalize("NFC", f).encode())
        llave = derivar(r["frase"])
        if llave.hex() != r["llave_hex"]:
            malos.append(f"{r['nombre']}: PBKDF2 no reproduce 'llave_hex'")
        aad = rfc8785.dumps({k: v for k, v in doc.items() if k != "cifrado"})
        if aad.hex() != r["aad_jcs_utf8_hex"]:
            malos.append(f"{r['nombre']}: el AAD no es el JCS del respaldo sin 'cifrado'")
        nonce, texto = desde_b64u(doc["cifrado"]["nonce"]), desde_b64u(doc["cifrado"]["texto"])
        try:
            claro = AESGCM(llave).decrypt(nonce, texto, aad)
        except InvalidTag:
            malos.append(f"{r['nombre']}: no se abre con su frase")
            continue
        if claro.hex() != r["texto_claro_hex"]:
            malos.append(f"{r['nombre']}: el texto claro no coincide")
        try:
            AESGCM(derivar(r["frase_incorrecta"])).decrypt(nonce, texto, aad)
            malos.append(f"{r['nombre']}: se abre con la frase incorrecta")
        except InvalidTag:
            pass
        try:
            AESGCM(llave).decrypt(nonce, texto, aad + b" ")
            malos.append(f"{r['nombre']}: se abre con la cabecera alterada")
        except InvalidTag:
            pass
        if doc["formato"] == "vereda.clave.v3":
            adentro = json.loads(claro)
            if rfc8785.dumps(adentro) != claro or list(esquema("texto_claro_v3").iter_errors(adentro)):
                malos.append(f"{r['nombre']}: el texto claro no es el JCS de texto_claro_v3")
                continue
            if publica_ed(desde_b64u(adentro["firma"])) != doc["clave_publica"]:
                malos.append(f"{r['nombre']}: la semilla de adentro no da la clave pública de afuera")
            if ("cifrado" in adentro) != ("clave_cifrado" in doc) or ("cifrado" in adentro and publica_x(desde_b64u(adentro["cifrado"])) != doc["clave_cifrado"]):
                malos.append(f"{r['nombre']}: la clave X25519 de adentro no da 'clave_cifrado'")
        elif publica_ed(claro) != doc["clave_publica"]:
            malos.append(f"{r['nombre']}: la semilla de adentro no da la clave pública de afuera")
    return malos, 3 + len(A["respaldos"])

malos, total = verificar_acceso()
fallos += len(malos)
for m in malos:
    print(f"✗ {m}")
print(f"{total - len(malos)}/{total} vectores de acceso y respaldo reproducidos exactamente")

sys.exit(1 if fallos else 0)
