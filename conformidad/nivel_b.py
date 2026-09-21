"""Nivel B: autenticado. Ver docs/suite-conformidad.md.

Nunca se autobootstrapea nada: sesión y mandato entran siempre por
parámetro, provistos por quien corre la suite contra su propio entorno de
prueba. Sin `--sesion` este nivel no corre. Sin `--mandato` corre igual
(ciclo de carrito con sesión), pero omite -- no falla -- todo lo que
necesita un mandato: el tope por período, la revocación, y la prueba que
más importa acá, que `POST /yo/claves/rotar` rechace un token de mandato.

Deuda conocida, a propósito: las ventanas de tiempo (carrito vence a las
24 h, `plazo_aceptacion_min`, la ventana de 7 días para reseñar) no se
prueban. Exigir un reloj de prueba es superficie nueva del protocolo.
"""
import os
import uuid
from typing import List, Optional

from jsonschema import Draft202012Validator

from . import cliente
from . import openapi_info as oi
from .nivel_a import Caso, _fallo, _ok, _omitido
from .oraculo import cargar as cargar_esquemas

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class NivelB:
    def __init__(self, origen, *, sesion, mandato=None, timeout=cliente.TIMEOUT_S):
        self.origen = origen.rstrip("/")
        self.base_v1 = self.origen + "/v1"
        self.sesion = sesion
        self.mandato = mandato
        self.timeout = timeout
        self.api = oi.cargar(BASE)
        self.esquemas, self.registry = cargar_esquemas(BASE)
        self.casos: List[Caso] = []

    # -- utilidades -----------------------------------------------------
    def _cabecera(self, mandato=False):
        token = self.mandato if mandato else self.sesion
        return {"Authorization": f"Bearer {token}"}

    def _op(self, ruta, metodo="post"):
        return self.api["paths"][ruta][metodo]

    def _validar(self, esquema_resuelto, doc):
        v = Draft202012Validator(esquema_resuelto, registry=self.registry)
        return sorted(v.iter_errors(doc), key=lambda e: list(e.path))

    def _formatear_errores(self, errores, limite=5):
        return "; ".join(f"{'/'.join(map(str, e.path)) or '(raíz)'}: {e.message[:140]}" for e in errores[:limite])

    def _chequear_esquema(self, opid, desc, ruta, metodo, cuerpo, estado="200") -> Optional[Caso]:
        op = self._op(ruta, metodo)
        esquema = oi.esquema_respuesta(self.api, op, estado)
        if esquema is None:
            return None
        errores = self._validar(esquema, cuerpo)
        if errores:
            return _fallo("esquema", opid, desc, self._formatear_errores(errores))
        return _ok("esquema", opid, desc)

    def _idem(self):
        return {"Idempotency-Key": str(uuid.uuid4())}

    # -- corrida ------------------------------------------------------------
    def correr(self) -> List[Caso]:
        self.casos = []
        pedido_id = self._ciclo_carrito_a_entregado()
        if pedido_id:
            self._resena(pedido_id)
        if self.mandato:
            self._mandato_tope()
            self._rotar_clave_no_por_mandato()
            self._revocacion_mandato()
        else:
            self.casos.append(_omitido("mandato", "confirmarCarrito", "tope del mandato por período (fuera_de_mandato)", "no se pasó --mandato"))
            self.casos.append(_omitido("mandato", "rotarClave", "rotarClave rechaza un token de mandato -- la prueba más importante de este nivel", "no se pasó --mandato"))
            self.casos.append(_omitido("mandato", "revocarMandato", "revocar un mandato lo invalida de inmediato", "no se pasó --mandato"))
        return self.casos

    # 1. el ciclo completo, con sesión, efectivo + retiro (sin PSP ni repartidor) --
    def _ciclo_carrito_a_entregado(self) -> Optional[str]:
        cat = "ciclo"

        r = cliente.solicitud("POST", f"{self.base_v1}/carritos", headers=self._cabecera(), json_body={}, timeout=self.timeout)
        if not r.ok or r.estado != 201:
            self.casos.append(_fallo(cat, "crearCarrito", "POST /carritos con sesión crea un carrito", r.motivo or f"esperaba 201, llegó {r.estado}"))
            return None
        caso = self._chequear_esquema("crearCarrito", "el carrito creado cumple esquemas/carrito.json", "/carritos", "post", r.cuerpo, "201")
        if caso:
            self.casos.append(caso)
        carrito_id = (r.cuerpo or {}).get("id")
        if not carrito_id:
            self.casos.append(_fallo(cat, "crearCarrito", "el carrito creado trae 'id'", "no vino 'id' en la respuesta"))
            return None
        self.casos.append(_ok(cat, "crearCarrito", "POST /carritos con sesión crea un carrito"))

        # oferta_id inventada: la respuesta correcta es 'no_disponible', no un error.
        r_bogus = cliente.solicitud(
            "POST", f"{self.base_v1}/carritos/{carrito_id}/items", headers=self._cabecera(),
            json_body={"oferta_id": "01920000-0000-7000-8000-0000000000ff", "cantidad": {"valor": 1, "unidad": "unidad"}}, timeout=self.timeout,
        )
        desc_bogus = "agregar una oferta_id inexistente responde 200 con estado 'no_disponible', no un error"
        if not r_bogus.ok:
            self.casos.append(_fallo(cat, "agregarItemCarrito", desc_bogus, r_bogus.motivo))
        elif r_bogus.estado == 200 and isinstance(r_bogus.cuerpo, dict) and r_bogus.cuerpo.get("estado") == "no_disponible":
            self.casos.append(_ok(cat, "agregarItemCarrito", desc_bogus))
        else:
            self.casos.append(_fallo(cat, "agregarItemCarrito", desc_bogus, f"estado {r_bogus.estado}, cuerpo.estado={ (r_bogus.cuerpo or {}).get('estado') if r_bogus.cuerpo_es_json else '(no JSON)'}"))

        r_item = cliente.solicitud(
            "POST", f"{self.base_v1}/carritos/{carrito_id}/items", headers=self._cabecera(),
            json_body={"oferta_id": "01920000-0000-7000-8000-0000000000b1", "cantidad": {"valor": 1, "unidad": "unidad"}}, timeout=self.timeout,
        )
        if not r_item.ok or r_item.estado != 200:
            self.casos.append(_fallo(cat, "agregarItemCarrito", "agregar un ítem real responde 200 con el carrito actualizado", r_item.motivo or f"estado {r_item.estado}"))
            return None
        caso = self._chequear_esquema("agregarItemCarrito", "el carrito con el ítem cumple esquemas/carrito.json", "/carritos/{id}/items", "post", r_item.cuerpo)
        if caso:
            self.casos.append(caso)
        self.casos.append(_ok(cat, "agregarItemCarrito", "agregar un ítem real responde 200 con el carrito actualizado"))

        r_mod = cliente.solicitud("PUT", f"{self.base_v1}/carritos/{carrito_id}/modalidad", headers=self._cabecera(), json_body={"tipo": "retiro"}, timeout=self.timeout)
        if not r_mod.ok or r_mod.estado != 200:
            self.casos.append(_fallo(cat, "elegirModalidadCarrito", "elegir modalidad 'retiro' responde 200", r_mod.motivo or f"estado {r_mod.estado}"))
            return None
        self.casos.append(_ok(cat, "elegirModalidadCarrito", "elegir modalidad 'retiro' responde 200"))

        r_conf = cliente.solicitud(
            "POST", f"{self.base_v1}/carritos/{carrito_id}/confirmar", headers={**self._cabecera(), **self._idem()}, json_body={}, timeout=self.timeout
        )
        if not r_conf.ok or r_conf.estado != 201:
            self.casos.append(_fallo(cat, "confirmarCarrito", "confirmar el carrito crea el pedido (201)", r_conf.motivo or f"estado {r_conf.estado}"))
            return None
        caso = self._chequear_esquema("confirmarCarrito", "el pedido creado cumple esquemas/pedido.json", "/carritos/{id}/confirmar", "post", r_conf.cuerpo, "201")
        if caso:
            self.casos.append(caso)
        pedido_id = (r_conf.cuerpo or {}).get("id")
        if not pedido_id:
            self.casos.append(_fallo(cat, "confirmarCarrito", "el pedido creado trae 'id'", "no vino 'id' en la respuesta"))
            return None
        self.casos.append(_ok(cat, "confirmarCarrito", "confirmar el carrito crea el pedido (201)"))

        item_id = ((r_conf.cuerpo or {}).get("items") or [{}])[0].get("id")

        r_acept = cliente.solicitud("POST", f"{self.base_v1}/pedidos/{pedido_id}/aceptar", headers=self._cabecera(), timeout=self.timeout)
        if not r_acept.ok or r_acept.estado != 200:
            self.casos.append(_fallo(cat, "aceptarPedido", "aceptar el pedido responde 200", r_acept.motivo or f"estado {r_acept.estado}"))
            return pedido_id
        self.casos.append(_ok(cat, "aceptarPedido", "aceptar el pedido responde 200"))

        desc_listo_temprano = "marcar 'listo' con ítems todavía sin resolver responde 409, no 200"
        r_listo_temprano = cliente.solicitud("POST", f"{self.base_v1}/pedidos/{pedido_id}/listo", headers=self._cabecera(), timeout=self.timeout)
        if not r_listo_temprano.ok:
            self.casos.append(_fallo(cat, "marcarPedidoListo", desc_listo_temprano, r_listo_temprano.motivo))
        elif r_listo_temprano.estado == 409:
            self.casos.append(_ok(cat, "marcarPedidoListo", desc_listo_temprano))
        else:
            self.casos.append(_fallo(cat, "marcarPedidoListo", desc_listo_temprano, f"esperaba 409, llegó {r_listo_temprano.estado}"))

        if item_id:
            r_res = cliente.solicitud("PATCH", f"{self.base_v1}/pedidos/{pedido_id}/items/{item_id}", headers=self._cabecera(), json_body={"estado": "confirmado"}, timeout=self.timeout)
            if not r_res.ok or r_res.estado != 200:
                self.casos.append(_fallo(cat, "resolverItemPedido", "confirmar el ítem responde 200", r_res.motivo or f"estado {r_res.estado}"))
            else:
                self.casos.append(_ok(cat, "resolverItemPedido", "confirmar el ítem responde 200"))
        else:
            self.casos.append(_omitido(cat, "resolverItemPedido", "confirmar el ítem", "el pedido no trajo items[0].id"))

        r_listo = cliente.solicitud("POST", f"{self.base_v1}/pedidos/{pedido_id}/listo", headers=self._cabecera(), timeout=self.timeout)
        if not r_listo.ok or r_listo.estado != 200:
            self.casos.append(_fallo(cat, "marcarPedidoListo", "marcar 'listo' con los ítems resueltos responde 200", r_listo.motivo or f"estado {r_listo.estado}"))
            return pedido_id
        self.casos.append(_ok(cat, "marcarPedidoListo", "marcar 'listo' con los ítems resueltos responde 200"))

        r_entrega_mal = cliente.solicitud(
            "POST", f"{self.base_v1}/pedidos/{pedido_id}/entregar", headers=self._cabecera(),
            json_body={"codigo_retiro": "000000", "cobrado_en_mano": True}, timeout=self.timeout,
        )
        desc_entrega_mal = "entregar con un código de retiro incorrecto responde 422 codigo_retiro_invalido"
        if not r_entrega_mal.ok:
            self.casos.append(_fallo(cat, "entregarPedido", desc_entrega_mal, r_entrega_mal.motivo))
        elif r_entrega_mal.estado == 422:
            self.casos.append(_ok(cat, "entregarPedido", desc_entrega_mal))
        else:
            self.casos.append(_fallo(cat, "entregarPedido", desc_entrega_mal, f"esperaba 422, llegó {r_entrega_mal.estado}"))

        r_ver = cliente.solicitud("GET", f"{self.base_v1}/pedidos/{pedido_id}", headers=self._cabecera(), timeout=self.timeout)
        codigo_real = (r_ver.cuerpo or {}).get("codigo_retiro") if r_ver.ok and r_ver.cuerpo_es_json else None
        if not codigo_real:
            self.casos.append(_fallo(cat, "verPedido", "GET /pedidos/{id} devuelve el código de retiro para poder entregar", r_ver.motivo or f"estado {r_ver.estado}"))
            return pedido_id
        self.casos.append(_ok(cat, "verPedido", "GET /pedidos/{id} devuelve el código de retiro para poder entregar"))

        r_entrega = cliente.solicitud(
            "POST", f"{self.base_v1}/pedidos/{pedido_id}/entregar", headers=self._cabecera(),
            json_body={"codigo_retiro": codigo_real, "cobrado_en_mano": True}, timeout=self.timeout,
        )
        if not r_entrega.ok or r_entrega.estado != 200:
            self.casos.append(_fallo(cat, "entregarPedido", "entregar con el código correcto responde 200", r_entrega.motivo or f"estado {r_entrega.estado}"))
            return pedido_id
        self.casos.append(_ok(cat, "entregarPedido", "entregar con el código correcto responde 200"))
        return pedido_id

    # 2. reseña: dentro de ventana se acepta una vez; la segunda, no --------
    def _resena(self, pedido_id):
        cat = "resena"
        cuerpo = {"pedido_id": pedido_id, "autor": "cliente-de-prueba@nodo-falso.test", "destinatario": "super-barrio-b@nodo-falso.test", "puntaje": 5, "texto": "Prueba de conformidad."}
        r1 = cliente.solicitud("POST", f"{self.base_v1}/resenas", headers=self._cabecera(), json_body=cuerpo, timeout=self.timeout)
        desc1 = "reseñar un pedido recién entregado responde 201"
        if not r1.ok or r1.estado != 201:
            self.casos.append(_fallo(cat, "crearResena", desc1, r1.motivo or f"estado {r1.estado}"))
            return
        self.casos.append(_ok(cat, "crearResena", desc1))

        r2 = cliente.solicitud("POST", f"{self.base_v1}/resenas", headers=self._cabecera(), json_body=cuerpo, timeout=self.timeout)
        desc2 = "reseñar el mismo pedido una segunda vez responde 409, no lo duplica"
        if not r2.ok:
            self.casos.append(_fallo(cat, "crearResena", desc2, r2.motivo))
        elif r2.estado == 409:
            self.casos.append(_ok(cat, "crearResena", desc2))
        else:
            self.casos.append(_fallo(cat, "crearResena", desc2, f"esperaba 409, llegó {r2.estado}"))

    # 3. tope del mandato por período -----------------------------------------
    def _mandato_tope(self):
        cat = "mandato"
        desc = "confirmar un carrito que supera el tope acumulado del mandato responde 402 fuera_de_mandato"

        def _carrito_confirmado_por_mandato(oferta_id):
            r = cliente.solicitud("POST", f"{self.base_v1}/carritos", headers=self._cabecera(mandato=True), json_body={}, timeout=self.timeout)
            if not r.ok or r.estado != 201:
                return None, r
            cid = (r.cuerpo or {}).get("id")
            cliente.solicitud("POST", f"{self.base_v1}/carritos/{cid}/items", headers=self._cabecera(mandato=True), json_body={"oferta_id": oferta_id, "cantidad": {"valor": 1, "unidad": "unidad"}}, timeout=self.timeout)
            cliente.solicitud("PUT", f"{self.base_v1}/carritos/{cid}/modalidad", headers=self._cabecera(mandato=True), json_body={"tipo": "retiro"}, timeout=self.timeout)
            r_conf = cliente.solicitud("POST", f"{self.base_v1}/carritos/{cid}/confirmar", headers={**self._cabecera(mandato=True), **self._idem()}, json_body={}, timeout=self.timeout)
            return cid, r_conf

        _cid1, r1 = _carrito_confirmado_por_mandato("01920000-0000-7000-8000-0000000000b1")  # barata: dentro del tope
        if not r1.ok or r1.estado != 201:
            self.casos.append(_fallo(cat, "confirmarCarrito", "un pedido dentro del tope del mandato se confirma (201)", r1.motivo if r1 else "sin respuesta"))
            self.casos.append(_omitido(cat, "confirmarCarrito", desc, "el primer pedido (dentro del tope) no se confirmó"))
            return
        self.casos.append(_ok(cat, "confirmarCarrito", "un pedido dentro del tope del mandato se confirma (201)"))

        _cid2, r2 = _carrito_confirmado_por_mandato("01920000-0000-7000-8000-0000000000b2")  # cara: suma más que el tope
        if not r2.ok:
            self.casos.append(_fallo(cat, "confirmarCarrito", desc, r2.motivo))
        elif r2.estado == 402:
            self.casos.append(_ok(cat, "confirmarCarrito", desc))
        else:
            self.casos.append(_fallo(cat, "confirmarCarrito", desc, f"esperaba 402 fuera_de_mandato, llegó {r2.estado}"))

    # 4. la garantía dura: rotar clave nunca por mandato ----------------------
    def _rotar_clave_no_por_mandato(self):
        cat = "mandato"
        opid = "rotarClave"

        r_sesion = cliente.solicitud("POST", f"{self.base_v1}/yo/claves/rotar", headers=self._cabecera(), json_body={}, timeout=self.timeout)
        desc_sesion = "rotarClave con sesión funciona (para saber que el 401 de abajo es un rechazo real, no la ruta rota)"
        if not r_sesion.ok or r_sesion.estado != 200:
            self.casos.append(_fallo(cat, opid, desc_sesion, r_sesion.motivo or f"estado {r_sesion.estado}"))
        else:
            self.casos.append(_ok(cat, opid, desc_sesion))

        r_mandato = cliente.solicitud("POST", f"{self.base_v1}/yo/claves/rotar", headers=self._cabecera(mandato=True), json_body={}, timeout=self.timeout)
        desc = "rotarClave con un token de mandato NO funciona -- openapi.yaml la declara security: [sesion], nunca mandato (docs/claves-y-firmas.md: 'Rotar nunca se puede hacer por mandato')"
        if not r_mandato.ok:
            self.casos.append(_fallo(cat, opid, desc, r_mandato.motivo))
        elif r_mandato.estado in (401, 403):
            self.casos.append(_ok(cat, opid, desc))
        else:
            self.casos.append(_fallo(cat, opid, desc, f"esperaba 401 o 403, llegó {r_mandato.estado} -- un agente pudo rotar la clave de la persona que le dio permisos"))

    # 5. revocación inmediata ------------------------------------------------
    def _revocacion_mandato(self):
        cat = "mandato"
        opid = "revocarMandato"
        r_rev = cliente.solicitud("POST", f"{self.base_v1}/mandatos/{self.mandato}/revocar", headers=self._cabecera(), timeout=self.timeout)
        desc_rev = "revocar el mandato (con sesión) responde 200"
        if not r_rev.ok or r_rev.estado != 200:
            self.casos.append(_fallo(cat, opid, desc_rev, r_rev.motivo or f"estado {r_rev.estado}"))
            self.casos.append(_omitido(cat, opid, "un mandato revocado deja de servir de inmediato", "no se pudo revocar"))
            return
        self.casos.append(_ok(cat, opid, desc_rev))

        r_uso = cliente.solicitud("POST", f"{self.base_v1}/carritos", headers=self._cabecera(mandato=True), json_body={}, timeout=self.timeout)
        desc_uso = "usar el mandato ya revocado responde 401, no crea nada"
        if not r_uso.ok:
            self.casos.append(_fallo(cat, opid, desc_uso, r_uso.motivo))
        elif r_uso.estado in (401, 403):
            self.casos.append(_ok(cat, opid, desc_uso))
        else:
            self.casos.append(_fallo(cat, opid, desc_uso, f"esperaba 401, llegó {r_uso.estado} -- el mandato revocado todavía funciona"))


def correr(origen, **kwargs) -> List[Caso]:
    return NivelB(origen, **kwargs).correr()
