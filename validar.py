#!/usr/bin/env python3
"""Valida los ejemplos contra los esquemas del Protocolo Vereda, y el OpenAPI."""
import json, sys, glob, os, yaml
from openapi_spec_validator import validate
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
    v = Draft202012Validator(esquemas[suite["esquema"]], registry=registry)
    mal = [c["porque"] for c in suite["casos"] if v.is_valid(c["doc"]) != (c["espera"] == "valido")]
    fallos += len(mal)
    for m in mal:
        print(f"✗ casos/{os.path.basename(f)}: {m}")
    print(f"{len(suite['casos']) - len(mal)}/{len(suite['casos'])} casos de {suite['esquema']} como se esperaba")

API = os.path.join(BASE, "openapi.yaml")
try:
    validate(yaml.safe_load(open(API)), base_uri="file://" + API)
    print("✓ openapi.yaml cumple OpenAPI 3.1")
except Exception as e:
    fallos += 1
    print(f"✗ openapi.yaml\n    {str(e).splitlines()[0][:200]}")
sys.exit(1 if fallos else 0)
