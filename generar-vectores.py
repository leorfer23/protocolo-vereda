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

def firmar(objeto, firmante, instante):
    """Firma JCS+Ed25519 sobre el objeto sin 'firma'. Devuelve el vector completo."""
    k, pub = clave(ACTORES[firmante])
    sin_firma = {c: v for c, v in objeto.items() if c not in ("firma", "firma_nodo")}
    jcs = rfc8785.dumps(sin_firma)
    firma = {"firmante": firmante, "clave_publica": pub, "valor": b64u(k.sign(jcs)), "instante": instante}
    return jcs, firma

def vector(nombre, descripcion, objeto, campo, firmante, instante, esquema):
    jcs, firma = firmar(objeto, firmante, instante)
    return {
        "nombre": nombre,
        "descripcion": descripcion,
        "esquema": esquema,
        "objeto_sin_firma": {c: v for c, v in objeto.items() if c != campo},
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

# --- 5. Casos JCS sin firma: donde las implementaciones se separan ---
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

# --- 6. Request RFC 9421 completo: una entrega entre nodos ---
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

doc = {
    "$comentario": "Vectores de prueba de firma del Protocolo Vereda. Una implementación conforme tiene que reproducir cada byte de este archivo.",
    "version_esquema": "1.0",
    "como_reproducir": {
        "1_semilla": "La clave privada de cada actor es Ed25519 a partir de la semilla SHA-256('vereda:vector:<etiqueta>'). Las etiquetas están en 'claves'. Son claves de prueba: nunca se usan en producción.",
        "2_canonicalizar": "Se quita el campo de firma del objeto y se serializa con JCS (RFC 8785). El resultado está en 'jcs_utf8_hex'.",
        "3_firmar": "Ed25519 (RFC 8032) sobre esos bytes exactos. La firma va en base64url sin relleno.",
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
    "vectores": [v_resena, v_clave, v_evento, v_mudanza],
    "casos_jcs": casos_jcs,
    "rfc9421": rfc9421,
}
ruta = os.path.join(BASE, "ejemplos", "vectores-firma.json")
open(ruta, "w").write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
print(f"escrito {ruta}: {len(doc['vectores'])} vectores firmados, {len(casos_jcs)} casos JCS, 1 request RFC 9421")
