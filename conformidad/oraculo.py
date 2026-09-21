"""Carga esquemas/*.json en un Registry de jsonschema.

Un solo lugar para esto: `validar.py` (offline, la spec contra sí misma) y
`conformidad/` (online, un nodo contra la spec) leen el mismo Registry en vez
de mantener dos copias del mismo loop.
"""
import glob
import json
import os

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

BASE_URI = "https://vereda.ar/esquemas/v1/"


def cargar(base):
    """base: la raíz del repo (donde vive esquemas/). Devuelve (esquemas, registry)."""
    esq_dir = os.path.join(base, "esquemas")
    registry = Registry()
    esquemas = {}
    for f in glob.glob(os.path.join(esq_dir, "*.json")):
        s = json.load(open(f))
        esquemas[os.path.basename(f)] = s
        registry = registry.with_resource(s["$id"], Resource.from_contents(s))
    return esquemas, registry


def validador(esquemas, registry, referencia):
    """referencia: 'oferta.json' (archivo completo) o 'comunes.json#/$defs/claves'
    (una parte). Siempre contra el mismo registry, para que los $ref internos
    entre esquemas resuelvan igual que en validar.py."""
    if "#" in referencia:
        esquema = {"$ref": BASE_URI + referencia}
    else:
        esquema = esquemas[referencia]
    return Draft202012Validator(esquema, registry=registry)
