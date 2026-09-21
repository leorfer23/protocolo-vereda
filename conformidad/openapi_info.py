"""Lee openapi.yaml una vez y resuelve sus referencias para que jsonschema las
entienda, sin copiar a mano ningún esquema ni ninguna operación."""
import os

import yaml

METODOS = {"get", "post", "put", "patch", "delete"}


def cargar(base):
    with open(os.path.join(base, "openapi.yaml")) as f:
        return yaml.safe_load(f)


def operaciones(api):
    """Todas las operaciones, method+path+operationId+objeto crudo del spec."""
    for ruta, item in api["paths"].items():
        for metodo, op in item.items():
            if metodo in METODOS:
                yield ruta, metodo, op


def lecturas_publicas(api):
    """Los GET con `security: []`: las rutas que un nivel A anónimo puede probar."""
    return [(ruta, op) for ruta, metodo, op in operaciones(api) if metodo == "get" and op.get("security") == []]


def _resolver_puntero(api, ref):
    """'#/components/schemas/Nodo' -> el dict real en ese lugar de openapi.yaml."""
    nodo = api
    for parte in ref.lstrip("#/").split("/"):
        nodo = nodo[parte]
    return nodo


def resolver_esquema(api, fragmento, _visitados=frozenset()):
    """Reescribe un fragmento de esquema tal como aparece en openapi.yaml para que
    jsonschema lo pueda validar contra el Registry de conformidad.oraculo:

    - 'esquemas/x.json'               -> {'$ref': 'https://vereda.ar/esquemas/v1/x.json'}
    - 'esquemas/x.json#/$defs/y'      -> {'$ref': 'https://vereda.ar/esquemas/v1/x.json#/$defs/y'}
    - '#/components/...' (interno al propio openapi.yaml) -> se resuelve inline

    El resto (type, properties, items, enum...) se copia tal cual.
    """
    if isinstance(fragmento, dict):
        ref = fragmento.get("$ref")
        if isinstance(ref, str):
            if ref.startswith("esquemas/"):
                return {"$ref": "https://vereda.ar/esquemas/v1/" + ref[len("esquemas/"):]}
            if ref.startswith("#/"):
                if ref in _visitados:
                    return {}
                objetivo = _resolver_puntero(api, ref)
                return resolver_esquema(api, objetivo, _visitados | {ref})
            return dict(fragmento)
        return {k: resolver_esquema(api, v, _visitados) for k, v in fragmento.items()}
    if isinstance(fragmento, list):
        return [resolver_esquema(api, v, _visitados) for v in fragmento]
    return fragmento


def esquema_respuesta(api, op, estado="200"):
    """El JSON Schema, ya resuelto, del cuerpo `application/json` de una respuesta.
    None si esa respuesta no está declarada o no tiene cuerpo (ej. un 204)."""
    resp = op.get("responses", {}).get(estado)
    if not resp:
        return None
    esquema = resp.get("content", {}).get("application/json", {}).get("schema")
    if esquema is None:
        return None
    return resolver_esquema(api, esquema)


def declara(op, estado):
    return estado in op.get("responses", {})
