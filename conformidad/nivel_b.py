"""Nivel B: autenticado. Ver docs/suite-conformidad.md.

Contra un nodo que publica `acceso.custodia_propia: true`, primero prueba el
acceso (conformidad/acceso.py) y, si no se pasó `--sesion`, sigue con la sesión
que abrió ahí. Contra cualquier otro, sesión y mandato entran siempre por
parámetro y sin `--sesion` este nivel no corre. Sin `--mandato` corre igual
(ciclo de carrito con sesión), pero omite -- no falla -- todo lo que
necesita un mandato: el tope por período, la revocación, y la prueba que
más importa acá, que `POST /yo/claves/rotar` rechace un token de mandato.

Deuda conocida, a propósito: las ventanas de tiempo (carrito vence a las
24 h, `plazo_aceptacion_min`, la ventana de 7 días para reseñar) no se
prueban. Exigir un reloj de prueba es superficie nueva del protocolo.
"""
import json
import os
import queue
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import requests

from jsonschema import Draft202012Validator

from . import acceso, cliente
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
        capacidades = acceso.capacidades(self.origen, self.timeout)
        if capacidades.get("custodia_propia") is True:
            prueba = acceso.Acceso(self.origen, api=self.api, registry=self.registry, timeout=self.timeout, alternativo=capacidades.get("alternativo") or [])
            self.casos.extend(prueba.correr())
            self.sesion = self.sesion or prueba.token
        else:
            self.casos.append(_omitido("acceso", "abrirSesion", "acceso por clave propia (docs/acceso.md)", "el nodo no publica acceso.custodia_propia: true en /.well-known/vereda.json"))
        if not self.sesion:
            self.casos.append(_omitido("ciclo", "crearCarrito", "el resto del nivel B", "no se pasó --sesion y no se pudo abrir una por /acceso"))
            return self.casos
        pedido_id = self._ciclo_carrito_a_entregado()
        if pedido_id:
            self._resena(pedido_id)
        self._direcciones()
        self._mis_comercios()
        self._viaje_ajeno()
        self._metodo_pago()
        self._ubicacion_en_camino()
        self._eventos_de_quien_administra(capacidades)
        self._apertura_manual()
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

        desc_mal = "aceptar con tiempo_preparacion_min fuera de rango responde 422 y no acepta"
        r_mal = cliente.solicitud("POST", f"{self.base_v1}/pedidos/{pedido_id}/aceptar", headers=self._cabecera(), json_body={"tiempo_preparacion_min": -5}, timeout=self.timeout)
        if not r_mal.ok:
            self.casos.append(_fallo(cat, "aceptarPedido", desc_mal, r_mal.motivo))
        elif r_mal.estado != 422:
            self.casos.append(_fallo(cat, "aceptarPedido", desc_mal, f"esperaba 422, llegó {r_mal.estado}"))
        else:
            self.casos.append(_ok(cat, "aceptarPedido", desc_mal))

        minutos = 25
        antes = datetime.now(timezone.utc)
        r_acept = cliente.solicitud("POST", f"{self.base_v1}/pedidos/{pedido_id}/aceptar", headers=self._cabecera(), json_body={"tiempo_preparacion_min": minutos}, timeout=self.timeout)
        if not r_acept.ok or r_acept.estado != 200:
            self.casos.append(_fallo(cat, "aceptarPedido", "aceptar el pedido responde 200", r_acept.motivo or f"estado {r_acept.estado}"))
            return pedido_id
        self.casos.append(_ok(cat, "aceptarPedido", "aceptar el pedido responde 200"))
        caso = self._chequear_esquema("aceptarPedido", "el pedido aceptado cumple esquemas/pedido.json", "/pedidos/{id}/aceptar", "post", r_acept.cuerpo)
        if caso:
            self.casos.append(caso)
        self._eta_del_aceptado(r_acept.cuerpo, minutos, antes)

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

    # aceptar con tiempo: los minutos que dio el comercio mueven la eta ------
    def _eta_del_aceptado(self, pedido, minutos, antes):
        cat, opid = "ciclo", "aceptarPedido"
        desc = f"aceptar con tiempo_preparacion_min {minutos} lo guarda en el pedido y fija eta a esos minutos de la aceptación (retiro, sin ruta)"
        if not isinstance(pedido, dict):
            self.casos.append(_fallo(cat, opid, desc, "la respuesta no es un pedido"))
            return
        if pedido.get("tiempo_preparacion_min") != minutos:
            self.casos.append(_fallo(cat, opid, desc, f"tiempo_preparacion_min vino {pedido.get('tiempo_preparacion_min')!r}"))
            return
        try:
            eta = datetime.fromisoformat(str(pedido.get("eta")).replace("Z", "+00:00"))
        except ValueError:
            self.casos.append(_fallo(cat, opid, desc, f"eta no es un instante: {pedido.get('eta')!r}"))
            return
        esperado = antes + timedelta(minutes=minutos)
        if abs((eta - esperado).total_seconds()) > 120:
            self.casos.append(_fallo(cat, opid, desc, f"eta {pedido.get('eta')} y se esperaba cerca de {esperado.isoformat()}"))
            return
        self.casos.append(_ok(cat, opid, desc))

    # quien administra el comercio recibe sus eventos por SSE (docs/eventos.md) --
    # Hace falta una compradora que no sea la sesión de prueba: sale de /acceso,
    # así que solo contra un nodo con custodia propia.
    def _eventos_de_quien_administra(self, capacidades, espera_s=15.0):
        cat, opid = "eventos", "escucharEventos"
        desc = "quien administra el comercio recibe por GET /eventos el pedido.creado de una compra ajena en su comercio"
        if capacidades.get("custodia_propia") is not True:
            self.casos.append(_omitido(cat, opid, desc, "hace falta una segunda identidad y el nodo no publica acceso.custodia_propia: true"))
            return
        prueba = acceso.Acceso(self.origen, api=self.api, registry=self.registry, timeout=self.timeout)
        compradora = prueba._entrar(acceso.Clave())
        token = (compradora or {}).get("token")
        if not token:
            self.casos.append(_omitido(cat, opid, desc, "no se pudo abrir la sesión de una compradora nueva por /acceso"))
            return

        vistos: "queue.Queue[dict]" = queue.Queue()
        corte = threading.Event()
        abierto = threading.Event()
        falla = []

        def escuchar():
            try:
                with requests.get(f"{self.base_v1}/eventos", headers={**self._cabecera(), "Accept": "text/event-stream"}, stream=True, timeout=(self.timeout, espera_s + 5)) as r:
                    if r.status_code != 200:
                        falla.append(f"el stream respondió {r.status_code}")
                        return
                    abierto.set()
                    tipo, datos = "", ""
                    for linea in r.iter_lines(decode_unicode=True):
                        if corte.is_set():
                            return
                        if linea is None:
                            continue
                        if linea == "":
                            if datos:
                                try:
                                    vistos.put({"tipo": tipo, "evento": json.loads(datos)})
                                except ValueError:
                                    pass
                            tipo, datos = "", ""
                        elif linea.startswith("event:"):
                            tipo = linea[6:].strip()
                        elif linea.startswith("data:"):
                            datos += linea[5:].strip()
            except requests.exceptions.RequestException as e:
                if not corte.is_set():
                    falla.append(f"el stream se cortó ({str(e)[:120]})")
            finally:
                abierto.set()

        hilo = threading.Thread(target=escuchar, daemon=True)
        hilo.start()
        abierto.wait(self.timeout)
        if falla:
            self.casos.append(_fallo(cat, opid, desc, falla[0]))
            return

        sesion_prueba = self.sesion
        self.sesion = token
        try:
            cid = self._carrito_con("01920000-0000-7000-8000-0000000000b1", {"tipo": "retiro"})
            r = self._confirmar(cid, {}) if cid else None
        finally:
            self.sesion = sesion_prueba
        pedido_id = (r.cuerpo or {}).get("id") if r and r.ok and r.estado == 201 and isinstance(r.cuerpo, dict) else None
        if not pedido_id:
            corte.set()
            self.casos.append(_omitido(cat, opid, desc, "la compradora nueva no pudo confirmar un pedido de la oferta de prueba"))
            return

        limite = time.monotonic() + espera_s
        visto = False
        while time.monotonic() < limite and not visto:
            try:
                e = vistos.get(timeout=max(0.1, limite - time.monotonic()))
            except queue.Empty:
                break
            entidad = (e["evento"] or {}).get("entidad") or {}
            visto = e["tipo"] == "pedido.creado" and entidad.get("id") == pedido_id
        corte.set()
        cliente.solicitud("POST", f"{self.base_v1}/pedidos/{pedido_id}/cancelar", headers={"Authorization": f"Bearer {token}"}, json_body={"motivo": "prueba de conformidad"}, timeout=self.timeout)
        if visto:
            self.casos.append(_ok(cat, opid, desc))
        else:
            self.casos.append(_fallo(cat, opid, desc, falla[0] if falla else f"en {espera_s:.0f} s no llegó pedido.creado del pedido {pedido_id}"))

    # "abierto ahora": apertura_manual pisa los horarios y se ve en la ficha y en la búsqueda --
    # Va al final: deja el comercio de prueba como estaba (sin apertura_manual).
    def _apertura_manual(self):
        cat, opid = "apertura", "editarComercio"
        comercio = self._comercio_de_la_oferta("01920000-0000-7000-8000-0000000000b1")
        if not comercio or not comercio.get("id"):
            self.casos.append(_omitido(cat, opid, "apertura_manual cierra y abre el comercio", "no se pudo leer el comercio de la oferta de prueba"))
            return
        cid = comercio["id"]
        punto = ((comercio.get("ubicacion") or {}).get("direccion") or {}).get("punto") or {}

        def editar(apertura):
            return cliente.solicitud("PATCH", f"{self.base_v1}/comercios/{cid}", headers=self._cabecera(), json_body={"apertura_manual": apertura}, timeout=self.timeout)

        def en_busqueda(abierto):
            if "lat" not in punto or "lng" not in punto:
                return None
            r = cliente.get(f"{self.base_v1}/comercios?lat={punto['lat']}&lng={punto['lng']}&abierto={'true' if abierto else 'false'}", timeout=self.timeout)
            if not r.ok or r.estado != 200 or not isinstance(r.cuerpo, list):
                return None
            return any(isinstance(c, dict) and c.get("id") == cid for c in r.cuerpo)

        desc = "la ficha trae abierto_ahora, booleano calculado por el nodo"
        if isinstance(comercio.get("abierto_ahora"), bool):
            self.casos.append(_ok(cat, "verComercio", desc))
        else:
            self.casos.append(_fallo(cat, "verComercio", desc, f"abierto_ahora vino {comercio.get('abierto_ahora')!r}"))

        hasta = (datetime.now(timezone.utc) + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
        for abierto in (False, True):
            estado = "cerrado" if not abierto else "abierto"
            desc = f"apertura_manual {{abierto: {str(abierto).lower()}}} deja el comercio {estado} en la ficha y en buscarComercios?abierto"
            r = editar({"abierto": abierto, "hasta": hasta})
            if not r.ok or r.estado != 200 or not isinstance(r.cuerpo, dict):
                self.casos.append(_fallo(cat, opid, desc, r.motivo or f"el PATCH respondió {r.estado}"))
                continue
            caso = self._chequear_esquema(opid, "la ficha editada cumple esquemas/comercio.json", "/comercios/{id}", "patch", r.cuerpo)
            if caso:
                self.casos.append(caso)
            ficha = cliente.get(f"{self.base_v1}/comercios/{cid}", headers={"Cache-Control": "no-cache"}, timeout=self.timeout)
            visto = (ficha.cuerpo or {}).get("abierto_ahora") if ficha.ok and isinstance(ficha.cuerpo, dict) else None
            if r.cuerpo.get("abierto_ahora") is not abierto or visto is not abierto:
                self.casos.append(_fallo(cat, opid, desc, f"abierto_ahora: PATCH {r.cuerpo.get('abierto_ahora')!r}, GET {visto!r}"))
                continue
            si, no = en_busqueda(abierto), en_busqueda(not abierto)
            if si is None or no is None:
                self.casos.append(_fallo(cat, "buscarComercios", desc, "no se pudo buscar comercios en el punto del comercio de prueba"))
            elif not si or no:
                self.casos.append(_fallo(cat, "buscarComercios", desc, f"con abierto={str(abierto).lower()} aparece: {si}; con abierto={str(not abierto).lower()} aparece: {no}"))
            else:
                self.casos.append(_ok(cat, opid, desc))

        desc = "apertura_manual con campos de más responde 422"
        r = editar({"abierto": False, "motivo": "vacaciones"})
        if not r.ok:
            self.casos.append(_fallo(cat, opid, desc, r.motivo))
        elif r.estado != 422:
            self.casos.append(_fallo(cat, opid, desc, f"esperaba 422, llegó {r.estado}"))
        else:
            self.casos.append(_ok(cat, opid, desc))

        desc = "apertura_manual: null la quita y vuelven a mandar los horarios"
        r = editar(None)
        if not r.ok or r.estado != 200 or not isinstance(r.cuerpo, dict):
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"el PATCH respondió {r.estado}"))
        elif "apertura_manual" in r.cuerpo:
            self.casos.append(_fallo(cat, opid, desc, f"la ficha sigue trayendo apertura_manual {r.cuerpo['apertura_manual']!r}"))
        elif r.cuerpo.get("abierto_ahora") != comercio.get("abierto_ahora"):
            self.casos.append(_fallo(cat, opid, desc, f"abierto_ahora quedó {r.cuerpo.get('abierto_ahora')!r} y antes de tocarlo era {comercio.get('abierto_ahora')!r}"))
        else:
            self.casos.append(_ok(cat, opid, desc))

    # direcciones guardadas: reemplaza la lista entera, valida, y nunca por mandato --
    def _direcciones(self):
        cat, opid = "direcciones", "guardarDirecciones"
        url = f"{self.base_v1}/yo/direcciones"
        r_yo = cliente.solicitud("GET", f"{self.base_v1}/yo", headers=self._cabecera(), timeout=self.timeout)
        if not r_yo.ok or r_yo.estado != 200 or not isinstance(r_yo.cuerpo, dict):
            self.casos.append(_omitido(cat, opid, "PUT /yo/direcciones", "no se pudo leer GET /yo para guardar y después restaurar las direcciones de la sesión de prueba"))
            return
        originales = r_yo.cuerpo.get("direcciones") or []

        nuevas = [
            {"texto": "Av. Rivadavia 4520 3° B, entre Yatay y Lambaré", "punto": {"lat": -34.6158, "lng": -58.4333}, "etiqueta": "casa"},
            {"texto": "Florida 520, CABA", "punto": {"lat": -34.6011, "lng": -58.3752}, "etiqueta": "trabajo"},
        ]
        desc = "PUT /yo/direcciones con sesión reemplaza la lista y la devuelve"
        r = cliente.solicitud("PUT", url, headers=self._cabecera(), json_body=nuevas, timeout=self.timeout)
        if not r.ok or r.estado != 200:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 200, llegó {r.estado}"))
            return
        caso = self._chequear_esquema(opid, "la respuesta cumple usuario.json#/$defs/direcciones", "/yo/direcciones", "put", r.cuerpo)
        if caso:
            self.casos.append(caso)
        etiquetas = [d.get("etiqueta") for d in r.cuerpo] if isinstance(r.cuerpo, list) else None
        if etiquetas == ["casa", "trabajo"]:
            self.casos.append(_ok(cat, opid, desc))
        else:
            self.casos.append(_fallo(cat, opid, desc, f"esperaba las etiquetas ['casa', 'trabajo'] en ese orden, llegó {etiquetas}"))

        desc = "GET /yo muestra las direcciones recién guardadas"
        r_ver = cliente.solicitud("GET", f"{self.base_v1}/yo", headers=self._cabecera(), timeout=self.timeout)
        leidas = [d.get("etiqueta") for d in ((r_ver.cuerpo or {}).get("direcciones") or [])] if r_ver.ok and isinstance(r_ver.cuerpo, dict) else None
        if leidas == ["casa", "trabajo"]:
            self.casos.append(_ok(cat, "verPerfil", desc))
        else:
            self.casos.append(_fallo(cat, "verPerfil", desc, f"GET /yo trae las etiquetas {leidas}"))

        rechazos = [
            ("dos direcciones con la misma etiqueta responde 422", [nuevas[0], {**nuevas[1], "etiqueta": "casa"}]),
            ("una dirección sin punto responde 422", [{"texto": "Pellegrini 800, Rosario", "etiqueta": "casa"}]),
            ("un objeto en vez de la lista responde 422", nuevas[0]),
        ]
        for desc, cuerpo in rechazos:
            r = cliente.solicitud("PUT", url, headers=self._cabecera(), json_body=cuerpo, timeout=self.timeout)
            if not r.ok:
                self.casos.append(_fallo(cat, opid, desc, r.motivo))
            elif r.estado != 422:
                self.casos.append(_fallo(cat, opid, desc, f"esperaba 422, llegó {r.estado}"))
            else:
                caso = self._chequear_esquema(opid, desc + " con esquemas/error.json", "/yo/direcciones", "put", r.cuerpo, "422")
                self.casos.append(caso or _ok(cat, opid, desc))

        if self.mandato:
            desc = "PUT /yo/direcciones con un token de mandato se rechaza: solo la persona las escribe"
            r = cliente.solicitud("PUT", url, headers=self._cabecera(mandato=True), json_body=[], timeout=self.timeout)
            if not r.ok:
                self.casos.append(_fallo(cat, opid, desc, r.motivo))
            elif r.estado in (401, 403):
                self.casos.append(_ok(cat, opid, desc))
            else:
                self.casos.append(_fallo(cat, opid, desc, f"esperaba 403, llegó {r.estado}"))
        else:
            self.casos.append(_omitido(cat, opid, "PUT /yo/direcciones rechaza un token de mandato", "no se pasó --mandato"))

        r = cliente.solicitud("PUT", url, headers=self._cabecera(), json_body=originales, timeout=self.timeout)
        desc = "restaurar las direcciones que la sesión de prueba tenía antes"
        if not r.ok or r.estado != 200:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 200, llegó {r.estado}"))

    # los comercios que administra la sesión de prueba ------------------------
    def _mis_comercios(self):
        opid, cat = "listarMisComercios", "mi-comercio"
        desc = "GET /yo/comercios con sesión responde 200 con la lista de comercios que administra"
        r = cliente.solicitud("GET", f"{self.base_v1}/yo/comercios", headers=self._cabecera(), timeout=self.timeout)
        if not r.ok or r.estado != 200:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 200, llegó {r.estado}"))
            return
        caso = self._chequear_esquema(opid, "la respuesta cumple MiComercio[]", "/yo/comercios", "get", r.cuerpo)
        if caso:
            self.casos.append(caso)
        self.casos.append(_ok(cat, opid, desc))

        # la sesión de prueba acepta el pedido del ciclo: es la dueña del comercio de la oferta b1
        desc = "GET /yo/comercios incluye el comercio de prueba, que la sesión administra"
        r_of = cliente.solicitud("GET", f"{self.base_v1}/ofertas/01920000-0000-7000-8000-0000000000b1", timeout=self.timeout)
        comercio_id = (r_of.cuerpo or {}).get("comercio_id") if r_of.ok and r_of.estado == 200 and isinstance(r_of.cuerpo, dict) else None
        if not comercio_id:
            self.casos.append(_omitido(cat, opid, desc, "no se pudo leer el comercio de la oferta de prueba"))
            return
        ids = [c.get("id") for c in r.cuerpo if isinstance(c, dict)] if isinstance(r.cuerpo, list) else []
        if comercio_id in ids:
            self.casos.append(_ok(cat, opid, desc))
        else:
            self.casos.append(_fallo(cat, opid, desc, f"{comercio_id} no está en {ids}"))

    # un viaje que no es de uno no se lee, ni se sabe si existe -------------
    def _viaje_ajeno(self):
        opid = "verViaje"
        desc = "GET /viajes/{id} de un viaje que no existe (o no es de uno) responde 404 con esquemas/error.json"
        r = cliente.solicitud("GET", f"{self.base_v1}/viajes/01920000-0000-7000-8000-00000000dead", headers=self._cabecera(), timeout=self.timeout)
        if not r.ok:
            self.casos.append(_fallo("viajes", opid, desc, r.motivo))
        elif r.estado != 404:
            self.casos.append(_fallo("viajes", opid, desc, f"esperaba 404, llegó {r.estado}"))
        else:
            caso = self._chequear_esquema(opid, desc, "/viajes/{id}", "get", r.cuerpo, "404")
            self.casos.append(caso or _ok("viajes", opid, desc))

    # el comprador elige cómo paga, entre los medios que acepta el comercio --
    def _comercio_de_la_oferta(self, oferta_id):
        r = cliente.solicitud("GET", f"{self.base_v1}/ofertas/{oferta_id}", timeout=self.timeout)
        comercio_id = (r.cuerpo or {}).get("comercio_id") if r.ok and r.estado == 200 and isinstance(r.cuerpo, dict) else None
        if not comercio_id:
            return None
        r = cliente.solicitud("GET", f"{self.base_v1}/comercios/{comercio_id}", timeout=self.timeout)
        return r.cuerpo if r.ok and r.estado == 200 and isinstance(r.cuerpo, dict) else None

    def _carrito_con(self, oferta_id, modalidad):
        r = cliente.solicitud("POST", f"{self.base_v1}/carritos", headers=self._cabecera(), json_body={}, timeout=self.timeout)
        cid = (r.cuerpo or {}).get("id") if r.ok and r.estado == 201 and isinstance(r.cuerpo, dict) else None
        if not cid:
            return None
        r = cliente.solicitud("POST", f"{self.base_v1}/carritos/{cid}/items", headers=self._cabecera(),
                              json_body={"oferta_id": oferta_id, "cantidad": {"valor": 1, "unidad": "unidad"}}, timeout=self.timeout)
        if not r.ok or r.estado != 200:
            return None
        r = cliente.solicitud("PUT", f"{self.base_v1}/carritos/{cid}/modalidad", headers=self._cabecera(), json_body=modalidad, timeout=self.timeout)
        if not r.ok or r.estado != 200:
            return None
        return cid

    def _confirmar(self, cid, cuerpo):
        return cliente.solicitud("POST", f"{self.base_v1}/carritos/{cid}/confirmar", headers={**self._cabecera(), **self._idem()}, json_body=cuerpo, timeout=self.timeout)

    def _metodo_pago(self):
        cat, opid = "metodo_pago", "confirmarCarrito"
        oferta = "01920000-0000-7000-8000-0000000000b1"
        comercio = self._comercio_de_la_oferta(oferta)
        if not comercio:
            self.casos.append(_omitido(cat, opid, "elegir cómo pagar al confirmar (metodo_pago)", "no se pudo leer el comercio de la oferta de prueba con GET /ofertas/{id} y GET /comercios/{id}"))
            return
        medios = comercio.get("medios_cobro") or []
        cid = self._carrito_con(oferta, {"tipo": "retiro"})
        if not cid:
            self.casos.append(_omitido(cat, opid, "elegir cómo pagar al confirmar (metodo_pago)", "no se pudo armar un carrito con retiro"))
            return

        desc = "un metodo_pago fuera de efectivo/transferencia responde 422 y no crea el pedido"
        r = self._confirmar(cid, {"metodo_pago": "cheque"})
        if not r.ok:
            self.casos.append(_fallo(cat, opid, desc, r.motivo))
        elif r.estado != 422:
            self.casos.append(_fallo(cat, opid, desc, f"esperaba 422, llegó {r.estado}"))
        else:
            caso = self._chequear_esquema(opid, desc + " con esquemas/error.json", "/carritos/{id}/confirmar", "post", r.cuerpo, "422")
            self.casos.append(caso or _ok(cat, opid, desc))

        no_acepta = [m for m in ("transferencia", "efectivo") if m not in medios]
        desc = "un metodo_pago que el comercio no acepta responde 422 con detalle.medios_cobro, los que sí acepta"
        if not no_acepta:
            self.casos.append(_omitido(cat, opid, desc, f"el comercio de prueba acepta efectivo y transferencia ({medios})"))
        else:
            r = self._confirmar(cid, {"metodo_pago": no_acepta[0]})
            cuerpo = r.cuerpo if isinstance(r.cuerpo, dict) else {}
            esperado = "efectivo_no_disponible" if no_acepta[0] == "efectivo" else "medio_no_disponible"
            devueltos = (cuerpo.get("detalle") or {}).get("medios_cobro")
            if not r.ok:
                self.casos.append(_fallo(cat, opid, desc, r.motivo))
            elif r.estado != 422 or cuerpo.get("codigo") != esperado:
                self.casos.append(_fallo(cat, opid, desc, f"con metodo_pago {no_acepta[0]!r} esperaba 422 {esperado}, llegó {r.estado} {cuerpo.get('codigo')}"))
            elif not isinstance(devueltos, list) or sorted(devueltos) != sorted(medios):
                self.casos.append(_fallo(cat, opid, desc, f"detalle.medios_cobro es {devueltos} y el comercio publica {medios}"))
            else:
                self.casos.append(_ok(cat, opid, desc))

        acepta = [m for m in ("efectivo", "transferencia") if m in medios]
        desc = "confirmar con un metodo_pago que el comercio acepta crea el pedido cobrado por ese medio"
        if not acepta:
            self.casos.append(_omitido(cat, opid, desc, f"el comercio de prueba no acepta efectivo ni transferencia ({medios})"))
            return
        r = self._confirmar(cid, {"metodo_pago": acepta[0]})
        if not r.ok or r.estado != 201 or not isinstance(r.cuerpo, dict):
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 201, llegó {r.estado}"))
            return
        metodos = [p.get("metodo") for p in r.cuerpo.get("pagos") or [] if p.get("concepto") == "productos"]
        if metodos and all(m == acepta[0] for m in metodos):
            self.casos.append(_ok(cat, opid, desc))
        else:
            self.casos.append(_fallo(cat, opid, desc, f"pidió {acepta[0]!r} y el cobro de los productos salió con {metodos}"))
        if r.cuerpo.get("id"):
            cliente.solicitud("POST", f"{self.base_v1}/pedidos/{r.cuerpo['id']}/cancelar", headers=self._cabecera(), json_body={"motivo": "prueba de conformidad"}, timeout=self.timeout)

    # quien abre el pedido a mitad del viaje ve dónde está el repartidor -----
    # La identidad de prueba compra, opera el comercio y se declara repartidora:
    # es la única sesión que tiene la suite. Lo que el nodo no deje armar
    # (despacho, zona, alta de repartidor) se omite; lo que se prueba es que,
    # con el pedido en_camino y un reporte, GET /pedidos/{id} traiga el punto.
    def _ubicacion_en_camino(self, espera_s=20.0):
        cat, opid = "seguimiento", "verPedido"
        desc = "con el pedido en_camino, GET /pedidos/{id} trae ubicacion_repartidor, el último reporte del repartidor"

        def omitir(motivo):
            self.casos.append(_omitido(cat, opid, desc, motivo))

        oferta = "01920000-0000-7000-8000-0000000000b1"
        comercio = self._comercio_de_la_oferta(oferta)
        punto = (((comercio or {}).get("ubicacion") or {}).get("direccion") or {}).get("punto")
        envio = next((m for m in (comercio or {}).get("modalidades") or [] if m.get("tipo") == "inmediata"), None)
        if not punto or not envio:
            return omitir("el comercio de prueba no publica su punto o una modalidad 'inmediata'")
        medios = comercio.get("medios_cobro") or []
        if "efectivo" not in medios:
            return omitir("el comercio de prueba no acepta efectivo, y sin PSP no hay cómo pagar el pedido de prueba")

        cerca = {"lat": round(punto["lat"] - 0.002, 6), "lng": round(punto["lng"] + 0.002, 6)}
        declaracion = {"nombre": "Repartidora de conformidad", "vehiculo": "bici",
                       "zona": {"centro": punto, "radio_km": 5}, "cobro": {"metodos": ["efectivo"]}}
        r = cliente.solicitud("PUT", f"{self.base_v1}/repartidor", headers=self._cabecera(), json_body=declaracion, timeout=self.timeout)
        if not r.ok or r.estado not in (200, 201):
            return omitir(f"PUT /repartidor no dio de alta a la identidad de prueba como repartidora ({r.motivo or r.estado})")
        cliente.solicitud("PUT", f"{self.base_v1}/repartidor/disponibilidad", headers=self._cabecera(), json_body={"disponible": True}, timeout=self.timeout)
        cliente.solicitud("PUT", f"{self.base_v1}/repartidor/ubicacion", headers=self._cabecera(), json_body=punto, timeout=self.timeout)
        try:
            self._ubicacion_en_camino_con(cat, opid, desc, oferta, envio, punto, cerca, omitir, espera_s)
        finally:
            cliente.solicitud("PUT", f"{self.base_v1}/repartidor/disponibilidad", headers=self._cabecera(), json_body={"disponible": False}, timeout=self.timeout)

    def _ubicacion_en_camino_con(self, cat, opid, desc, oferta, envio, punto, cerca, omitir, espera_s):
        modalidad = {"tipo": "inmediata", "modalidad_id": envio.get("id"), "direccion": {"texto": "Prueba de conformidad", "punto": cerca}}
        cid = self._carrito_con(oferta, modalidad)
        if not cid:
            return omitir("no se pudo armar un carrito con envío inmediato a 200 m del comercio")
        r = self._confirmar(cid, {"metodo_pago": "efectivo"})
        pedido = r.cuerpo if r.ok and r.estado == 201 and isinstance(r.cuerpo, dict) else None
        if not pedido or not pedido.get("id"):
            return omitir(f"no se pudo confirmar el pedido con envío ({r.motivo or r.estado})")
        pid = pedido["id"]
        pasos = [("POST", f"/pedidos/{pid}/aceptar", None)]
        pasos += [("PATCH", f"/pedidos/{pid}/items/{it['id']}", {"estado": "confirmado"}) for it in pedido.get("items") or [] if it.get("id")]
        pasos.append(("POST", f"/pedidos/{pid}/listo", None))
        for metodo, ruta, cuerpo in pasos:
            r = cliente.solicitud(metodo, self.base_v1 + ruta, headers=self._cabecera(), json_body=cuerpo, timeout=self.timeout)
            if not r.ok or r.estado != 200:
                return omitir(f"{metodo} {ruta} respondió {r.motivo or r.estado} al preparar el pedido")

        viaje = None
        limite = time.monotonic() + espera_s
        while time.monotonic() < limite and not viaje:
            r = cliente.solicitud("GET", f"{self.base_v1}/viajes/ofrecidos", headers=self._cabecera(), timeout=self.timeout)
            for v in (r.cuerpo if r.ok and isinstance(r.cuerpo, list) else []):
                if any(pid in (p.get("pedidos") or []) for p in v.get("paradas") or []):
                    viaje = v
            if not viaje:
                time.sleep(1)
        if not viaje or not viaje.get("id"):
            return omitir(f"el despacho no le ofreció el viaje del pedido a la repartidora de prueba en {espera_s:.0f} s")
        r = cliente.solicitud("POST", f"{self.base_v1}/viajes/{viaje['id']}/aceptar", headers=self._cabecera(), json_body={}, timeout=self.timeout)
        if not r.ok or r.estado != 200:
            return omitir(f"aceptar el viaje respondió {r.motivo or r.estado}")
        r = cliente.solicitud("POST", f"{self.base_v1}/pedidos/{pid}/retirar", headers=self._cabecera(), json_body={}, timeout=self.timeout)
        if not r.ok or r.estado != 200:
            return omitir(f"retirar el pedido respondió {r.motivo or r.estado}")

        en_camino = {"lat": round(punto["lat"] - 0.001, 6), "lng": round(punto["lng"] + 0.001, 6)}
        r = cliente.solicitud("PUT", f"{self.base_v1}/repartidor/ubicacion", headers=self._cabecera(), json_body=en_camino, timeout=self.timeout)
        if not r.ok or r.estado != 204:
            self.casos.append(_fallo(cat, "reportarUbicacion", "reportar la ubicación con el pedido en camino responde 204", r.motivo or f"llegó {r.estado}"))
            return

        visto, cuerpo = None, None
        limite = time.monotonic() + espera_s
        while time.monotonic() < limite:
            r = cliente.solicitud("GET", f"{self.base_v1}/pedidos/{pid}", headers=self._cabecera(), timeout=self.timeout)
            cuerpo = r.cuerpo if r.ok and r.estado == 200 and isinstance(r.cuerpo, dict) else None
            visto = (cuerpo or {}).get("ubicacion_repartidor")
            if visto and abs(visto.get("lat", 0) - en_camino["lat"]) < 1e-5 and abs(visto.get("lng", 0) - en_camino["lng"]) < 1e-5:
                break
            time.sleep(0.5)
        if not cuerpo:
            self.casos.append(_fallo(cat, opid, desc, "GET /pedidos/{id} no respondió 200"))
        elif cuerpo.get("estado") != "en_camino":
            omitir(f"el pedido quedó en {cuerpo.get('estado')!r} después de retirar, no en 'en_camino'")
        elif not visto:
            self.casos.append(_fallo(cat, opid, desc, f"a {espera_s:.0f} s del reporte, el pedido en_camino no trae ubicacion_repartidor"))
        elif abs(visto.get("lat", 0) - en_camino["lat"]) >= 1e-5 or abs(visto.get("lng", 0) - en_camino["lng"]) >= 1e-5:
            self.casos.append(_fallo(cat, opid, desc, f"trae {visto} y el último reporte fue {en_camino}"))
        else:
            caso = self._chequear_esquema(opid, "el pedido en_camino cumple esquemas/pedido.json", "/pedidos/{id}", "get", cuerpo)
            if caso:
                self.casos.append(caso)
            self.casos.append(_ok(cat, opid, desc))

        r = cliente.solicitud("POST", f"{self.base_v1}/pedidos/{pid}/entregar", headers=self._cabecera(), json_body={"cobrado_en_mano": True}, timeout=self.timeout)
        desc_fin = "entregado el pedido, GET /pedidos/{id} ya no trae ubicacion_repartidor"
        if not r.ok or r.estado != 200:
            self.casos.append(_omitido(cat, opid, desc_fin, f"entregar respondió {r.motivo or r.estado}"))
            return
        r = cliente.solicitud("GET", f"{self.base_v1}/pedidos/{pid}", headers=self._cabecera(), timeout=self.timeout)
        if r.ok and isinstance(r.cuerpo, dict) and "ubicacion_repartidor" not in r.cuerpo:
            self.casos.append(_ok(cat, opid, desc_fin))
        else:
            self.casos.append(_fallo(cat, opid, desc_fin, r.motivo or f"estado {r.estado}, ubicacion_repartidor={(r.cuerpo or {}).get('ubicacion_repartidor') if isinstance(r.cuerpo, dict) else '?'}"))

    # 2. reseña: dentro de ventana se acepta una vez; la segunda, no --------
    def _resena(self, pedido_id):
        cat = "resena"

        r_yo = cliente.solicitud("GET", f"{self.base_v1}/yo", headers=self._cabecera(), timeout=self.timeout)
        autor = (r_yo.cuerpo or {}).get("identidad") if r_yo.ok and r_yo.cuerpo_es_json else None
        desc_autor = "GET /yo da la identidad de la sesión para reseñar como autor (nunca en nombre de otro)"
        if not r_yo.ok or r_yo.estado != 200 or not autor:
            self.casos.append(_fallo(cat, "crearResena", desc_autor, r_yo.motivo or f"estado {r_yo.estado}"))
            self.casos.append(_omitido(cat, "crearResena", "reseñar un pedido recién entregado", "no se pudo obtener la identidad del autor con GET /yo"))
            return
        self.casos.append(_ok(cat, "crearResena", desc_autor))

        r_pedido = cliente.solicitud("GET", f"{self.base_v1}/pedidos/{pedido_id}", headers=self._cabecera(), timeout=self.timeout)
        destinatario = (r_pedido.cuerpo or {}).get("comercio") if r_pedido.ok and r_pedido.cuerpo_es_json else None
        desc_dest = "GET /pedidos/{id} da el comercio del pedido para reseñar como destinatario"
        if not r_pedido.ok or r_pedido.estado != 200 or not destinatario:
            self.casos.append(_fallo(cat, "crearResena", desc_dest, r_pedido.motivo or f"estado {r_pedido.estado}"))
            self.casos.append(_omitido(cat, "crearResena", "reseñar un pedido recién entregado", "no se pudo obtener el comercio del pedido con GET /pedidos/{id}"))
            return
        self.casos.append(_ok(cat, "crearResena", desc_dest))

        cuerpo = {"pedido_id": pedido_id, "autor": autor, "destinatario": destinatario, "puntaje": 5, "texto": "Prueba de conformidad."}
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

        # revocarMandato toma el id del mandato, no el token del bearer:
        # openapi.yaml no da otra forma de mapear uno al otro (no hay un
        # 'crear mandato' en esta corrida que devuelva el id en el cuerpo,
        # el mandato ya viene dado por --mandato), así que se resuelve
        # listando "mis mandatos" con la sesión y tomando el único activo.
        r_list = cliente.solicitud("GET", f"{self.base_v1}/mandatos", headers=self._cabecera(), timeout=self.timeout)
        desc_list = "GET /mandatos (con sesión) lista el mandato de prueba, para revocarlo por su id"
        if not r_list.ok or r_list.estado != 200 or not r_list.cuerpo_es_json:
            self.casos.append(_fallo(cat, "listarMandatos", desc_list, r_list.motivo or f"estado {r_list.estado}"))
            self.casos.append(_omitido(cat, opid, "un mandato revocado deja de servir de inmediato", "no se pudo listar /mandatos para obtener el id"))
            return
        activos = [m for m in r_list.cuerpo if isinstance(m, dict) and m.get("estado") == "activo"]
        if len(activos) != 1:
            self.casos.append(_fallo(cat, "listarMandatos", desc_list, f"esperaba un único mandato activo para identificar el de prueba sin ambigüedad, hay {len(activos)}"))
            self.casos.append(_omitido(cat, opid, "un mandato revocado deja de servir de inmediato", "listarMandatos no identificó unívocamente el mandato de prueba"))
            return
        self.casos.append(_ok(cat, "listarMandatos", desc_list))
        mandato_id = activos[0].get("id")

        r_rev = cliente.solicitud("POST", f"{self.base_v1}/mandatos/{mandato_id}/revocar", headers=self._cabecera(), timeout=self.timeout)
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
