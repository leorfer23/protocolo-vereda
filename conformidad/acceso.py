"""Nivel B, acceso (docs/acceso.md): solo contra un nodo que publica
`acceso.custodia_propia: true` en /.well-known/vereda.json.

Cada prueba genera sus claves en el momento, así que da de alta usuarios de
prueba en el nodo: es exactamente lo que el nodo promete, entrar sin que nadie
apruebe. Los casos negativos salen de openapi.yaml (cada campo requerido de cada
cuerpo de /acceso, quitado de a uno) y de ejemplos/casos/acceso-*.json.
"""
import base64
import glob
import json
import os
from datetime import datetime, timezone
from typing import List, Optional

import rfc8785
from cryptography.hazmat.primitives import serialization as sz
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from jsonschema import Draft202012Validator

from . import cliente
from . import openapi_info as oi
from .nivel_a import Caso, _fallo, _ok, _omitido

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


class Clave:
    def __init__(self):
        self.privada = Ed25519PrivateKey.generate()
        self.publica = _b64u(self.privada.public_key().public_bytes(sz.Encoding.Raw, sz.PublicFormat.Raw))

    def firmar(self, objeto) -> str:
        return _b64u(self.privada.sign(rfc8785.dumps(objeto)))


def capacidades(origen, timeout=cliente.TIMEOUT_S) -> dict:
    """El bloque 'acceso' de /.well-known/vereda.json, o {} si no está o no se pudo leer."""
    r = cliente.get(origen.rstrip("/") + "/.well-known/vereda.json", timeout=timeout)
    if not r.ok or r.estado != 200 or not r.cuerpo_es_json or not isinstance(r.cuerpo, dict):
        return {}
    acceso = r.cuerpo.get("acceso")
    return acceso if isinstance(acceso, dict) else {}


class Acceso:
    def __init__(self, origen, *, api, registry, timeout=cliente.TIMEOUT_S, alternativo=()):
        self.origen = origen.rstrip("/")
        self.api = api
        self.registry = registry
        self.timeout = timeout
        self.alternativo = list(alternativo)
        self.casos: List[Caso] = []
        self.token: Optional[str] = None
        self.clave: Optional[Clave] = None

    # -- utilidades -----------------------------------------------------
    def _post(self, ruta, cuerpo=None, token=None, metodo="POST"):
        cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
        return cliente.solicitud(metodo, self.origen + ruta, headers=cabeceras, json_body=cuerpo, timeout=self.timeout)

    def _yo(self, token):
        return cliente.get(self.origen + "/v1/yo", headers={"Authorization": f"Bearer {token}"}, timeout=self.timeout)

    def _esquema(self, opid, desc, ruta, metodo, cuerpo, estado):
        esquema = oi.esquema_respuesta(self.api, self.api["paths"][ruta][metodo], estado)
        if esquema is None:
            return
        errores = sorted(Draft202012Validator(esquema, registry=self.registry).iter_errors(cuerpo), key=lambda e: list(e.path))
        if errores:
            self.casos.append(_fallo("esquema", opid, desc, "; ".join(f"{'/'.join(map(str, e.path)) or '(raíz)'}: {e.message[:140]}" for e in errores[:5])))
        else:
            self.casos.append(_ok("esquema", opid, desc))

    def _espera(self, opid, desc, r, estados, codigo=None) -> bool:
        if not r.ok:
            self.casos.append(_fallo("acceso", opid, desc, r.motivo))
            return False
        if r.estado not in estados:
            self.casos.append(_fallo("acceso", opid, desc, f"esperaba {' o '.join(map(str, estados))}, llegó {r.estado}: {str(r.cuerpo)[:160]}"))
            return False
        if codigo:
            llego = r.cuerpo.get("codigo") if r.cuerpo_es_json and isinstance(r.cuerpo, dict) else None
            if llego != codigo:
                self.casos.append(_fallo("acceso", opid, desc, f"esperaba el código {codigo!r}, llegó {llego!r}"))
                return False
        self.casos.append(_ok("acceso", opid, desc))
        return True

    def _desafio(self, clave) -> Optional[dict]:
        r = self._post("/acceso/desafio", {"clave_publica": clave.publica})
        if r.ok and r.estado == 201 and r.cuerpo_es_json and isinstance(r.cuerpo, dict) and r.cuerpo.get("desafio"):
            return r.cuerpo
        return None

    def _canje(self, clave, desafio, nodo=None, **extra):
        prueba = {"clave_publica": clave.publica, "desafio": desafio["desafio"], "nodo": nodo or desafio["nodo"]}
        return self._post("/acceso/sesion", {"clave_publica": clave.publica, "desafio": desafio["desafio"], "firma": clave.firmar(prueba), **extra})

    def _entrar(self, clave) -> Optional[dict]:
        d = self._desafio(clave)
        if not d:
            return None
        r = self._canje(clave, d)
        return r.cuerpo if r.ok and r.estado == 201 and r.cuerpo_es_json else None

    # -- corrida --------------------------------------------------------
    def correr(self) -> List[Caso]:
        marta = Clave()
        sesion = self._flujo(marta)
        if sesion:
            self._desafio_de_otra_clave(marta)
            sesion = self._renovar_y_cerrar(marta, sesion)
            self._rotada_y_comprometida()
        else:
            self.casos.append(_omitido("acceso", "abrirSesion", "el resto del acceso", "no se pudo abrir la primera sesión"))
        self._negativos()
        self._alternativo()
        return self.casos

    def _flujo(self, clave) -> Optional[dict]:
        r = self._post("/acceso/desafio", {"clave_publica": clave.publica})
        if not self._espera("pedirDesafio", "POST /acceso/desafio con una clave nueva responde 201", r, (201,)):
            return None
        self._esquema("pedirDesafio", "el desafío cumple acceso.json#/$defs/desafio", "/acceso/desafio", "post", r.cuerpo, "201")
        d = r.cuerpo

        r_mala = self._canje(clave, d, nodo="otro-nodo.invalid")
        self._espera("abrirSesion", "una firma hecha para otro nodo responde 401 firma_invalida", r_mala, (401,), "firma_invalida")

        r = self._canje(clave, d, nombre="Conformidad")
        if not self._espera("abrirSesion", "la firma buena canjea el mismo desafío (la mala no lo gastó): 201", r, (201,)):
            return None
        self._esquema("abrirSesion", "la sesión cumple acceso.json#/$defs/sesion", "/acceso/sesion", "post", r.cuerpo, "201")
        sesion = r.cuerpo
        if sesion.get("nuevo") is not True:
            self.casos.append(_fallo("acceso", "abrirSesion", "la primera entrada de una clave nueva trae nuevo: true", f"llegó nuevo={sesion.get('nuevo')!r}"))
        else:
            self.casos.append(_ok("acceso", "abrirSesion", "la primera entrada de una clave nueva trae nuevo: true"))

        r_otra = self._canje(clave, d)
        self._espera("abrirSesion", "el mismo desafío no se canjea dos veces: 401", r_otra, (401,))

        r_yo = self._yo(sesion["token"])
        if self._espera("verPerfil", "el token abre GET /v1/yo", r_yo, (200,)) and isinstance(r_yo.cuerpo, dict) and r_yo.cuerpo.get("identidad") != sesion.get("identidad"):
            self.casos.append(_fallo("acceso", "verPerfil", "GET /v1/yo devuelve la identidad de la sesión", f"{r_yo.cuerpo.get('identidad')!r} != {sesion.get('identidad')!r}"))

        otra = self._entrar(clave)
        desc = "volver a entrar con la misma clave da la misma identidad y nuevo: false"
        if not otra:
            self.casos.append(_fallo("acceso", "abrirSesion", desc, "no se pudo volver a entrar"))
        elif otra.get("identidad") != sesion.get("identidad") or otra.get("nuevo") is not False:
            self.casos.append(_fallo("acceso", "abrirSesion", desc, f"identidad {otra.get('identidad')!r}, nuevo {otra.get('nuevo')!r}"))
        else:
            self.casos.append(_ok("acceso", "abrirSesion", desc))
            self.token = otra["token"]
            self.clave = clave
        return sesion

    def _desafio_de_otra_clave(self, marta):
        otra = Clave()
        d = self._desafio(otra)
        if not d:
            self.casos.append(_omitido("acceso", "abrirSesion", "un desafío emitido para otra clave no se canjea", "no se pudo pedir el desafío"))
            return
        self._espera("abrirSesion", "un desafío emitido para otra clave no se canjea: 401", self._canje(marta, d), (401,))

    def _renovar_y_cerrar(self, clave, sesion):
        r = self._post("/acceso/renovar", token=sesion["token"])
        if self._espera("renovarSesion", "POST /acceso/renovar con la sesión responde 200", r, (200,)):
            self._esquema("renovarSesion", "la renovación cumple acceso.json#/$defs/renovacion", "/acceso/renovar", "post", r.cuerpo, "200")
            self._espera("renovarSesion", "el token viejo deja de valer en el acto: 401", self._yo(sesion["token"]), (401,))
            sesion = {**sesion, "token": r.cuerpo["token"]}
            self._espera("renovarSesion", "el token nuevo abre GET /v1/yo", self._yo(sesion["token"]), (200,))
        r = self._post("/acceso/sesion", token=sesion["token"], metodo="DELETE")
        if self._espera("cerrarSesion", "DELETE /acceso/sesion responde 204", r, (204,)):
            self._espera("cerrarSesion", "el token cerrado ya no abre GET /v1/yo: 401", self._yo(sesion["token"]), (401,))
        return sesion

    def _rotada_y_comprometida(self):
        vieja, nueva, tercera = Clave(), Clave(), Clave()
        sesion = self._entrar(vieja)
        if not sesion:
            self.casos.append(_omitido("acceso", "rotarClave", "una clave retirada no abre sesión (clave_rotada)", "no se pudo entrar con la clave a rotar"))
            return
        ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        entrada = {"clave_publica": nueva.publica, "desde": ahora, "estado": "activa"}
        entrada["avalada_por"] = {"clave_publica": vieja.publica, "valor": vieja.firmar(entrada)}
        r = cliente.solicitud("POST", self.origen + "/v1/yo/claves/rotar", headers={"Authorization": f"Bearer {sesion['token']}"}, json_body={"clave": entrada}, timeout=self.timeout)
        if not self._espera("rotarClave", "con custodia propia, rotar con la entrada nueva avalada por la vieja responde 200", r, (200,)):
            self.casos.append(_omitido("acceso", "abrirSesion", "una clave retirada no abre sesión (clave_rotada)", "no se pudo rotar"))
            return
        d = self._desafio(vieja)
        if d:
            self._espera("abrirSesion", "la clave retirada no abre sesión: 401 clave_rotada", self._canje(vieja, d), (401,), "clave_rotada")
        con_nueva = self._entrar(nueva)
        desc = "la clave nueva entra a la misma identidad"
        if con_nueva and con_nueva.get("identidad") == sesion.get("identidad"):
            self.casos.append(_ok("acceso", "abrirSesion", desc))
        else:
            self.casos.append(_fallo("acceso", "abrirSesion", desc, f"llegó {con_nueva and con_nueva.get('identidad')!r}"))
            return

        cuerpo = {"clave_publica": nueva.publica, "comprometida_desde": ahora, "clave": {"clave_publica": tercera.publica, "desde": ahora, "estado": "activa"}}
        r = cliente.solicitud("POST", self.origen + "/v1/yo/claves/comprometida", headers={"Authorization": f"Bearer {con_nueva['token']}"}, json_body=cuerpo, timeout=self.timeout)
        if not self._espera("declararClaveComprometida", "declarar comprometida la clave activa, con la entrada que la reemplaza, responde 200", r, (200,)):
            return
        d = self._desafio(nueva)
        if d:
            self._espera("abrirSesion", "la clave comprometida no abre sesión: 401 clave_comprometida", self._canje(nueva, d), (401,), "clave_comprometida")
        con_tercera = self._entrar(tercera)
        desc = "la clave que reemplazó a la comprometida entra a la misma identidad"
        if con_tercera and con_tercera.get("identidad") == sesion.get("identidad"):
            self.casos.append(_ok("acceso", "abrirSesion", desc))
        else:
            self.casos.append(_fallo("acceso", "abrirSesion", desc, f"llegó {con_tercera and con_tercera.get('identidad')!r}"))

    def _negativos(self):
        """Cada campo requerido de cada cuerpo de /acceso, quitado de a uno, se
        rechaza con 422 -- sale de openapi.yaml, no de una lista a mano."""
        base = {"clave_publica": Clave().publica, "desafio": "no-existe-este-desafio", "firma": "A" * 86, "canal": "email", "valor": "nadie@ejemplo.invalid", "codigo": "000000"}
        for ruta, metodo, op in oi.operaciones(self.api):
            if not ruta.startswith("/acceso/") or "requestBody" not in op:
                continue
            if op["operationId"] in ("pedirCodigoDeAcceso", "canjearCodigoDeAcceso") and not self.alternativo:
                continue
            esquema = oi.resolver_esquema(self.api, op["requestBody"]["content"]["application/json"]["schema"])
            ref = esquema.get("$ref", "")
            defn = ref.rsplit("/", 1)[-1]
            requeridos = json.load(open(os.path.join(BASE, "esquemas", "acceso.json")))["$defs"].get(defn, {}).get("required", [])
            for campo in requeridos:
                cuerpo = {k: base[k] for k in requeridos if k != campo}
                r = self._post(ruta, cuerpo, metodo=metodo.upper())
                self._espera(op["operationId"], f"{metodo.upper()} {ruta} sin '{campo}' responde 422", r, (422,))

        for archivo in sorted(glob.glob(os.path.join(BASE, "ejemplos", "casos", "acceso-sesion.json"))):
            for caso in json.load(open(archivo))["casos"]:
                if caso["espera"] != "invalido":
                    continue
                r = self._post("/acceso/sesion", caso["doc"])
                desc = f"POST /acceso/sesion rechaza: {caso['porque'][:80]}"
                if not r.ok:
                    self.casos.append(_fallo("negativos", "abrirSesion", desc, r.motivo))
                elif r.estado in (401, 422) and r.cuerpo_es_json:
                    self.casos.append(_ok("negativos", "abrirSesion", desc))
                else:
                    self.casos.append(_fallo("negativos", "abrirSesion", desc, f"esperaba 401 o 422 con error.json, llegó {r.estado}"))

    def _alternativo(self):
        if not self.alternativo:
            r = self._post("/acceso/codigo", {"canal": "email", "valor": "nadie@ejemplo.invalid"})
            self._espera("pedirCodigoDeAcceso", "sin acceso alternativo declarado, POST /acceso/codigo responde 501", r, (501,), "no_implementado")
            return
        canal = self.alternativo[0]
        valor = "nadie@ejemplo.invalid" if canal == "email" else "+5491100000000"
        self._espera("pedirCodigoDeAcceso", f"POST /acceso/codigo por {canal} responde 202", self._post("/acceso/codigo", {"canal": canal, "valor": valor}), (202,))
        self._espera("canjearCodigoDeAcceso", "un código incorrecto no abre sesión: 401", self._post("/acceso/codigo/canje", {"canal": canal, "valor": valor, "codigo": "000000"}), (401,))
