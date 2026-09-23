"""Nivel A: caja negra, anónimo, de solo lectura.

Corre contra la URL de cualquier nodo sin pedirle permiso a nadie: es el
único nivel que da valor el día uno, antes de que exista una sola cuenta de
prueba. Ver docs/suite-conformidad.md.

Deuda conocida, a propósito: las ventanas de tiempo (carrito vence a las
24 h, `plazo_aceptacion_min`) no se prueban acá. Probarlas exigiría que el
nodo exponga un reloj de prueba, que es superficie nueva del protocolo y no
la decide este PR.
"""
import base64
import glob
import json
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional
from urllib.parse import quote, urlparse

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from jsonschema import Draft202012Validator

from . import cliente
from . import openapi_info as oi
from .oraculo import cargar as cargar_esquemas

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Buenos Aires, CABA: default razonable para un protocolo pensado para
# Argentina. --lat/--lng lo pisa para apuntar a un nodo de otra zona.
LAT_DEFECTO = -34.6037
LNG_DEFECTO = -58.3816

ID_INEXISTENTE = "01920000-0000-7000-8000-00000000dead"  # un UUIDv7 bien formado que no debería existir en ningún nodo
EAN_INEXISTENTE = "0000000000000"  # cumple el patrón de 8-14 dígitos; no debería existir en ningún catálogo


def _desde_b64u(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


@dataclass
class Caso:
    categoria: str  # estructura | esquema | errores | firmas | negativos
    operation_id: str
    descripcion: str
    resultado: str  # ok | fallo | omitido
    motivo: str = ""
    evidencia: dict = field(default_factory=dict)


# Campos que el firmante no escribió y que por eso quedan fuera del JCS
# (docs/claves-y-firmas.md): 'respuesta' la escribe el reseñado después, y
# 'senales' y 'visible' las escribe el nodo al recalcular. Si entraran, responder
# o marcar una reseña invalidaría la firma de quien la escribió.
_CAMPOS_FUERA_DE_LA_FIRMA = {"respuesta", "senales", "visible"}


def _ok(cat, opid, desc, evidencia=None) -> Caso:
    return Caso(cat, opid, desc, "ok", evidencia=evidencia or {})


def _fallo(cat, opid, desc, motivo, evidencia=None) -> Caso:
    return Caso(cat, opid, desc, "fallo", motivo=motivo, evidencia=evidencia or {})


def _omitido(cat, opid, desc, motivo) -> Caso:
    return Caso(cat, opid, desc, "omitido", motivo=motivo)


class NivelA:
    def __init__(self, origen, *, lat=LAT_DEFECTO, lng=LNG_DEFECTO, timeout=cliente.TIMEOUT_S, incluir_negativos=False):
        self.origen = origen.rstrip("/")
        self.base_v1 = self.origen + "/v1"
        self.lat, self.lng = lat, lng
        self.timeout = timeout
        self.incluir_negativos = incluir_negativos
        self.api = oi.cargar(BASE)
        self.esquemas, self.registry = cargar_esquemas(BASE)
        self.casos: List[Caso] = []

    # -- utilidades ------------------------------------------------------
    def _get(self, url, headers=None):
        return cliente.get(url, headers=headers, timeout=self.timeout)

    def _op(self, ruta, metodo="get"):
        return self.api["paths"][ruta][metodo]

    def _encontrar_op(self, operation_id):
        for _ruta, _metodo, op in oi.operaciones(self.api):
            if op.get("operationId") == operation_id:
                return op
        raise KeyError(operation_id)

    def _url(self, ruta_plantilla, **valores):
        ruta = ruta_plantilla
        for k, v in valores.items():
            ruta = ruta.replace("{" + k + "}", quote(str(v), safe=""))
        return self.base_v1 + ruta

    def _validar(self, esquema_resuelto, doc):
        v = Draft202012Validator(esquema_resuelto, registry=self.registry)
        return sorted(v.iter_errors(doc), key=lambda e: list(e.path))

    def _formatear_errores(self, errores, limite=5):
        return "; ".join(f"{'/'.join(map(str, e.path)) or '(raíz)'}: {e.message[:140]}" for e in errores[:limite])

    def _chequear_estructura(self, opid, desc, url, r) -> Caso:
        """ETag + Cache-Control en el 200, y 304 sin cuerpo al repetir con If-None-Match."""
        if r.estado != 200:
            return _fallo("estructura", opid, desc, f"esperaba 200, llegó {r.estado}")
        faltan = [h for h in ("ETag", "Cache-Control") if h not in r.cabeceras]
        if faltan:
            return _fallo("estructura", opid, desc, f"falta(n) cabecera(s) {', '.join(faltan)} en el 200")
        etag = r.cabeceras["ETag"]
        r2 = self._get(url, headers={"If-None-Match": etag})
        if not r2.ok:
            return _fallo("estructura", opid, desc, f"revalidar con If-None-Match: {r2.motivo}")
        if r2.estado != 304:
            return _fallo("estructura", opid, desc, f"con el If-None-Match del ETag recién visto, esperaba 304 y llegó {r2.estado}")
        return _ok("estructura", opid, desc, {"etag": etag})

    def _chequear_esquema(self, opid, desc, op, cuerpo, estado="200") -> Optional[Caso]:
        esquema = oi.esquema_respuesta(self.api, op, estado)
        if esquema is None:
            return None
        errores = self._validar(esquema, cuerpo)
        if errores:
            return _fallo("esquema", opid, desc, self._formatear_errores(errores))
        return _ok("esquema", opid, desc)

    def _esquema_o_no_json(self, opid, desc, op, r, estado="200") -> Optional[Caso]:
        """Como _chequear_esquema, pero primero deja explícito que un 200 con un
        cuerpo que no es JSON es un fallo -- no algo que se salta en silencio."""
        if str(r.estado) != estado:
            return None
        if not r.cuerpo_es_json:
            return _fallo("esquema", opid, desc, f"la respuesta {estado} no es JSON válido: {str(r.cuerpo)[:140]!r}")
        return self._chequear_esquema(opid, desc, op, r.cuerpo, estado)

    # -- corrida -----------------------------------------------------------
    def correr(self) -> List[Caso]:
        self.casos = []
        self._bien_conocido()
        self._sostenimiento()
        comercios = self._comercios()
        self._buscar()
        rondas = self._rondas()
        comercio = comercios[0] if comercios else None
        self._detalle_comercio(comercio)
        self._reputacion_comercio(comercio)
        ofertas = self._ofertas_comercio(comercio)
        self._detalle_oferta(ofertas)
        self._promociones_comercio(comercio)
        self._catalogo(ofertas)
        self._detalle_ronda(rondas)
        self._actor(comercio)
        self._errores()
        if self.incluir_negativos:
            self._negativos_sin_sesion()
        return self.casos

    # 1. estructura + esquema de las lecturas públicas ---------------------
    def _bien_conocido(self):
        # RFC 8615 y docs/federacion.md: .well-known vive en la raíz del dominio,
        # no bajo /v1. openapi.yaml no puede expresar un `servers` distinto por
        # operación y lista esta ruta junto a las demás -- ver el PR de este
        # archivo para la ambigüedad que eso deja en el spec.
        opid = "verNodo"
        op = self._op("/.well-known/vereda.json")
        url = self.origen + "/.well-known/vereda.json"
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, "GET /.well-known/vereda.json", r.motivo))
            return
        self.casos.append(self._chequear_estructura(opid, "GET /.well-known/vereda.json", url, r))
        caso = self._esquema_o_no_json(opid, "el cuerpo de /.well-known/vereda.json cumple Nodo", op, r)
        if caso:
            self.casos.append(caso)

    def _sostenimiento(self):
        # docs/sostenimiento.md: lo que el nodo recibe y gasta es público, sin token.
        opid = "verSostenimiento"
        op = self._op("/sostenimiento")
        url = self.base_v1 + "/sostenimiento"
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, "GET /sostenimiento", r.motivo))
            return
        self.casos.append(self._chequear_estructura(opid, "GET /sostenimiento", url, r))
        caso = self._esquema_o_no_json(opid, "el cuerpo de /sostenimiento cumple esquemas/sostenimiento.json", op, r)
        if caso:
            self.casos.append(caso)

    def _comercios(self):
        opid = "buscarComercios"
        op = self._op("/comercios")
        url = f"{self.base_v1}/comercios?lat={self.lat}&lng={self.lng}"
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, "GET /comercios", r.motivo))
            return []
        self.casos.append(self._chequear_estructura(opid, "GET /comercios", url, r))
        if r.estado != 200 or not r.cuerpo_es_json:
            self.casos.append(_fallo("esquema", opid, "el cuerpo de /comercios cumple un array de esquemas/comercio.json", f"estado {r.estado} no es 200 con JSON"))
            return []
        caso = self._chequear_esquema(opid, "el cuerpo de /comercios cumple un array de esquemas/comercio.json", op, r.cuerpo)
        if caso:
            self.casos.append(caso)
        if not isinstance(r.cuerpo, list) or not r.cuerpo:
            self.casos.append(_omitido(
                "esquema", "verComercio",
                "encadenar comercio -> ofertas -> catálogo -> actor",
                f"/comercios no devolvió ningún comercio para lat={self.lat}, lng={self.lng}; probá con --lat/--lng de una zona con datos"))
            return []
        return r.cuerpo

    def _buscar(self):
        opid = "buscarOfertas"
        op = self._op("/buscar")
        url = f"{self.base_v1}/buscar?lat={self.lat}&lng={self.lng}"
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, "GET /buscar", r.motivo))
            return
        self.casos.append(self._chequear_estructura(opid, "GET /buscar", url, r))
        caso = self._esquema_o_no_json(opid, "el cuerpo de /buscar cumple lo declarado en openapi.yaml", op, r)
        if caso:
            self.casos.append(caso)

    def _rondas(self):
        opid = "buscarRondas"
        op = self._op("/rondas")
        url = f"{self.base_v1}/rondas?lat={self.lat}&lng={self.lng}"
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, "GET /rondas", r.motivo))
            return []
        self.casos.append(self._chequear_estructura(opid, "GET /rondas", url, r))
        if r.estado != 200 or not r.cuerpo_es_json:
            self.casos.append(_fallo("esquema", opid, "el cuerpo de /rondas cumple un array de esquemas/ronda.json", f"estado {r.estado} no es 200 con JSON"))
            return []
        caso = self._chequear_esquema(opid, "el cuerpo de /rondas cumple un array de esquemas/ronda.json", op, r.cuerpo)
        if caso:
            self.casos.append(caso)
        return r.cuerpo if isinstance(r.cuerpo, list) else []

    def _detalle_ronda(self, rondas):
        opid = "verRonda"
        if not rondas:
            self.casos.append(_omitido("esquema", opid, "GET /rondas/{id}", "no hay rondas abiertas publicadas para encadenar"))
            return
        rid = rondas[0].get("id")
        if not rid:
            self.casos.append(_fallo("esquema", opid, "GET /rondas/{id}", "la ronda descubierta no trae 'id' (esquemas/comunes.json#/$defs/metadatos)"))
            return
        op = self._op("/rondas/{id}")
        url = self._url("/rondas/{id}", id=rid)
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, "GET /rondas/{id}", r.motivo))
            return
        self.casos.append(self._chequear_estructura(opid, "GET /rondas/{id}", url, r))
        caso = self._esquema_o_no_json(opid, "el cuerpo de /rondas/{id} cumple esquemas/ronda.json", op, r)
        if caso:
            self.casos.append(caso)

    def _detalle_comercio(self, comercio):
        opid = "verComercio"
        if comercio is None:
            self.casos.append(_omitido("esquema", opid, "GET /comercios/{id}", "no se descubrió ningún comercio en /comercios"))
            return
        cid = comercio.get("id")
        if not cid:
            self.casos.append(_fallo("esquema", opid, "GET /comercios/{id}", "el comercio descubierto no trae 'id' (esquemas/comunes.json#/$defs/metadatos)"))
            return
        op = self._op("/comercios/{id}")
        url = self._url("/comercios/{id}", id=cid)
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, "GET /comercios/{id}", r.motivo))
            return
        self.casos.append(self._chequear_estructura(opid, "GET /comercios/{id}", url, r))
        caso = self._esquema_o_no_json(opid, "el cuerpo de /comercios/{id} cumple esquemas/comercio.json", op, r)
        if caso:
            self.casos.append(caso)

    def _reputacion_comercio(self, comercio):
        """No alcanza con que el nodo devuelva un número: la reputación es una
        fórmula publicada (docs/resenas.md) y el desglose trae sus partes, así
        que se rehace la cuenta acá. Un nodo que devuelve 5,0 con un promedio de
        3,2 y recompra 0 no cumple el protocolo aunque el esquema valide."""
        opid = "verReputacion"
        if comercio is None:
            self.casos.append(_omitido("esquema", opid, "GET /comercios/{id}/reputacion", "no se descubrió ningún comercio en /comercios"))
            return
        cid = comercio.get("id")
        if not cid:
            self.casos.append(_fallo("esquema", opid, "GET /comercios/{id}/reputacion", "el comercio descubierto no trae 'id'"))
            return
        op = self._op("/comercios/{id}/reputacion")
        url = self._url("/comercios/{id}/reputacion", id=cid)
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, "GET /comercios/{id}/reputacion", r.motivo))
            return
        self.casos.append(self._chequear_estructura(opid, "GET /comercios/{id}/reputacion", url, r))
        caso = self._esquema_o_no_json(opid, "el cuerpo de /comercios/{id}/reputacion cumple resena.json#/$defs/reputacion_contextual", op, r)
        if caso:
            self.casos.append(caso)
        desc = "la reputación publicada es 0,7 · promedio + 0,3 · (1 + 4 · recompra)"
        if r.estado != 200 or not r.cuerpo_es_json or not isinstance(r.cuerpo, dict):
            self.casos.append(_fallo("esquema", opid, desc, f"estado {r.estado} no es 200 con un objeto JSON"))
            return
        partes = {k: r.cuerpo.get(k) for k in ("reputacion", "promedio", "recompra")}
        if any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in partes.values()):
            self.casos.append(_fallo("esquema", opid, desc, f"faltan o no son números las partes del desglose: {partes}"))
            return
        esperado = 0.7 * partes["promedio"] + 0.3 * (1 + 4 * partes["recompra"])
        if abs(esperado - partes["reputacion"]) > 0.02:
            self.casos.append(_fallo("esquema", opid, desc, f"con promedio {partes['promedio']} y recompra {partes['recompra']} la fórmula da {esperado:.3f}, el nodo publica {partes['reputacion']}"))
        else:
            self.casos.append(_ok("esquema", opid, desc, {"reputacion": partes["reputacion"], "promedio": partes["promedio"], "recompra": partes["recompra"]}))
        if not r.cuerpo.get("formula"):
            self.casos.append(_fallo("esquema", opid, "el desglose dice qué fórmula aplicó", "'formula' vacío o ausente: la reputación tiene que ser auditable sin leer la spec"))
        else:
            self.casos.append(_ok("esquema", opid, "el desglose dice qué fórmula aplicó"))

    def _ofertas_comercio(self, comercio):
        opid = "listarOfertas"
        if comercio is None:
            self.casos.append(_omitido("esquema", opid, "GET /comercios/{id}/ofertas", "no se descubrió ningún comercio"))
            return []
        cid = comercio.get("id")
        op = self._op("/comercios/{id}/ofertas")
        url = self._url("/comercios/{id}/ofertas", id=cid)
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, "GET /comercios/{id}/ofertas", r.motivo))
            return []
        self.casos.append(self._chequear_estructura(opid, "GET /comercios/{id}/ofertas", url, r))
        if r.estado != 200 or not r.cuerpo_es_json:
            self.casos.append(_fallo("esquema", opid, "el cuerpo de /comercios/{id}/ofertas cumple un array de esquemas/oferta.json", f"estado {r.estado} no es 200 con JSON"))
            return []
        caso = self._chequear_esquema(opid, "el cuerpo de /comercios/{id}/ofertas cumple un array de esquemas/oferta.json", op, r.cuerpo)
        if caso:
            self.casos.append(caso)
        return r.cuerpo if isinstance(r.cuerpo, list) else []

    def _detalle_oferta(self, ofertas):
        opid = "verOferta"
        oid = next((o.get("id") for o in (ofertas or []) if isinstance(o, dict) and o.get("id")), None)
        if not oid:
            self.casos.append(_omitido("esquema", opid, "GET /ofertas/{id}", "ninguna oferta descubierta en /comercios/{id}/ofertas para encadenar"))
            return
        op = self._op("/ofertas/{id}")
        url = self._url("/ofertas/{id}", id=oid)
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, "GET /ofertas/{id}", r.motivo))
            return
        self.casos.append(self._chequear_estructura(opid, "GET /ofertas/{id}", url, r))
        caso = self._esquema_o_no_json(opid, "el cuerpo de /ofertas/{id} cumple esquemas/oferta.json", op, r)
        if caso:
            self.casos.append(caso)
        desc = "GET /ofertas/{id} devuelve la oferta pedida, la misma que lista su comercio"
        if r.estado == 200 and r.cuerpo_es_json and isinstance(r.cuerpo, dict) and r.cuerpo.get("id") == oid:
            self.casos.append(_ok("esquema", opid, desc))
        else:
            self.casos.append(_fallo("esquema", opid, desc, f"pedí {oid}, llegó estado {r.estado} con id {(r.cuerpo or {}).get('id') if r.cuerpo_es_json and isinstance(r.cuerpo, dict) else '(sin id)'}"))

    def _promociones_comercio(self, comercio):
        opid = "listarPromociones"
        if comercio is None:
            self.casos.append(_omitido("esquema", opid, "GET /comercios/{id}/promociones", "no se descubrió ningún comercio"))
            return
        cid = comercio.get("id")
        op = self._op("/comercios/{id}/promociones")
        url = self._url("/comercios/{id}/promociones", id=cid)
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, "GET /comercios/{id}/promociones", r.motivo))
            return
        self.casos.append(self._chequear_estructura(opid, "GET /comercios/{id}/promociones", url, r))
        caso = self._esquema_o_no_json(opid, "el cuerpo de /comercios/{id}/promociones cumple un array de esquemas/promocion.json", op, r)
        if caso:
            self.casos.append(caso)

    def _catalogo(self, ofertas):
        opid = "verProductoDeCatalogo"
        ean = next((o.get("ean") for o in (ofertas or []) if o.get("ean")), None)
        if not ean:
            self.casos.append(_omitido("esquema", opid, "GET /catalogo/{ean}", "ninguna oferta descubierta trae 'ean' para probar un EAN real"))
            return
        op = self._op("/catalogo/{ean}")
        url = self._url("/catalogo/{ean}", ean=ean)
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, "GET /catalogo/{ean}", r.motivo))
            return
        if r.estado == 404:
            # carrera entre el momento en que listamos la oferta y esta llamada, o el
            # nodo no replica su propio EAN en /catalogo -- no es una falla de la suite.
            self.casos.append(_omitido("esquema", opid, "GET /catalogo/{ean}", f"404 para el EAN {ean} que una oferta de este mismo nodo acababa de publicar"))
            return
        self.casos.append(self._chequear_estructura(opid, "GET /catalogo/{ean}", url, r))
        caso = self._esquema_o_no_json(opid, "el cuerpo de /catalogo/{ean} cumple esquemas/catalogo-maestro.json", op, r)
        if caso:
            self.casos.append(caso)

    def _actor(self, comercio):
        if comercio is None:
            for opid in ("listarClavesDeActor", "verMudanzaDeActor", "listarResenasDeActor", "verVerificacion", "listarAtestaciones", "listarDenuncias"):
                self.casos.append(_omitido("esquema", opid, f"{opid} con la identidad de un comercio real", "no se descubrió ningún comercio en este nodo"))
            return
        identidad = comercio.get("identidad")
        if not identidad:
            self.casos.append(_fallo("esquema", "verComercio", "el comercio descubierto trae 'identidad'", "requerido por esquemas/comercio.json y no está"))
            return
        self._actor_claves(identidad)
        self._actor_mudanza(identidad)
        self._firmas_reales(comercio, identidad)
        self._identidad_verificable(identidad)

    def _actor_claves(self, identidad):
        opid = "listarClavesDeActor"
        op = self._op("/actores/{identidad}/claves")
        url = self._url("/actores/{identidad}/claves", identidad=identidad)
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, f"GET /actores/{identidad}/claves", r.motivo))
            return
        if r.estado == 404:
            self.casos.append(_fallo("esquema", opid, f"GET /actores/{identidad}/claves", "404 para un comercio que el propio nodo acaba de listar en /comercios"))
            return
        self.casos.append(self._chequear_estructura(opid, f"GET /actores/{identidad}/claves", url, r))
        caso = self._esquema_o_no_json(opid, f"el historial de claves de {identidad} cumple comunes.json#/$defs/claves", op, r)
        if caso:
            self.casos.append(caso)

    def _actor_mudanza(self, identidad):
        opid = "verMudanzaDeActor"
        op = self._op("/actores/{identidad}/mudanza")
        url = self._url("/actores/{identidad}/mudanza", identidad=identidad)
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, f"GET /actores/{identidad}/mudanza", r.motivo))
            return
        if r.estado == 404:
            self.casos.append(_ok("esquema", opid, f"GET /actores/{identidad}/mudanza responde 404 (no se mudó, el caso esperable)"))
            return
        self.casos.append(self._chequear_estructura(opid, f"GET /actores/{identidad}/mudanza", url, r))
        caso = self._esquema_o_no_json(opid, f"la mudanza de {identidad} cumple comunes.json#/$defs/mudanza", op, r)
        if caso:
            self.casos.append(caso)

    def _lectura_de_actor(self, opid, ruta, identidad, desc_esquema):
        """GET público de /actores/{identidad}/...: estructura de caché y esquema.
        Devuelve el cuerpo si es un 200 con JSON, para seguir con las firmas."""
        op = self._op(ruta)
        url = self._url(ruta, identidad=identidad)
        desc = "GET " + ruta.replace("{identidad}", identidad)
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, desc, r.motivo))
            return None
        self.casos.append(self._chequear_estructura(opid, desc, url, r))
        caso = self._esquema_o_no_json(opid, desc_esquema, op, r)
        if caso:
            self.casos.append(caso)
        return r.cuerpo if r.estado == 200 and r.cuerpo_es_json else None

    def _identidad_verificable(self, identidad):
        """docs/identidad-y-verificacion.md: nada lo otorga nadie, todo se
        recomprueba. La suite rehace lo que se puede rehacer sin salir de HTTP:
        cada declaración, atestación y denuncia está firmada por su autor. Deuda
        conocida: la firma del nodo sobre el documento entero no se verifica acá,
        y las pruebas que viven afuera (DNS, una página, un perfil) tampoco:
        exigirían red hacia terceros."""
        cache_claves = {}
        ver = self._lectura_de_actor("verVerificacion", "/actores/{identidad}/verificacion", identidad,
                                     f"la verificación de {identidad} cumple comunes.json#/$defs/verificacion_de_actor")
        if isinstance(ver, dict):
            vinculaciones = ver.get("vinculaciones") or []
            if not vinculaciones:
                self.casos.append(_omitido("firmas", "verVerificacion", "verificar la firma de cada vinculación declarada", f"{identidad} no declaró ninguna vinculación"))
            for v in vinculaciones[:25]:
                if not isinstance(v, dict):
                    self.casos.append(_fallo("firmas", "verVerificacion", "cada vinculación es un objeto", f"llegó {str(v)[:60]!r}"))
                    continue
                desc = f"firma de la vinculación {v.get('tipo', '?')} {v.get('valor', '')} de {v.get('identidad', '?')}".rstrip()
                if v.get("identidad") != identidad:
                    self.casos.append(_fallo("firmas", "verVerificacion", desc, f"la declara {v.get('identidad')!r}, no {identidad}"))
                    continue
                ok, motivo = self._verificar_firma(v, cache_claves)
                self.casos.append(_ok("firmas", "verVerificacion", desc) if ok else _fallo("firmas", "verVerificacion", desc, motivo))
        for opid, ruta, esquema, que in (
            ("listarAtestaciones", "/actores/{identidad}/atestaciones", "comunes.json#/$defs/atestacion", "atestación"),
            ("listarDenuncias", "/actores/{identidad}/denuncias", "denuncia.json", "denuncia"),
        ):
            lista = self._lectura_de_actor(opid, ruta, identidad, f"el cuerpo de {ruta} cumple un array de {esquema}")
            if not isinstance(lista, list):
                continue
            if not lista:
                self.casos.append(_omitido("firmas", opid, f"verificar la firma de cada {que}", f"{identidad} no tiene ninguna publicada"))
            for obj in lista[:25]:
                if not isinstance(obj, dict):
                    self.casos.append(_fallo("firmas", opid, f"cada {que} es un objeto", f"llegó {str(obj)[:60]!r}"))
                    continue
                autor = obj.get("autor") or obj.get("denunciante") or "?"
                ok, motivo = self._verificar_firma(obj, cache_claves)
                desc = f"firma de la {que} de {autor} sobre {identidad}"
                self.casos.append(_ok("firmas", opid, desc) if ok else _fallo("firmas", opid, desc, motivo))

    # 2. errores con identificadores que no existen -------------------------
    def _errores(self):
        dominio = urlparse(self.origen).hostname or "vereda.ar"
        identidad_inexistente = f"no-existe-conformidad@{dominio}"
        objetivos = [
            ("verProductoDeCatalogo", self._url("/catalogo/{ean}", ean=EAN_INEXISTENTE), "404"),
            ("listarClavesDeActor", self._url("/actores/{identidad}/claves", identidad=identidad_inexistente), "404"),
            ("verOferta", self._url("/ofertas/{id}", id=ID_INEXISTENTE), "404"),
        ]
        for opid, url, estado_esperado in objetivos:
            op = self._encontrar_op(opid)
            desc = f"{opid} con un identificador inexistente responde {estado_esperado}"
            r = self._get(url)
            if not r.ok:
                self.casos.append(_fallo("errores", opid, desc, r.motivo))
                continue
            if str(r.estado) != estado_esperado:
                self.casos.append(_fallo("errores", opid, desc, f"esperaba {estado_esperado}, llegó {r.estado}"))
                continue
            esquema_error = oi.esquema_respuesta(self.api, op, estado_esperado)
            if esquema_error is None:
                self.casos.append(_ok("errores", opid, desc, {"nota": "openapi.yaml no declara cuerpo para este estado; solo se comprobó el código"}))
                continue
            if not r.cuerpo_es_json:
                self.casos.append(_fallo("errores", opid, desc, "el cuerpo no es JSON"))
                continue
            errores = self._validar(esquema_error, r.cuerpo)
            if errores:
                self.casos.append(_fallo("errores", opid, desc, self._formatear_errores(errores)))
            else:
                self.casos.append(_ok("errores", opid, desc + " con esquemas/error.json"))

    # 3. firmas reales de reseñas públicas, sin fixtures ---------------------
    def _firmas_reales(self, comercio, identidad):
        opid = "listarResenasDeActor"
        op = self._op("/actores/{identidad}/resenas")
        url = self._url("/actores/{identidad}/resenas", identidad=identidad)
        r = self._get(url)
        if not r.ok:
            self.casos.append(_fallo("estructura", opid, f"GET /actores/{identidad}/resenas", r.motivo))
            return
        self.casos.append(self._chequear_estructura(opid, f"GET /actores/{identidad}/resenas", url, r))
        if r.estado != 200 or not r.cuerpo_es_json or not isinstance(r.cuerpo, list):
            self.casos.append(_fallo("esquema", opid, "el cuerpo de /actores/{identidad}/resenas cumple un array de esquemas/resena.json", f"estado {r.estado} no es 200 con un array JSON"))
            return
        caso = self._chequear_esquema(opid, "el cuerpo de /actores/{identidad}/resenas cumple un array de esquemas/resena.json", op, r.cuerpo)
        if caso:
            self.casos.append(caso)
        if not r.cuerpo:
            self.casos.append(_omitido("firmas", opid, "verificar la firma de reseñas públicas", f"{identidad} no tiene reseñas públicas todavía"))
            return
        cache_claves = {}
        MAX_RESENAS = 25
        for resena in r.cuerpo[:MAX_RESENAS]:
            desc = f"firma de la reseña de {resena.get('autor', '?')} sobre {resena.get('destinatario', '?')}"
            ok, motivo = self._verificar_firma(resena, cache_claves)
            self.casos.append(_ok("firmas", opid, desc) if ok else _fallo("firmas", opid, desc, motivo))

    def _claves_de(self, identidad):
        """GET .../actores/{identidad}/claves en el nodo DE ESE ACTOR, que puede
        ser distinto del nodo bajo prueba: es la parte que prueba interoperabilidad
        real entre nodos, no algo que la suite pueda fijar de antemano. Si el actor
        vive en el mismo dominio que se está probando (el caso común: reseñas entre
        vecinos del mismo nodo), se usa ese mismo origen, con su esquema y su
        puerto, en vez de forzar https -- para poder probar un nodo de desarrollo
        sin TLS ni puerto 443.
        Un dominio distinto es federación real entre nodos y siempre va por https."""
        if "@" not in identidad:
            return None
        dominio = identidad.split("@", 1)[1]
        mismo_nodo = dominio == urlparse(self.origen).hostname
        base = self.origen if mismo_nodo else f"https://{dominio}"
        url = f"{base}/v1/actores/{quote(identidad, safe='')}/claves"
        r = self._get(url)
        if not r.ok or r.estado != 200 or not r.cuerpo_es_json or not isinstance(r.cuerpo, list):
            return None
        return r.cuerpo

    def _verificar_firma(self, obj, cache_claves, campo_firma="firma"):
        """Cripto (JCS + Ed25519) más presencia y ventana en el historial del
        firmante. No reproduce el paso 4 completo de docs/claves-y-firmas.md
        (clave 'comprometida' + 'ya registrado antes de'): una corrida sin
        estado entre ejecuciones no tiene con qué compararlo. Deuda conocida,
        documentada, no una aproximación silenciosa."""
        firma = obj.get(campo_firma)
        if not isinstance(firma, dict):
            return False, f"no tiene '{campo_firma}'"
        try:
            clave_publica, valor, firmante, instante = firma["clave_publica"], firma["valor"], firma["firmante"], firma["instante"]
        except KeyError as e:
            return False, f"a la firma le falta el campo {e}"
        sin_firma = {k: v for k, v in obj.items() if k not in _CAMPOS_FUERA_DE_LA_FIRMA and k != campo_firma}
        try:
            jcs = rfc8785.dumps(sin_firma)
        except (TypeError, ValueError) as e:
            return False, f"no se pudo canonicalizar (JCS) el objeto sin firma: {e}"
        try:
            Ed25519PublicKey.from_public_bytes(_desde_b64u(clave_publica)).verify(_desde_b64u(valor), jcs)
        except (InvalidSignature, ValueError):
            return False, "firma_invalida: no verifica contra su propia 'clave_publica'"
        if firmante not in cache_claves:
            cache_claves[firmante] = self._claves_de(firmante)
        claves = cache_claves[firmante]
        if claves is None:
            return False, f"no se pudo obtener el historial de claves de {firmante} (¿nodo de {firmante.split('@')[-1] if '@' in firmante else '?'} caído o incompatible?)"
        entrada = next((c for c in claves if c.get("clave_publica") == clave_publica), None)
        if entrada is None:
            return False, f"clave_desconocida: esa clave_publica no está en el historial de {firmante}"
        desde, hasta = entrada.get("desde"), entrada.get("hasta")
        if desde and instante < desde:
            return False, f"el instante de la firma es anterior a 'desde' de esa clave en el historial de {firmante}"
        if hasta and instante > hasta:
            return False, f"el instante de la firma es posterior a 'hasta' de esa clave en el historial de {firmante}"
        return True, ""

    # 4. negativos sin sesión, generados desde ejemplos/casos/*.json -------
    def _operaciones_de_escritura_por_esquema(self):
        """Para cada archivo de ejemplos/casos/*.json, la operación (si existe)
        cuyo requestBody es exactamente ese esquema completo -- no un sub-campo.
        Se arma leyendo openapi.yaml, no a mano: si mañana una operación nueva
        toma 'promocion.json' como cuerpo, este método la encuentra solo."""
        mapa = {}
        for ruta, metodo, op in oi.operaciones(self.api):
            if metodo not in ("post", "put", "patch") or op.get("security") == []:
                continue
            esquema_cuerpo = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
            ref = esquema_cuerpo.get("$ref", "")
            if ref.startswith("esquemas/") and "#" not in ref:
                mapa.setdefault(ref[len("esquemas/"):], (ruta, metodo, op))
        return mapa

    def _negativos_sin_sesion(self):
        mapa = self._operaciones_de_escritura_por_esquema()
        for archivo in sorted(glob.glob(os.path.join(BASE, "ejemplos", "casos", "*.json"))):
            suite = json.load(open(archivo))
            esquema, nombre = suite["esquema"], os.path.basename(archivo)
            if "#" in esquema:
                self.casos.append(_omitido("negativos", esquema, f"casos de {nombre} sin sesión", "es un sub-campo (#...), no el cuerpo completo de ninguna operación de escritura"))
                continue
            objetivo = mapa.get(esquema)
            if objetivo is None:
                self.casos.append(_omitido("negativos", esquema, f"casos de {nombre} sin sesión", f"ninguna operación de openapi.yaml toma '{esquema}' completo como cuerpo de request"))
                continue
            ruta, metodo, op = objetivo
            # las rutas con {parametro} se mandan con un id inexistente: sin sesión, el
            # nodo tiene que responder 401 antes de mirar si ese id existe.
            opid = op["operationId"]
            url = self.base_v1 + re.sub(r"\{[^}]+\}", "no-existe", ruta)
            for caso in suite["casos"]:
                desc = f"{metodo.upper()} {ruta} sin sesión, cuerpo {caso['espera']} de {nombre} ({caso['porque'][:70]})"
                r = cliente.solicitud(metodo, url, json_body=caso["doc"], timeout=self.timeout)
                if not r.ok:
                    self.casos.append(_fallo("negativos", opid, desc, r.motivo))
                elif r.estado == 401:
                    self.casos.append(_ok("negativos", opid, desc))
                else:
                    self.casos.append(_fallo("negativos", opid, desc, f"sin sesión, esperaba 401 y llegó {r.estado}"))


def correr(origen, **kwargs) -> List[Caso]:
    return NivelA(origen, **kwargs).correr()
