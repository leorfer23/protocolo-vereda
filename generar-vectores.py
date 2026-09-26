#!/usr/bin/env python3
"""Genera ejemplos/vectores-firma.json. Determinista: correrlo dos veces da el mismo archivo.

    pip install cryptography rfc8785 && python3 generar-vectores.py
"""
import json, hashlib, base64, os
import rfc8785
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization as sz

BASE = os.path.dirname(os.path.abspath(__file__))
b64u = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
semilla = lambda etiqueta: hashlib.sha256(f"vereda:vector:{etiqueta}".encode()).digest()

def clave(etiqueta):
    k = Ed25519PrivateKey.from_private_bytes(semilla(etiqueta))
    return k, b64u(k.public_key().public_bytes(sz.Encoding.Raw, sz.PublicFormat.Raw))

ACTORES = {
    "marta@vereda.ar": "marta",
    "lahuerta@nodo.rosario.coop": "lahuerta",
    "vereda.ar": "nodo-vereda",
    "nodo.rosario.coop": "nodo-rosario",
}

# Lo que el firmante no escribió queda fuera del JCS (docs/claves-y-firmas.md):
# 'respuesta' la agrega el reseñado, 'senales' y 'visible' las escribe el nodo.
FUERA_DE_LA_FIRMA = ("firma", "firma_nodo", "respuesta", "senales", "visible")

def firmar(objeto, firmante, instante):
    """Firma JCS+Ed25519 sobre el objeto sin los campos que no escribió su autor.
    Devuelve el vector completo."""
    k, pub = clave(ACTORES[firmante])
    sin_firma = {c: v for c, v in objeto.items() if c not in FUERA_DE_LA_FIRMA}
    jcs = rfc8785.dumps(sin_firma)
    firma = {"firmante": firmante, "clave_publica": pub, "valor": b64u(k.sign(jcs)), "instante": instante}
    return jcs, firma

def vector(nombre, descripcion, objeto, campo, firmante, instante, esquema):
    jcs, firma = firmar(objeto, firmante, instante)
    return {
        "nombre": nombre,
        "descripcion": descripcion,
        "esquema": esquema,
        "objeto_sin_firma": {c: v for c, v in objeto.items() if c != campo and c not in FUERA_DE_LA_FIRMA},
        "jcs_utf8_hex": jcs.hex(),
        "jcs_sha256_hex": hashlib.sha256(jcs).hexdigest(),
        "jcs_bytes": len(jcs),
        "campo_firma": campo,
        "objeto_firmado": {**objeto, campo: firma},
    }

META = lambda i, ts: {"id": i, "nodo": "vereda.ar", "creado": ts, "actualizado": ts, "version_esquema": "1.0"}
TS = "2026-09-21T15:04:05-03:00"

# --- 1. Reseña: la pieza que hace portable la reputación ---
resena = {
    **META("01926b3a-1111-7000-8000-000000000001", TS),
    "pedido_id": "01926b3a-0000-7000-8000-00000000000a",
    "autor": "marta@vereda.ar",
    "destinatario": "lahuerta@nodo.rosario.coop",
    "rol_autor": "usuario",
    "puntaje": 5,
    "texto": "Tomates impecables y llegó antes de la franja. Ñandú, açaí, 5 ★.",
}
v_resena = vector("resena-firmada",
    "Reseña firmada por su autora. El texto lleva acentos, ñ, cedilla y un símbolo fuera del BMP a propósito: es donde más difieren las implementaciones de JCS.",
    resena, "firma", "marta@vereda.ar", TS, "resena.json")

# La misma reseña después de que el reseñado respondió y el nodo la marcó: los
# tres campos nuevos no los escribió la autora, así que la firma es byte por byte
# la misma y sigue verificando. Es la prueba de que responder o marcar una reseña
# no puede romper lo único que el protocolo promete de ella.
resena_marcada = {
    **resena,
    "visible": True,
    "senales": {
        "peso": 0.2,
        "motivos": ["en_revision_por_rafaga"],
        "rafaga": {"resenas_en_ventana": 20, "ventana_horas": 72, "ritmo_habitual": 1.4, "autores_sin_credito": 0.95},
    },
    "respuesta": {"texto": "Gracias Marta, nos alegra.", "instante": "2026-09-25T10:00:00-03:00"},
}
v_resena_marcada = vector("resena-respondida-y-marcada",
    "La misma reseña con 'respuesta', 'senales' y 'visible'. El JCS es idéntico al del vector anterior: quien verifica saca los campos que no escribió el firmante antes de canonicalizar.",
    resena_marcada, "firma", "marta@vereda.ar", TS, "resena.json")
assert v_resena_marcada["jcs_sha256_hex"] == v_resena["jcs_sha256_hex"], \
    "responder o marcar una reseña cambió los bytes que cubre la firma"

# --- 2. Entrada de clave avalada: la cadena de rotación ---
k_vieja, pub_vieja = clave("marta-clave-1")
k_nueva, pub_nueva = clave("marta-clave-2")
entrada = {"clave_publica": pub_nueva, "desde": "2026-09-01T10:00:00-03:00", "estado": "activa"}
jcs_entrada = rfc8785.dumps(entrada)
entrada_avalada = {**entrada, "avalada_por": {"clave_publica": pub_vieja, "valor": b64u(k_vieja.sign(jcs_entrada))}}
v_clave = {
    "nombre": "entrada-de-clave-avalada",
    "descripcion": "Rotación de clave: la clave anterior firma el JCS de la entrada nueva sin 'avalada_por'. Esto es lo que permite verificar el historial sin confiar en el nodo.",
    "esquema": "comunes.json#/$defs/clave",
    "objeto_sin_firma": entrada,
    "jcs_utf8_hex": jcs_entrada.hex(),
    "jcs_sha256_hex": hashlib.sha256(jcs_entrada).hexdigest(),
    "jcs_bytes": len(jcs_entrada),
    "campo_firma": "avalada_por",
    "clave_avaladora": {"etiqueta_semilla": "marta-clave-1", "clave_publica": pub_vieja},
    "objeto_firmado": entrada_avalada,
}

# --- 3. Evento firmado por el nodo: lo que viaja entre nodos ---
evento = {
    "id": "01926b3a-2222-7000-8000-000000000002",
    "tipo": "pedido.aceptado",
    "instante": TS,
    "nodo": "nodo.rosario.coop",
    "entidad": {"tipo": "pedido", "id": "01926b3a-0000-7000-8000-00000000000a"},
    "actor": "lahuerta@nodo.rosario.coop",
    "datos": {"estado": "aceptado"},
    "secuencia": 3,
}
v_evento = vector("evento-firmado-por-el-nodo",
    "Evento tal como viaja en POST /federacion/entrantes. Lo firma el nodo, no el actor.",
    evento, "firma_nodo", "nodo.rosario.coop", TS, "evento.json")

# --- 4. Mudanza: la declaración que vale sin el nodo viejo ---
mudanza = {
    "identidad_anterior": "marta@vereda.ar",
    "identidad_nueva": "marta@otro.ar",
    "instante": TS,
    "claves_anteriores": [{"clave_publica": clave(ACTORES["marta@vereda.ar"])[1], "desde": "2026-01-10T10:00:00-03:00", "estado": "activa"}],
}
v_mudanza = vector("mudanza-firmada-por-el-actor",
    "Marta declara que se mudó de nodo. La firma ella, con la clave que ya usaba en el nodo viejo, y el firmante es su identidad anterior. Cualquiera la verifica contra su historial de claves sin preguntarle al nodo viejo: por eso una mudanza no depende de que el nodo viejo coopere.",
    mudanza, "firma", "marta@vereda.ar", TS, "comunes.json#/$defs/mudanza")

# --- 5. Vinculación: la prueba que cualquiera rehace sin preguntarle al nodo ---
vinculacion = {
    "id": "01926b3a-2222-7000-8000-000000000001",
    "identidad": "lahuerta@nodo.rosario.coop",
    "tipo": "dominio",
    "valor": "lahuerta.com.ar",
    "declarada": TS,
    "senales": {"estado": "verificada", "verificada_en": TS, "comprobada_en": TS},
}
v_vinculacion = vector("vinculacion-dominio-con-codigo",
    "La Huerta declara que lahuerta.com.ar es suyo. El texto a publicar en el TXT de _vereda.lahuerta.com.ar sale del SHA-256 del mismo JCS que cubre la firma: los primeros 16 bytes, en base64url. 'senales' la escribió el nodo después y no entra ni en la firma ni en el código (docs/identidad-y-verificacion.md).",
    vinculacion, "firma", "lahuerta@nodo.rosario.coop", TS, "comunes.json#/$defs/vinculacion")
v_vinculacion["texto_de_prueba"] = "vereda:prueba=" + b64u(bytes.fromhex(v_vinculacion["jcs_sha256_hex"])[:16])

# --- 5b. Traspaso: la firma del repartidor al entregar ---
traspaso = {
    "accion": "entrega",
    "pedido_id": "01926b3a-7c4e-7000-8000-00000000abcd",
    "repartidor": "marta@vereda.ar",
    "instante": TS,
}
v_traspaso = vector("traspaso-entrega",
    "Marta, repartidora, entrega el pedido y firma con la clave de su teléfono. Manda solo 'firma' en POST /pedidos/{id}/entregar; el nodo rearma este objeto con la acción de la ruta, el id del pedido, la identidad de la sesión y firma.instante, y lo verifica. Lo guarda en pedido.firmas.entrega (docs/repartidores.md, punto j).",
    traspaso, "firma", "marta@vereda.ar", TS, "pedido.json#/$defs/traspaso")

# --- 5b. Recepción: el nodo atestigua que quien entregó dio el código del comprador ---
recepcion = {
    "accion": "recepcion",
    "pedido_id": "01926b3a-7c4e-7000-8000-00000000abcd",
    "usuario": "juan@vereda.ar",
    "entrego": "marta@vereda.ar",
    "instante": TS,
}
v_recepcion = vector("recepcion-con-codigo",
    "Marta entrega y manda el codigo_entrega que le dijo Juan; coincide. El nodo vereda.ar firma este objeto con su clave (firmante = su dominio) y lo guarda en pedido.firmas.recepcion. No lleva el código. Se rearma desde el pedido: id, usuario, quien mandó el código y firma.instante (docs/claves-y-firmas.md, \"Recepción con código\").",
    recepcion, "firma", "vereda.ar", TS, "pedido.json#/$defs/recepcion")

# --- 5c. Rendición: el repartidor declara cuánto efectivo le dio al comercio ---
rendicion = {
    "accion": "rendida",
    "pedido_id": "01926b3a-7c4e-7000-8000-00000000abcd",
    "actor": "marta@vereda.ar",
    "monto": {"centavos": 1234000, "moneda": "ARS"},
    "instante": TS,
}
v_rendicion = vector("rendicion-rendida",
    "Marta, repartidora, cobró en la puerta los productos en efectivo y le da al comercio lo suyo después de entregar. Firma con la clave de su teléfono y manda {monto, firma} en POST /pedidos/{id}/rendicion; el nodo arma este objeto con la acción de la ruta, el id del pedido, la identidad de la sesión, el monto y firma.instante, lo verifica y lo guarda entero en pedido.rendicion.constancias. La 'recibida' del comercio es igual, con su identidad y su clave (docs/repartidores.md, punto l).",
    rendicion, "firma", "marta@vereda.ar", TS, "pedido.json#/$defs/constancia_rendicion")

# --- 6. Casos JCS sin firma: donde las implementaciones se separan ---
CASOS = [
    ("orden-de-claves", "Las claves se ordenan por sus unidades de código UTF-16, no por alfabeto ni por orden de aparición.",
     {"b": 1, "A": 2, "a": 3, "á": 4, "10": 5, "2": 6}),
    ("montos-enteros", "Vereda expresa dinero en centavos enteros. Nunca hay decimales en un monto.",
     {"monto": {"centavos": 1250000, "moneda": "ARS"}, "descuento": {"centavos": 0, "moneda": "ARS"}}),
    ("numeros-no-monetarios", "Pesos, distancias y puntajes sí son decimales. JCS los serializa como ECMAScript.",
     {"peso_kg": 1.5, "lat": -34.6103, "lng": -58.4212, "promedio": 4.5, "cero": 0, "entero_grande": 9007199254740991}),
    ("texto-unicode", "Acentos, ñ y símbolos fuera del BMP van tal cual en UTF-8; JCS no los escapa.",
     {"nombre": "Almacén Doña Ñata", "nota": "café ☕ 100% — 5 ★", "emoji": "\U0001F600"}),
    ("escapes-obligatorios", "Solo se escapan comilla, barra invertida y los controles por debajo de 0x20.",
     {"texto": "Linea1\nLinea2\tcon \"comillas\" y \\barra\\", "control": "\u0001"}),
    ("anidado-y-vacios", "Arrays conservan su orden. Objetos y arrays vacíos se serializan igual que cualquier otro.",
     {"items": [{"z": 1, "a": 2}, {}], "vacio": {}, "lista_vacia": [], "nulo": None, "si": True, "no": False}),
]
casos_jcs = []
for nombre, desc, obj in CASOS:
    jcs = rfc8785.dumps(obj)
    casos_jcs.append({"nombre": nombre, "descripcion": desc, "objeto": obj,
                      "jcs_utf8": jcs.decode("utf-8"), "jcs_utf8_hex": jcs.hex(),
                      "jcs_sha256_hex": hashlib.sha256(jcs).hexdigest()})

# --- 7. Request RFC 9421 completo: una entrega entre nodos ---
cuerpo = rfc8785.dumps(v_evento["objeto_firmado"])
digest = base64.b64encode(hashlib.sha256(cuerpo).digest()).decode()
content_digest = f"sha-256=:{digest}:"
k_nodo, pub_nodo = clave(ACTORES["nodo.rosario.coop"])
created = 1758477845
params = ('("@method" "@target-uri" "content-digest" "content-type" "vereda-version")'
          f';created={created};keyid="{pub_nodo}";alg="ed25519"')
lineas = [
    '"@method": POST',
    '"@target-uri": https://vereda.ar/v1/federacion/entrantes',
    f'"content-digest": {content_digest}',
    '"content-type": application/json',
    '"vereda-version": 1.0',
    f'"@signature-params": {params}',
]
base_firma = "\n".join(lineas)
sig = base64.b64encode(k_nodo.sign(base_firma.encode())).decode()
rfc9421 = {
    "descripcion": "POST /federacion/entrantes de nodo.rosario.coop a vereda.ar, firmado con la clave del nodo emisor. Es el único mecanismo de firma HTTP del protocolo: no hay variantes ni fallback a draft-cavage.",
    "etiqueta_firma": "sig1",
    "metodo": "POST",
    "url": "https://vereda.ar/v1/federacion/entrantes",
    "cuerpo_utf8_hex": cuerpo.hex(),
    "cuerpo_sha256_hex": hashlib.sha256(cuerpo).hexdigest(),
    "componentes": ["@method", "@target-uri", "content-digest", "content-type", "vereda-version"],
    "created": created,
    "keyid": pub_nodo,
    "alg": "ed25519",
    "base_de_firma": base_firma,
    "base_de_firma_hex": base_firma.encode().hex(),
    "cabeceras": {
        "Content-Type": "application/json",
        "Vereda-Version": "1.0",
        "Content-Digest": content_digest,
        "Signature-Input": f"sig1={params}",
        "Signature": f"sig1=:{sig}:",
    },
    "nota_base64": "Signature y Content-Digest usan base64 estándar con relleno, como manda RFC 9421. Las firmas dentro de los objetos JSON usan base64url sin relleno.",
}

# --- 8. Firma fresca: la persona firma una operación sensible con su clave activa (docs/acceso.md, punto 6) ---
k_marta, pub_marta_ff = clave(ACTORES["marta@vereda.ar"])
cuerpo_ff = rfc8785.dumps({"privado": {"cuenta_cobro": {"alias": "lahuerta.verdu", "titular": "Marta Gómez"}}})
digest_ff = "sha-256=:" + base64.b64encode(hashlib.sha256(cuerpo_ff).digest()).decode() + ":"
created_ff = 1790000000
path_ff = "/v1/comercios/01926b3c-4d5e-7f00-8a1b-2c3d4e5f6a7b"
params_ff = ('("@method" "@path" "@query" "content-digest")'
             f';created={created_ff};keyid="{pub_marta_ff}";alg="ed25519";tag="vereda-fresca"')
base_ff = "\n".join([
    '"@method": PATCH',
    f'"@path": {path_ff}',
    '"@query": ?',
    f'"content-digest": {digest_ff}',
    f'"@signature-params": {params_ff}',
])
firma_fresca = {
    "descripcion": "PATCH /v1/comercios/{id} que cambia privado.cuenta_cobro, firmado por marta@vereda.ar con su clave activa, además del token de sesión. '@query' es '?' porque el pedido no trae query (RFC 9421, 2.2.7). Un GET sin cuerpo lleva el Content-Digest de cero bytes.",
    "etiqueta_firma": "fresca",
    "metodo": "PATCH",
    "path": path_ff,
    "query": "?",
    "cuerpo_utf8_hex": cuerpo_ff.hex(),
    "componentes": ["@method", "@path", "@query", "content-digest"],
    "created": created_ff,
    "keyid": pub_marta_ff,
    "alg": "ed25519",
    "tag": "vereda-fresca",
    "base_de_firma": base_ff,
    "base_de_firma_hex": base_ff.encode().hex(),
    "content_digest_vacio": "sha-256=:" + base64.b64encode(hashlib.sha256(b"").digest()).decode() + ":",
    "cabeceras": {
        "Content-Digest": digest_ff,
        "Signature-Input": f"fresca={params_ff}",
        "Signature": "fresca=:" + base64.b64encode(k_marta.sign(base_ff.encode())).decode() + ":",
    },
}

doc = {
    "$comentario": "Vectores de prueba de firma del Protocolo Vereda. Una implementación conforme reproduce byte a byte cada JCS, Content-Digest y base de firma, y verifica cada firma contra la clave publicada. Las firmas no se exigen idénticas: Ed25519 con azar (CryptoKit en iOS) da firmas distintas e igual de válidas.",
    "version_esquema": "1.0",
    "como_reproducir": {
        "1_semilla": "La clave privada de cada actor es Ed25519 a partir de la semilla SHA-256('vereda:vector:<etiqueta>'). Las etiquetas están en 'claves'. Son claves de prueba: nunca se usan en producción.",
        "2_canonicalizar": "Se quita el campo de firma del objeto y se serializa con JCS (RFC 8785). El resultado está en 'jcs_utf8_hex'.",
        "3_firmar": "Ed25519 (RFC 8032) sobre esos bytes exactos, en base64url sin relleno. Quien verifica comprueba la firma contra la clave publicada; no compara bytes de firma: una firma con azar es tan válida como la determinista.",
        "4_verificar": "python3 validar.py comprueba cada vector de este archivo.",
    },
    "referencias": {
        "canonicalizacion": "RFC 8785 (JCS)",
        "firma": "RFC 8032 (Ed25519)",
        "firma_http": "RFC 9421 (HTTP Message Signatures), único mecanismo; sin draft-cavage ni double-knocking",
        "digest": "RFC 9530 (Content-Digest)",
    },
    "claves": [
        {"actor": actor, "etiqueta_semilla": et, "semilla_sha256_de": f"vereda:vector:{et}",
         "semilla_hex": semilla(et).hex(), "clave_publica": clave(et)[1]}
        for actor, et in ACTORES.items()
    ] + [
        {"actor": "marta@vereda.ar (clave anterior, rotada)", "etiqueta_semilla": "marta-clave-1",
         "semilla_sha256_de": "vereda:vector:marta-clave-1", "semilla_hex": semilla("marta-clave-1").hex(), "clave_publica": pub_vieja},
        {"actor": "marta@vereda.ar (clave nueva del vector de rotación)", "etiqueta_semilla": "marta-clave-2",
         "semilla_sha256_de": "vereda:vector:marta-clave-2", "semilla_hex": semilla("marta-clave-2").hex(), "clave_publica": pub_nueva},
    ],
    "vectores": [v_resena, v_resena_marcada, v_clave, v_evento, v_mudanza, v_vinculacion, v_traspaso, v_recepcion, v_rendicion],
    "casos_jcs": casos_jcs,
    "rfc9421": rfc9421,
    "firma_fresca": firma_fresca,
}
ruta = os.path.join(BASE, "ejemplos", "vectores-firma.json")
open(ruta, "w").write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"escrito {ruta}: {len(doc['vectores'])} vectores firmados, {len(casos_jcs)} casos JCS, 1 request RFC 9421 y 1 firma fresca")

# --- Acceso y respaldo de la clave (docs/acceso.md) ---
import unicodedata
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

k_marta, pub_marta = clave("marta")
desafio = b64u(hashlib.sha256(b"vereda:vector:desafio").digest())
prueba = {"clave_publica": pub_marta, "desafio": desafio, "nodo": "vereda.ar"}
jcs_prueba = rfc8785.dumps(prueba)
firma_prueba = b64u(k_marta.sign(jcs_prueba))

crudo_marta = k_marta.public_key().public_bytes(sz.Encoding.Raw, sz.PublicFormat.Raw)
local = base64.b32encode(hashlib.sha256(crudo_marta).digest()[:10]).decode().rstrip("=").lower()

ITERACIONES = 600_000
# v3: la frase se normaliza a NFKD antes de derivar (como BIP-39), así un
# teclado que compone la ñ o la tilde distinto no deja a nadie afuera de su
# propio respaldo. El vector trae la misma frase en las dos formas en que la
# producen los teclados: compuesta (NFC) y descompuesta (NFD).
FRASE = unicodedata.normalize("NFC", "Ñandú, pingüino y café en la vereda")
FRASE_OTRA_FORMA = unicodedata.normalize("NFD", FRASE)
FRASE_MALA = "Nandu, pinguino y cafe en la vereda"
# v2 derivaba de la frase tal cual, sin normalizar: su vector usa una frase
# sin acentos para que no haya ambigüedad.
FRASE_V2 = "la vereda de enfrente"
NORMALIZACION = {"vereda.clave.v3": "NFKD", "vereda.clave.v2": None}
x_marta = semilla("marta-cifrado")
x_pub = b64u(X25519PrivateKey.from_private_bytes(x_marta).public_key().public_bytes(sz.Encoding.Raw, sz.PublicFormat.Raw))

def bytes_de_frase(formato, frase):
    forma = NORMALIZACION[formato]
    return (unicodedata.normalize(forma, frase) if forma else frase).encode()

def llave_de(formato, frase, sal, iteraciones):
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal, iterations=iteraciones)
    return kdf.derive(bytes_de_frase(formato, frase))

def respaldo(formato, texto_claro, sal, nonce, extra):
    cabecera = {"formato": formato, "clave_publica": pub_marta, **extra, "identidad": "marta@vereda.ar", "creada": TS,
                "kdf": {"nombre": "PBKDF2", "hash": "SHA-256", "iteraciones": ITERACIONES, "sal": b64u(sal)}}
    aad = rfc8785.dumps(cabecera)
    frase = FRASE if formato == "vereda.clave.v3" else FRASE_V2
    llave = llave_de(formato, frase, sal, ITERACIONES)
    texto = AESGCM(llave).encrypt(nonce, texto_claro, aad)
    return {
        "frase": frase,
        **({"frase_otra_forma": FRASE_OTRA_FORMA} if formato == "vereda.clave.v3" else {}),
        "normalizacion": NORMALIZACION[formato] or "ninguna",
        "frase_kdf_utf8_hex": bytes_de_frase(formato, frase).hex(),
        "frase_incorrecta": FRASE_MALA,
        "llave_hex": llave.hex(),
        "aad_jcs_utf8_hex": aad.hex(),
        "texto_claro_hex": texto_claro.hex(),
        "respaldo": {**cabecera, "cifrado": {"nombre": "AES-GCM", "nonce": b64u(nonce), "texto": b64u(texto)}},
    }

texto_v3 = rfc8785.dumps({"firma": b64u(semilla("marta")), "cifrado": b64u(x_marta)})
acceso = {
    "$comentario": "Vectores de acceso y respaldo del Protocolo Vereda (docs/acceso.md). Una app o un nodo conforme reproduce byte a byte el JCS, la identidad derivada, la llave PBKDF2 y el texto claro, y verifica la firma contra la clave publicada: Ed25519 puede firmar con azar (CryptoKit lo hace) y una firma distinta pero válida es conforme. Regenerar: python3 generar-vectores.py.",
    "version_esquema": "1.0",
    "clave": {"actor": "marta@vereda.ar", "semilla_sha256_de": "vereda:vector:marta", "clave_publica": pub_marta,
              "cifrado_sha256_de": "vereda:vector:marta-cifrado", "clave_cifrado": x_pub},
    "prueba_de_clave": {
        "descripcion": "Lo que firma el dispositivo para canjear un desafío en POST /acceso/sesion.",
        "desafio": {"desafio": desafio, "vence": "2026-09-21T18:06:05Z", "nodo": "vereda.ar"},
        "objeto": prueba,
        "jcs_utf8_hex": jcs_prueba.hex(),
        "pedido_sesion": {"clave_publica": pub_marta, "desafio": desafio, "firma": firma_prueba, "nombre": "Marta"},
    },
    "identidad_derivada": {
        "descripcion": "Recomendada, no obligatoria: la identidad la acuña el nodo. base32 sin relleno, en minúscula, de los primeros 10 bytes del SHA-256 de la clave pública cruda, arroba el dominio del nodo.",
        "clave_publica": pub_marta,
        "identidad": f"{local}@vereda.ar",
    },
    "respaldos": [
        {"nombre": "respaldo-v3", "descripcion": "Formato actual: semilla Ed25519 y clave X25519 del chat. El texto claro es el JCS de {firma, cifrado}.",
         **respaldo("vereda.clave.v3", texto_v3, semilla("respaldo-sal-v3")[:16], semilla("respaldo-nonce-v3")[:12], {"clave_cifrado": x_pub})},
        {"nombre": "respaldo-v2", "descripcion": "Formato anterior, solo lectura: el texto claro es la semilla Ed25519 cruda, sin clave de chat.",
         **respaldo("vereda.clave.v2", semilla("marta"), semilla("respaldo-sal-v2")[:16], semilla("respaldo-nonce-v2")[:12], {})},
    ],
}
ruta = os.path.join(BASE, "ejemplos", "vectores-acceso.json")
open(ruta, "w").write(json.dumps(acceso, indent=2, ensure_ascii=False) + "\n")
print(f"escrito {ruta}: 1 prueba de clave, 1 identidad derivada, {len(acceso['respaldos'])} respaldos")
