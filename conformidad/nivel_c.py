"""Nivel C: la suite actúa como nodo par y entrega eventos de federación
firmados a POST /federacion/entrantes. Ver docs/suite-conformidad.md.

Identidad de prueba: la de 'nodo.rosario.coop' publicada en
ejemplos/vectores-firma.json -- no hace falta que nadie entregue nada, la
clave ya está ahí a propósito ("cualquiera llega a la misma clave privada
sin que se la pasemos", docs/claves-y-firmas.md).

Aviso importante, para leer el reporte con la cabeza puesta: contra un nodo
real que no confía explícitamente en esta identidad de prueba (porque no
resuelve `nodo.rosario.coop` o no la tiene seedeada como par de un entorno
de conformidad), TODO este nivel puede volver 401 de punta a punta -- y eso
también es información: es exactamente lo que un nodo bien hecho debería
hacer frente a un emisor que no puede verificar. Un nodo que en cambio
acepta el evento sin poder verificarlo, o rompe con un 500, tiene un
problema real. Por eso cada prueba que depende de que el evento haya sido
aceptado se omite (no falla) si el primer envío no dio 202: no hay manera
honesta de probar idempotencia u orden sobre algo que el nodo rechazó.
"""
import base64
import os
import time
from typing import List, Optional

import rfc8785
from cryptography.hazmat.primitives import serialization as sz
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from . import cliente, evento_federacion, rfc9421, vectores
from .nivel_a import Caso, _fallo, _ok, _omitido

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

IDENTIDAD_NODO_PRUEBA = "nodo.rosario.coop"
VERSION_INEXISTENTE = "1.999999"  # cumple el patrón ^1\.[0-9]+$; ningún nodo real la va a soportar
CODIGOS_401_FEDERACION = {"firma_invalida", "clave_desconocida", "clave_comprometida"}


def _id_v7(offset_ms=0):
    """UUID v7-ish: ordenable por tiempo, cumple comunes.json#/$defs/id.
    No hace falta que sea un v7 de verdad (no se prueba su monotonicidad
    acá); alcanza con cumplir el patrón que exige el esquema."""
    ahora_ms = int(time.time() * 1000) + offset_ms
    ts = ahora_ms.to_bytes(6, "big", signed=False)
    resto = os.urandom(10)
    b = bytearray(ts + resto)
    b[6] = 0x70 | (b[6] & 0x0F)
    b[8] = 0x80 | (b[8] & 0x3F)
    h = b.hex()
    return f"{h[0:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:32]}"


def _instante():
    return time.strftime("%Y-%m-%dT%H:%M:%S-03:00", time.gmtime())


class NivelC:
    def __init__(self, origen, *, timeout=cliente.TIMEOUT_S):
        self.origen = origen.rstrip("/")
        self.base_v1 = self.origen + "/v1"
        self.timeout = timeout
        self.vectores = vectores.cargar(BASE)
        self.clave_privada, self.clave_publica = vectores.clave_privada_de(self.vectores, IDENTIDAD_NODO_PRUEBA)
        self.url = self.base_v1 + "/federacion/entrantes"
        self.version = self._descubrir_version()
        self.casos: List[Caso] = []

    # -- utilidades ---------------------------------------------------------
    def _descubrir_version(self) -> str:
        """Una versión que el nodo probablemente soporte, para los casos que
        no están probando la negociación de versión en sí. Si no se puede
        leer .well-known, 1.0 es la apuesta razonable (openapi.yaml: version: '1.0')."""
        r = cliente.get(self.origen + "/.well-known/vereda.json", timeout=self.timeout)
        if r.ok and r.estado == 200 and r.cuerpo_es_json and isinstance(r.cuerpo, dict):
            versiones = r.cuerpo.get("versiones")
            if isinstance(versiones, list) and versiones:
                return versiones[0]
        return "1.0"

    def _evento_base(self, *, entidad_id=None, secuencia=1, tipo="pedido.aceptado", datos=None):
        return {
            "id": _id_v7(),
            "tipo": tipo,
            "instante": _instante(),
            "nodo": IDENTIDAD_NODO_PRUEBA,
            "entidad": {"tipo": "pedido", "id": entidad_id or _id_v7()},
            "actor": f"vecino-de-prueba@{IDENTIDAD_NODO_PRUEBA}",
            "datos": datos if datos is not None else {"estado": "aceptado"},
            "secuencia": secuencia,
        }

    def _enviar(self, evento_sin_firma, *, clave_privada=None, clave_publica=None, dominio_emisor=None, vereda_version=None, keyid=None):
        """Firma el evento (firma_nodo) y el request (RFC 9421) y lo entrega.
        Los parámetros por default son la identidad de prueba real; se pisan
        uno por uno para fabricar cada escenario roto a propósito."""
        clave_privada = clave_privada or self.clave_privada
        clave_publica = clave_publica or self.clave_publica
        dominio_emisor = dominio_emisor or IDENTIDAD_NODO_PRUEBA
        vereda_version = vereda_version or self.version
        keyid = keyid or self.clave_publica

        _firmado, cuerpo = evento_federacion.firmar_evento(
            evento_sin_firma, clave_privada=clave_privada, clave_publica_b64u=clave_publica, dominio_emisor=dominio_emisor
        )
        cabeceras = rfc9421.firmar_pedido(
            metodo="POST", url=self.url, cuerpo=cuerpo, vereda_version=vereda_version, clave_privada=clave_privada, keyid=keyid
        )
        return cliente.solicitud_cruda("POST", self.url, headers=cabeceras, cuerpo=cuerpo, timeout=self.timeout)

    def _es_401_de_federacion(self, r) -> Optional[str]:
        """None si el 401 tiene la forma que pide openapi.yaml; si no, el motivo."""
        if r.estado != 401:
            return f"esperaba 401, llegó {r.estado}"
        if not r.cuerpo_es_json or not isinstance(r.cuerpo, dict):
            return "401 sin cuerpo esquemas/error.json"
        codigo = r.cuerpo.get("codigo")
        if codigo not in CODIGOS_401_FEDERACION:
            return f"401 con codigo {codigo!r}, no uno de {sorted(CODIGOS_401_FEDERACION)}"
        return None

    # -- corrida --------------------------------------------------------------
    def correr(self) -> List[Caso]:
        self.casos = []
        aceptado = self._identidad_de_prueba()
        self._firma_http_invalida()
        self._firma_de_evento_invalida()
        self._clave_desconocida()
        self._idempotencia(aceptado)
        self._orden(aceptado)
        self._version()
        return self.casos

    # 1. la identidad de prueba, aceptada o rechazada mano a mano ------------
    def _identidad_de_prueba(self) -> bool:
        evento = self._evento_base(secuencia=1)
        r = self._enviar(evento)
        opid = "recibirFederacion"
        desc = f"entregar un evento firmado como {IDENTIDAD_NODO_PRUEBA} (identidad de prueba de ejemplos/vectores-firma.json)"
        if not r.ok:
            self.casos.append(_fallo("identidad", opid, desc, r.motivo))
            return False
        if r.estado == 202:
            self.casos.append(_ok("identidad", opid, desc + ": 202, el nodo confía en esta identidad de prueba"))
            return True
        motivo_401 = self._es_401_de_federacion(r)
        if motivo_401 is None:
            self.casos.append(_ok("identidad", opid, desc + f": 401 bien formado ({r.cuerpo.get('codigo')}) -- este nodo no confía en la identidad de prueba, lo cual es una respuesta válida; idempotencia y orden quedan sin probar"))
            return False
        self.casos.append(_fallo("identidad", opid, desc, f"ni 202 ni un 401 bien formado: {motivo_401}"))
        return False

    # 2. firma HTTP (RFC 9421) inválida, evento por lo demás correcto --------
    def _firma_http_invalida(self):
        opid = "recibirFederacion"
        desc = "POST /federacion/entrantes con la firma HTTP RFC 9421 de otra clave (el evento adentro está firmado correctamente)"
        clave_ajena = Ed25519PrivateKey.generate()
        evento = self._evento_base(secuencia=1)
        # firma_nodo (adentro del evento) con la clave real; la firma HTTP del
        # transporte, con una clave distinta pero anunciando el keyid real.
        _firmado, cuerpo = evento_federacion.firmar_evento(evento, clave_privada=self.clave_privada, clave_publica_b64u=self.clave_publica, dominio_emisor=IDENTIDAD_NODO_PRUEBA)
        cabeceras = rfc9421.firmar_pedido(metodo="POST", url=self.url, cuerpo=cuerpo, vereda_version=self.version, clave_privada=clave_ajena, keyid=self.clave_publica)
        r = cliente.solicitud_cruda("POST", self.url, headers=cabeceras, cuerpo=cuerpo, timeout=self.timeout)
        if not r.ok:
            self.casos.append(_fallo("firma", opid, desc, r.motivo))
            return
        motivo = self._es_401_de_federacion(r)
        self.casos.append(_ok("firma", opid, desc) if motivo is None else _fallo("firma", opid, desc, motivo))

    # 3. firma_nodo (adentro del evento) inválida, transporte correcto -------
    def _firma_de_evento_invalida(self):
        opid = "recibirFederacion"
        desc = "POST /federacion/entrantes con firma_nodo del evento alterada después de firmarlo (el transporte RFC 9421 sí es correcto)"
        evento = self._evento_base(secuencia=1)
        firmado, _cuerpo_original = evento_federacion.firmar_evento(evento, clave_privada=self.clave_privada, clave_publica_b64u=self.clave_publica, dominio_emisor=IDENTIDAD_NODO_PRUEBA)
        # se corrompe la firma DESPUÉS de calcularla, y se recanonicaliza: el
        # transporte firma estos bytes nuevos, así que Content-Digest y la
        # firma RFC 9421 son consistentes con lo que viaja. Lo único roto es
        # firma_nodo.valor, que ya no verifica contra el objeto.
        firmado_roto = {**firmado, "firma_nodo": {**firmado["firma_nodo"], "valor": firmado["firma_nodo"]["valor"][:-4] + "Aaaa"}}
        cuerpo_roto = rfc8785.dumps(firmado_roto)
        cabeceras = rfc9421.firmar_pedido(metodo="POST", url=self.url, cuerpo=cuerpo_roto, vereda_version=self.version, clave_privada=self.clave_privada, keyid=self.clave_publica)
        r = cliente.solicitud_cruda("POST", self.url, headers=cabeceras, cuerpo=cuerpo_roto, timeout=self.timeout)
        if not r.ok:
            self.casos.append(_fallo("firma", opid, desc, r.motivo))
            return
        motivo = self._es_401_de_federacion(r)
        self.casos.append(_ok("firma", opid, desc) if motivo is None else _fallo("firma", opid, desc, motivo))

    def _clave_publica_de(self, clave_privada) -> str:
        cruda = clave_privada.public_key().public_bytes(sz.Encoding.Raw, sz.PublicFormat.Raw)
        return base64.urlsafe_b64encode(cruda).rstrip(b"=").decode()

    # 4. clave completamente desconocida --------------------------------------
    def _clave_desconocida(self):
        opid = "recibirFederacion"
        desc = "POST /federacion/entrantes firmado de punta a punta por una clave que nadie publicó nunca"
        clave_nueva = Ed25519PrivateKey.generate()
        clave_publica_nueva = self._clave_publica_de(clave_nueva)
        evento = self._evento_base(secuencia=1)
        r = self._enviar(evento, clave_privada=clave_nueva, clave_publica=clave_publica_nueva, dominio_emisor=IDENTIDAD_NODO_PRUEBA, keyid=clave_publica_nueva)
        if not r.ok:
            self.casos.append(_fallo("firma", opid, desc, r.motivo))
            return
        motivo = self._es_401_de_federacion(r)
        self.casos.append(_ok("firma", opid, desc) if motivo is None else _fallo("firma", opid, desc, motivo))

    # 5. idempotencia: mismo id + mismo contenido -> 202 de nuevo; -----------
    #    mismo id + otro contenido -> 409 -------------------------------------
    def _idempotencia(self, aceptado):
        opid = "recibirFederacion"
        if not aceptado:
            self.casos.append(_omitido("idempotencia", opid, "reentregar el mismo evento", "la identidad de prueba no fue aceptada; ver la categoría 'identidad'"))
            self.casos.append(_omitido("idempotencia", opid, "mismo id con otro contenido -> 409", "la identidad de prueba no fue aceptada; ver la categoría 'identidad'"))
            return
        evento = self._evento_base(entidad_id=_id_v7(), secuencia=1)
        r1 = self._enviar(evento)
        desc1 = f"un evento nuevo (id {evento['id'][:8]}...) se acepta"
        if not r1.ok or r1.estado != 202:
            self.casos.append(_fallo("idempotencia", opid, desc1, r1.motivo or f"esperaba 202, llegó {r1.estado}"))
            self.casos.append(_omitido("idempotencia", opid, "reentregar el mismo evento", "el envío original no dio 202"))
            self.casos.append(_omitido("idempotencia", opid, "mismo id con otro contenido -> 409", "el envío original no dio 202"))
            return
        self.casos.append(_ok("idempotencia", opid, desc1))

        r2 = self._enviar(evento)  # exactamente el mismo evento, de nuevo
        desc2 = "reentregar el mismo evento (mismo id, mismo contenido) vuelve a dar 202 sin duplicar nada"
        if not r2.ok:
            self.casos.append(_fallo("idempotencia", opid, desc2, r2.motivo))
        elif r2.estado == 202:
            self.casos.append(_ok("idempotencia", opid, desc2))
        else:
            self.casos.append(_fallo("idempotencia", opid, desc2, f"esperaba 202 de nuevo, llegó {r2.estado}"))

        evento_alterado = {**evento, "datos": {"estado": "otra-cosa-distinta"}}
        r3 = self._enviar(evento_alterado)
        desc3 = "el mismo id con otro contenido responde 409, no lo pisa"
        if not r3.ok:
            self.casos.append(_fallo("idempotencia", opid, desc3, r3.motivo))
        elif r3.estado == 409:
            self.casos.append(_ok("idempotencia", opid, desc3))
        else:
            self.casos.append(_fallo("idempotencia", opid, desc3, f"esperaba 409, llegó {r3.estado}"))

    # 6. orden: un salto de secuencia para la misma entidad -> 409 -----------
    def _orden(self, aceptado):
        opid = "recibirFederacion"
        desc = "un salto de secuencia para la misma entidad responde 409 secuencia_fuera_de_orden con detalle.ultima_secuencia"
        if not aceptado:
            self.casos.append(_omitido("orden", opid, desc, "la identidad de prueba no fue aceptada; ver la categoría 'identidad'"))
            return
        entidad_id = _id_v7()
        r1 = self._enviar(self._evento_base(entidad_id=entidad_id, secuencia=1))
        if not r1.ok or r1.estado != 202:
            self.casos.append(_omitido("orden", opid, desc, f"la secuencia 1 (línea de base) no se aceptó: {r1.motivo or r1.estado}"))
            return
        r2 = self._enviar(self._evento_base(entidad_id=entidad_id, secuencia=5))  # salta 2, 3 y 4
        if not r2.ok:
            self.casos.append(_fallo("orden", opid, desc, r2.motivo))
            return
        if r2.estado != 409:
            self.casos.append(_fallo("orden", opid, desc, f"esperaba 409, llegó {r2.estado}"))
            return
        if not r2.cuerpo_es_json or not isinstance(r2.cuerpo, dict) or "ultima_secuencia" not in r2.cuerpo.get("detalle", {}):
            self.casos.append(_fallo("orden", opid, desc, "409 sin detalle.ultima_secuencia"))
            return
        self.casos.append(_ok("orden", opid, desc, {"ultima_secuencia": r2.cuerpo["detalle"]["ultima_secuencia"]}))

    # 7. negociación de versión -----------------------------------------------
    def _version(self):
        opid = "recibirFederacion"
        desc = f"Vereda-Version: {VERSION_INEXISTENTE} (que ningún nodo real declara) responde 400 version_no_soportada con detalle.versiones"
        r = self._enviar(self._evento_base(secuencia=1), vereda_version=VERSION_INEXISTENTE)
        if not r.ok:
            self.casos.append(_fallo("version", opid, desc, r.motivo))
            return
        if r.estado == 401:
            self.casos.append(_omitido("version", opid, desc, "el nodo respondió 401 antes de llegar a mirar la versión (identidad de prueba no confiada); no es un fallo, pero no prueba esto"))
            return
        if r.estado != 400:
            self.casos.append(_fallo("version", opid, desc, f"esperaba 400, llegó {r.estado}"))
            return
        if not r.cuerpo_es_json or not isinstance(r.cuerpo, dict):
            self.casos.append(_fallo("version", opid, desc, "400 sin cuerpo JSON"))
            return
        if r.cuerpo.get("codigo") != "version_no_soportada":
            self.casos.append(_fallo("version", opid, desc, f"400 con codigo {r.cuerpo.get('codigo')!r}, no 'version_no_soportada'"))
            return
        if "versiones" not in r.cuerpo.get("detalle", {}):
            self.casos.append(_fallo("version", opid, desc, "400 version_no_soportada sin detalle.versiones"))
            return
        self.casos.append(_ok("version", opid, desc, {"versiones": r.cuerpo["detalle"]["versiones"]}))


def correr(origen, **kwargs) -> List[Caso]:
    return NivelC(origen, **kwargs).correr()
