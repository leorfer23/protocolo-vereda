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
import base64
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

from . import acceso, cliente, rfc9421
from . import openapi_info as oi
from .nivel_a import Caso, NivelA, _fallo, _ok, _omitido
from .oraculo import cargar as cargar_esquemas

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class NivelB:
    def __init__(self, origen, *, sesion, mandato=None, timeout=cliente.TIMEOUT_S):
        self.origen = origen.rstrip("/")
        self.base_v1 = self.origen + "/v1"
        self.sesion = sesion
        self.mandato = mandato
        self.clave = None
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

    def _sesion_nueva(self) -> Optional[str]:
        """Token de una identidad nueva por /acceso. Si el nodo limita el acceso
        por minuto (429, con Retry-After) y la suite ya gastó el cupo en las
        pruebas de acceso, espera a que se renueve y reintenta una vez."""
        prueba = acceso.Acceso(self.origen, api=self.api, registry=self.registry, timeout=self.timeout)
        for intento in range(2):
            clave = acceso.Clave()
            r = prueba._post("/acceso/desafio", {"clave_publica": clave.publica})
            if r.ok and r.estado == 429 and intento == 0:
                try:
                    espera = int((r.cabeceras or {}).get("Retry-After") or 60)
                except ValueError:
                    espera = 60
                time.sleep(min(max(espera, 1), 65))
                continue
            if not (r.ok and r.estado == 201 and isinstance(r.cuerpo, dict) and r.cuerpo.get("desafio")):
                return None
            r = prueba._canje(clave, r.cuerpo)
            return (r.cuerpo or {}).get("token") if r.ok and r.estado == 201 and isinstance(r.cuerpo, dict) else None
        return None

    # -- corrida ------------------------------------------------------------
    def correr(self) -> List[Caso]:
        self.casos = []
        capacidades = acceso.capacidades(self.origen, self.timeout)
        if capacidades.get("custodia_propia") is True:
            prueba = acceso.Acceso(self.origen, api=self.api, registry=self.registry, timeout=self.timeout, alternativo=capacidades.get("alternativo") or [])
            self.casos.extend(prueba.correr())
            if not self.sesion and prueba.token:
                self.sesion, self.clave = prueba.token, prueba.clave
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
        self._nombres(capacidades)
        self._apertura_manual()
        self._videos()
        self._medios(capacidades)
        self._dispositivos()
        self._sesiones(capacidades)
        self._equipo(capacidades)
        self._topes()
        if self.mandato:
            self._mandato_tope()
            self._rotar_clave_no_por_mandato()
            self._actividad_mandato()
            self._revocacion_mandato()
        else:
            self.casos.append(_omitido("mandato", "confirmarCarrito", "tope del mandato por período (fuera_de_mandato)", "no se pasó --mandato"))
            self.casos.append(_omitido("mandato", "verActividadDeMandato", "la persona ve qué escribió su agente con el mandato", "no se pasó --mandato"))
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

        r_conf = self._confirmar(carrito_id, {})
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
            r_antes = cliente.solicitud("GET", f"{self.base_v1}/pedidos/{pedido_id}", headers=self._cabecera(), timeout=self.timeout)
            estado_antes = (r_antes.cuerpo or {}).get("estado") if r_antes.ok and r_antes.cuerpo_es_json else None
            r_res = cliente.solicitud("PATCH", f"{self.base_v1}/pedidos/{pedido_id}/items/{item_id}", headers=self._cabecera(), json_body={"estado": "confirmado"}, timeout=self.timeout)
            if not r_res.ok or r_res.estado != 200:
                self.casos.append(_fallo(cat, "resolverItemPedido", "confirmar el ítem responde 200", r_res.motivo or f"estado {r_res.estado}"))
            else:
                self.casos.append(_ok(cat, "resolverItemPedido", "confirmar el ítem responde 200"))
                self._paso_a_preparando(cat, pedido_id, estado_antes)
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

    def _paso_a_preparando(self, cat, pedido_id, estado_antes):
        desc = "el primer ítem resuelto pasa el pedido de 'aceptado' a 'preparando'"
        if estado_antes != "aceptado":
            self.casos.append(_omitido(cat, "resolverItemPedido", desc, f"antes de resolver el pedido estaba '{estado_antes}', no 'aceptado'"))
            return
        r = cliente.solicitud("GET", f"{self.base_v1}/pedidos/{pedido_id}", headers=self._cabecera(), timeout=self.timeout)
        estado = (r.cuerpo or {}).get("estado") if r.ok and r.cuerpo_es_json else None
        if estado == "preparando":
            self.casos.append(_ok(cat, "resolverItemPedido", desc))
        else:
            self.casos.append(_fallo(cat, "resolverItemPedido", desc, r.motivo or f"el pedido quedó '{estado}'"))

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
        token = self._sesion_nueva()
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

    # nombres del pedido: el que elige la persona y quién lo ve (docs/datos-y-privacidad.md) --
    def _nombres(self, capacidades):
        cat, opid = "nombres", "guardarNombre"
        url = f"{self.base_v1}/yo/nombre"
        r_yo = cliente.solicitud("GET", f"{self.base_v1}/yo", headers=self._cabecera(), timeout=self.timeout)
        if not r_yo.ok or r_yo.estado != 200 or not isinstance(r_yo.cuerpo, dict):
            self.casos.append(_omitido(cat, opid, "PUT /yo/nombre", "no se pudo leer GET /yo para guardar y después restaurar el nombre de la sesión de prueba"))
            return
        original = r_yo.cuerpo.get("nombre")

        desc = "PUT /yo/nombre con sesión lo guarda sin los espacios de los bordes y lo devuelve"
        r = cliente.solicitud("PUT", url, headers=self._cabecera(), json_body={"nombre": "  Prueba de nombres  "}, timeout=self.timeout)
        if not r.ok or r.estado != 200 or not isinstance(r.cuerpo, dict):
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 200, llegó {r.estado}"))
            return
        caso = self._chequear_esquema(opid, "la respuesta de PUT /yo/nombre cumple su esquema", "/yo/nombre", "put", r.cuerpo)
        if caso:
            self.casos.append(caso)
        if r.cuerpo.get("nombre") == "Prueba de nombres":
            self.casos.append(_ok(cat, opid, desc))
        else:
            self.casos.append(_fallo(cat, opid, desc, f"devolvió {r.cuerpo.get('nombre')!r}"))

        desc = "GET /yo muestra el nombre recién guardado"
        r_ver = cliente.solicitud("GET", f"{self.base_v1}/yo", headers=self._cabecera(), timeout=self.timeout)
        visto = r_ver.cuerpo.get("nombre") if r_ver.ok and isinstance(r_ver.cuerpo, dict) else None
        self.casos.append(_ok(cat, "verPerfil", desc) if visto == "Prueba de nombres" else _fallo(cat, "verPerfil", desc, f"GET /yo trae {visto!r}"))

        rechazos = [
            ("un nombre vacío responde 422", {"nombre": ""}),
            ("un nombre de puros espacios responde 422", {"nombre": "   "}),
            ("un nombre de más de 80 caracteres responde 422", {"nombre": "x" * 81}),
            ("un nombre que no es texto responde 422", {"nombre": 5}),
            ("un cuerpo sin 'nombre' responde 422", {}),
        ]
        for desc, cuerpo in rechazos:
            r = cliente.solicitud("PUT", url, headers=self._cabecera(), json_body=cuerpo, timeout=self.timeout)
            if not r.ok:
                self.casos.append(_fallo(cat, opid, desc, r.motivo))
            elif r.estado != 422:
                self.casos.append(_fallo(cat, opid, desc, f"esperaba 422, llegó {r.estado}"))
            else:
                caso = self._chequear_esquema(opid, desc + " con esquemas/error.json", "/yo/nombre", "put", r.cuerpo, "422")
                self.casos.append(caso or _ok(cat, opid, desc))

        if self.mandato:
            desc = "PUT /yo/nombre con un token de mandato se rechaza: solo la persona elige cómo se llama"
            r = cliente.solicitud("PUT", url, headers=self._cabecera(mandato=True), json_body={"nombre": "Otro"}, timeout=self.timeout)
            if not r.ok:
                self.casos.append(_fallo(cat, opid, desc, r.motivo))
            elif r.estado in (401, 403):
                self.casos.append(_ok(cat, opid, desc))
            else:
                self.casos.append(_fallo(cat, opid, desc, f"esperaba 403, llegó {r.estado}"))
        else:
            self.casos.append(_omitido(cat, opid, "PUT /yo/nombre rechaza un token de mandato", "no se pasó --mandato"))

        desc = "PUT /yo/nombre con null lo borra: GET /yo ya no trae 'nombre'"
        r = cliente.solicitud("PUT", url, headers=self._cabecera(), json_body={"nombre": None}, timeout=self.timeout)
        r_ver = cliente.solicitud("GET", f"{self.base_v1}/yo", headers=self._cabecera(), timeout=self.timeout)
        if not r.ok or r.estado != 200:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 200, llegó {r.estado}"))
        elif not r_ver.ok or not isinstance(r_ver.cuerpo, dict) or "nombre" in r_ver.cuerpo:
            self.casos.append(_fallo(cat, opid, desc, f"GET /yo trae {(r_ver.cuerpo or {}).get('nombre') if isinstance(r_ver.cuerpo, dict) else r_ver.estado!r}"))
        else:
            self.casos.append(_ok(cat, opid, desc))

        r = cliente.solicitud("PUT", url, headers=self._cabecera(), json_body={"nombre": original}, timeout=self.timeout)
        if not r.ok or r.estado != 200:
            self.casos.append(_fallo(cat, opid, "restaurar el nombre que la sesión de prueba tenía antes", r.motivo or f"esperaba 200, llegó {r.estado}"))

        self._nombres_en_el_pedido(capacidades)

    # Una compradora nueva compra en el comercio de prueba: el comercio ve su nombre
    # mientras el pedido está activo y ya no cuando terminó; quien no es parte, nada.
    def _nombres_en_el_pedido(self, capacidades):
        cat, opid = "nombres", "verPedido"
        if capacidades.get("custodia_propia") is not True:
            self.casos.append(_omitido(cat, opid, "quién ve el nombre del comprador en partes", "hace falta una segunda identidad y el nodo no publica acceso.custodia_propia: true"))
            return
        token = self._sesion_nueva()
        if not token:
            self.casos.append(_omitido(cat, opid, "quién ve el nombre del comprador en partes", "no se pudo abrir la sesión de una compradora nueva por /acceso"))
            return
        suya = {"Authorization": f"Bearer {token}"}

        desc = "quien entra por primera vez sin nombre no tiene 'nombre' en GET /yo: el nodo no pone el handle"
        r = cliente.solicitud("GET", f"{self.base_v1}/yo", headers=suya, timeout=self.timeout)
        if not r.ok or r.estado != 200 or not isinstance(r.cuerpo, dict):
            self.casos.append(_fallo(cat, "verPerfil", desc, r.motivo or f"esperaba 200, llegó {r.estado}"))
        elif "nombre" in r.cuerpo:
            self.casos.append(_fallo(cat, "verPerfil", desc, f"trae nombre {r.cuerpo['nombre']!r}"))
        else:
            self.casos.append(_ok(cat, "verPerfil", desc))

        nombre = "Julia de conformidad"
        r = cliente.solicitud("PUT", f"{self.base_v1}/yo/nombre", headers=suya, json_body={"nombre": nombre}, timeout=self.timeout)
        if not r.ok or r.estado != 200:
            self.casos.append(_omitido(cat, opid, "quién ve el nombre del comprador en partes", f"la compradora nueva no pudo elegir su nombre ({r.motivo or r.estado})"))
            return
        sesion_prueba = self.sesion
        self.sesion = token
        try:
            cid = self._carrito_con("01920000-0000-7000-8000-0000000000b1", {"tipo": "retiro"})
            r = self._confirmar(cid, {}) if cid else None
        finally:
            self.sesion = sesion_prueba
        pedido = r.cuerpo if r and r.ok and r.estado == 201 and isinstance(r.cuerpo, dict) else None
        if not pedido or not pedido.get("id"):
            self.casos.append(_omitido(cat, opid, "quién ve el nombre del comprador en partes", "la compradora nueva no pudo confirmar un pedido de la oferta de prueba"))
            return
        pid, compradora = pedido["id"], pedido.get("usuario")

        def partes(cabecera):
            r = cliente.solicitud("GET", f"{self.base_v1}/pedidos/{pid}", headers=cabecera, timeout=self.timeout)
            if not r.ok or r.estado != 200 or not isinstance(r.cuerpo, dict):
                return r, None
            return r, r.cuerpo.get("partes") or {}

        def usuario_de(p):
            return (p or {}).get("usuario") or {}

        try:
            desc = "activo, la compradora ve en partes su nombre y el del comercio"
            r, p = partes(suya)
            if p is None:
                self.casos.append(_fallo(cat, opid, desc, r.motivo or f"GET /pedidos/{{id}} respondió {r.estado}"))
            else:
                caso = self._chequear_esquema(opid, "el pedido con partes cumple esquemas/pedido.json", "/pedidos/{id}", "get", r.cuerpo)
                if caso:
                    self.casos.append(caso)
                comercio = p.get("comercio") or {}
                if usuario_de(p) != {"identidad": compradora, "nombre": nombre}:
                    self.casos.append(_fallo(cat, opid, desc, f"partes.usuario es {usuario_de(p)}"))
                elif comercio.get("identidad") != r.cuerpo.get("comercio") or not comercio.get("nombre"):
                    self.casos.append(_fallo(cat, opid, desc, f"partes.comercio es {comercio}"))
                else:
                    self.casos.append(_ok(cat, opid, desc))

            desc = "activo, quien administra el comercio ve el nombre de la compradora"
            r, p = partes(self._cabecera())
            administra = p is not None
            if not administra:
                self.casos.append(_omitido(cat, opid, desc, f"la sesión de prueba no ve el pedido ({r.motivo or r.estado}): no administra el comercio de la oferta de prueba"))
            elif usuario_de(p).get("nombre") != nombre:
                self.casos.append(_fallo(cat, opid, desc, f"partes.usuario es {usuario_de(p)}"))
            else:
                self.casos.append(_ok(cat, opid, desc))

            desc = "quien no es parte del pedido no lo ve: 404, sin nombres"
            otra = self._sesion_nueva()
            if not otra:
                self.casos.append(_omitido(cat, opid, desc, "no se pudo abrir la sesión de una tercera identidad por /acceso"))
            else:
                r, _ = partes({"Authorization": f"Bearer {otra}"})
                if not r.ok:
                    self.casos.append(_fallo(cat, opid, desc, r.motivo))
                elif r.estado != 404:
                    self.casos.append(_fallo(cat, opid, desc, f"esperaba 404, llegó {r.estado}"))
                else:
                    self.casos.append(_ok(cat, opid, desc))
        finally:
            r_canc = cliente.solicitud("POST", f"{self.base_v1}/pedidos/{pid}/cancelar", headers=suya, json_body={"motivo": "prueba de conformidad"}, timeout=self.timeout)
        if not r_canc.ok or r_canc.estado != 200:
            self.casos.append(_omitido(cat, opid, "terminado el pedido, quién sigue viendo el nombre", f"la compradora no pudo cancelar ({r_canc.motivo or r_canc.estado})"))
            return

        desc = "cancelado, la compradora sigue viendo su nombre en partes"
        r, p = partes(suya)
        if usuario_de(p).get("nombre") == nombre:
            self.casos.append(_ok(cat, opid, desc))
        else:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"partes.usuario es {usuario_de(p)}"))

        desc = "cancelado y sin lista de clientes aceptada, el comercio ya no ve el nombre de la compradora"
        if not administra:
            self.casos.append(_omitido(cat, opid, desc, "la sesión de prueba no administra el comercio de la oferta de prueba"))
            return
        r, p = partes(self._cabecera())
        if p is None:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"GET /pedidos/{{id}} respondió {r.estado}"))
        elif "nombre" in usuario_de(p):
            self.casos.append(_fallo(cat, opid, desc, f"partes.usuario sigue trayendo {usuario_de(p)['nombre']!r}"))
        elif usuario_de(p).get("identidad") != compradora:
            self.casos.append(_fallo(cat, opid, desc, f"partes.usuario es {usuario_de(p)}"))
        else:
            self.casos.append(_ok(cat, opid, desc))

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
            if not abierto:
                self._confirmar_cerrado(cat)
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

    def _confirmar_cerrado(self, cat):
        opid, desc = "confirmarCarrito", "con el comercio cerrado, confirmar un carrito responde 409 comercio_cerrado y no crea el pedido"
        r = cliente.solicitud("POST", f"{self.base_v1}/carritos", headers=self._cabecera(), json_body={}, timeout=self.timeout)
        carrito_id = (r.cuerpo or {}).get("id") if r.ok and r.estado == 201 and isinstance(r.cuerpo, dict) else None
        if not carrito_id:
            self.casos.append(_fallo(cat, "crearCarrito", desc, r.motivo or f"POST /carritos respondió {r.estado}"))
            return
        for metodo, ruta, cuerpo in (("POST", "items", {"oferta_id": "01920000-0000-7000-8000-0000000000b1", "cantidad": {"valor": 1, "unidad": "unidad"}}), ("PUT", "modalidad", {"tipo": "retiro"})):
            r = cliente.solicitud(metodo, f"{self.base_v1}/carritos/{carrito_id}/{ruta}", headers=self._cabecera(), json_body=cuerpo, timeout=self.timeout)
            if not r.ok or r.estado != 200:
                self.casos.append(_fallo(cat, opid, desc, r.motivo or f"{metodo} /carritos/{{id}}/{ruta} respondió {r.estado}"))
                return
        r = self._confirmar(carrito_id, {})
        codigo = (r.cuerpo or {}).get("codigo") if isinstance(r.cuerpo, dict) else None
        if not r.ok:
            self.casos.append(_fallo(cat, opid, desc, r.motivo))
        elif r.estado != 409 or codigo != "comercio_cerrado":
            self.casos.append(_fallo(cat, opid, desc, f"esperaba 409 comercio_cerrado, llegó {r.estado} {codigo!r}"))
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

        # Qué comercios administra la sesión de prueba lo decide cada nodo: puede
        # ser la identidad del comercio y no su dueña, y entonces la lista viene
        # vacía. Lo que sí vale siempre: cada uno existe y coincide con su ficha.
        desc = "cada comercio de GET /yo/comercios existe y coincide con su ficha pública"
        mios = r.cuerpo if isinstance(r.cuerpo, list) else []
        if not mios:
            self.casos.append(_omitido(cat, opid, desc, "la sesión de prueba no administra ningún comercio"))
            return
        for c in mios:
            cid = c.get("id") if isinstance(c, dict) else None
            r_c = cliente.solicitud("GET", f"{self.base_v1}/comercios/{cid}", timeout=self.timeout)
            ficha = r_c.cuerpo if r_c.ok and r_c.estado == 200 and isinstance(r_c.cuerpo, dict) else None
            if ficha is None:
                self.casos.append(_fallo(cat, opid, desc, f"GET /comercios/{cid} respondió {r_c.estado}"))
                return
            distinto = [k for k in ("identidad", "nombre", "tipo") if ficha.get(k) != c.get(k)]
            if distinto:
                self.casos.append(_fallo(cat, opid, desc, f"{cid}: {', '.join(distinto)} no coincide con la ficha"))
                return
        self.casos.append(_ok(cat, opid, desc))

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
    def _topes(self):
        """Tope de pedidos sin pagar (docs/topes.md): una identidad nueva confirma
        hasta el tope que publica el nodo y el siguiente es 429 tope_alcanzado, con
        Retry-After, detalle.tope y los pedidos a pagar o cancelar. No crea nada."""
        cat, opid = "topes", "confirmarCarrito"
        desc = "pasar el tope de pedidos sin pagar responde 429 tope_alcanzado con Retry-After y no crea el pedido"
        r = cliente.solicitud("GET", self.origen + "/.well-known/vereda.json", timeout=self.timeout)
        topes = (r.cuerpo or {}).get("topes") if r.ok and r.estado == 200 and isinstance(r.cuerpo, dict) else None
        maximo = (topes or {}).get("pedidos_sin_pagar_por_identidad")
        if not isinstance(maximo, int) or maximo < 1:
            self.casos.append(_omitido(cat, opid, desc, "el nodo no publica topes.pedidos_sin_pagar_por_identidad en /.well-known/vereda.json"))
            return
        if maximo > 10:
            self.casos.append(_omitido(cat, opid, desc, f"el tope es {maximo}: la suite no abre tantos pedidos"))
            return
        token = self._sesion_nueva()
        if not token:
            self.casos.append(_omitido(cat, opid, desc, "no se pudo abrir una sesión nueva por /acceso"))
            return
        sesion_prueba, self.sesion = self.sesion, token
        creados, r, pasados = [], None, 0
        try:
            while len(creados) <= maximo and pasados < 3:
                cid = self._carrito_con("01920000-0000-7000-8000-0000000000b1", {"tipo": "retiro"})
                if not cid:
                    break
                r = self._confirmar(cid, {}, respetar_topes=False)
                tope = _tope_alcanzado(r)
                if tope and tope.get("tope") == "pedidos_por_minuto_por_identidad":
                    pasados += 1
                    time.sleep(_espera(r))
                    r = self._confirmar(cid, {}, respetar_topes=False)
                if r.ok and r.estado == 201 and isinstance(r.cuerpo, dict) and r.cuerpo.get("id"):
                    creados.append(r.cuerpo["id"])
                    continue
                break
        finally:
            self.sesion = sesion_prueba
            for pid in creados:
                cliente.solicitud("POST", f"{self.base_v1}/pedidos/{pid}/cancelar", headers={"Authorization": f"Bearer {token}"}, json_body={"motivo": "prueba de conformidad"}, timeout=self.timeout)
        if len(creados) < maximo:
            self.casos.append(_omitido(cat, opid, desc, f"la identidad nueva confirmó {len(creados)} de {maximo} pedidos de la oferta de prueba antes del tope"))
            return
        tope = _tope_alcanzado(r)
        if len(creados) > maximo or tope is None:
            self.casos.append(_fallo(cat, opid, desc, f"con {maximo} pedidos sin pagar, el siguiente respondió {r.estado if r else 'nada'} {((r.cuerpo or {}) if r and isinstance(r.cuerpo, dict) else {}).get('codigo', '')}".strip()))
            return
        motivos = []
        try:
            if int((r.cabeceras or {}).get("Retry-After") or 0) < 1:
                motivos.append("sin Retry-After en segundos")
        except ValueError:
            motivos.append("Retry-After no es un número de segundos")
        if tope.get("tope") != "pedidos_sin_pagar_por_identidad" or tope.get("maximo") != maximo:
            motivos.append(f"detalle {tope}, se esperaba tope pedidos_sin_pagar_por_identidad y maximo {maximo}")
        if sorted(tope.get("pedidos") or []) != sorted(creados):
            motivos.append("detalle.pedidos no son los pedidos sin pagar de la identidad")
        caso = self._chequear_esquema(opid, "el 429 tope_alcanzado cumple esquemas/error.json", "/carritos/{id}/confirmar", "post", r.cuerpo, "429")
        if caso:
            self.casos.append(caso)
        self.casos.append(_fallo(cat, opid, desc, "; ".join(motivos)) if motivos else _ok(cat, opid, desc))

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

    def _confirmar(self, cid, cuerpo, cabecera=None, respetar_topes=True):
        """confirmarCarrito. La suite confirma muchos pedidos seguidos con la misma
        identidad, así que respeta los topes públicos (docs/topes.md): ante un 429
        tope_alcanzado por minuto espera Retry-After y reintenta una vez; por
        pedidos sin pagar cancela los que lista detalle.pedidos (son de la
        identidad de prueba) y reintenta."""
        cabecera = cabecera or self._cabecera()
        url = f"{self.base_v1}/carritos/{cid}/confirmar"
        r = cliente.solicitud("POST", url, headers={**cabecera, **self._idem()}, json_body=cuerpo, timeout=self.timeout)
        tope = _tope_alcanzado(r)
        if not respetar_topes or not tope:
            return r
        if tope.get("tope") == "pedidos_sin_pagar_por_identidad":
            for pid in tope.get("pedidos") or []:
                cliente.solicitud("POST", f"{self.base_v1}/pedidos/{pid}/cancelar", headers=self._cabecera(), json_body={"motivo": "prueba de conformidad"}, timeout=self.timeout)
        else:
            time.sleep(_espera(r))
        return cliente.solicitud("POST", url, headers={**cabecera, **self._idem()}, json_body=cuerpo, timeout=self.timeout)

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

        desc = "un metodo_pago fuera de efectivo/transferencia/tarjeta responde 422 y no crea el pedido"
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
        else:
            r = self._confirmar(cid, {"metodo_pago": acepta[0]})
            if not r.ok or r.estado != 201 or not isinstance(r.cuerpo, dict):
                self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 201, llegó {r.estado}"))
            else:
                metodos = [p.get("metodo") for p in r.cuerpo.get("pagos") or [] if p.get("concepto") == "productos"]
                if metodos and all(m == acepta[0] for m in metodos):
                    self.casos.append(_ok(cat, opid, desc))
                else:
                    self.casos.append(_fallo(cat, opid, desc, f"pidió {acepta[0]!r} y el cobro de los productos salió con {metodos}"))
                if r.cuerpo.get("id"):
                    cliente.solicitud("POST", f"{self.base_v1}/pedidos/{r.cuerpo['id']}/cancelar", headers=self._cabecera(), json_body={"motivo": "prueba de conformidad"}, timeout=self.timeout)

        # tarjeta solo si el nodo anuncia cobradores (docs/cobro-con-psp.md)
        desc = "confirmar con metodo_pago tarjeta crea el pedido pendiente con link_pago cuando el nodo ofrece cobradores"
        cobradores = None
        try:
            wk = cliente.solicitud("GET", f"{self.origen.rstrip('/')}/.well-known/vereda.json", timeout=self.timeout)
            if wk.ok and wk.estado == 200 and isinstance(wk.cuerpo, dict):
                cobradores = wk.cuerpo.get("cobradores")
        except Exception:
            cobradores = None
        if not cobradores:
            self.casos.append(_omitido(cat, opid, desc, "el nodo no publica cobradores en /.well-known/vereda.json"))
        elif "tarjeta" not in medios:
            self.casos.append(_omitido(cat, opid, desc, f"el comercio de prueba no tiene tarjeta en medios_cobro ({medios})"))
        else:
            cid2 = self._carrito_con(oferta, {"tipo": "retiro"})
            if not cid2:
                self.casos.append(_omitido(cat, opid, desc, "no se pudo armar un segundo carrito con retiro para tarjeta"))
            else:
                r = self._confirmar(cid2, {"metodo_pago": "tarjeta"})
                if not r.ok or r.estado != 201 or not isinstance(r.cuerpo, dict):
                    self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 201, llegó {r.estado}"))
                else:
                    pagos = [p for p in r.cuerpo.get("pagos") or [] if p.get("concepto") == "productos"]
                    ok_tarjeta = (
                        pagos
                        and all(p.get("metodo") == "tarjeta" for p in pagos)
                        and all(p.get("estado") == "pendiente" for p in pagos)
                        and all(p.get("link_pago") for p in pagos)
                        and all(p.get("psp") for p in pagos)
                        and all(p.get("psp_referencia") for p in pagos)
                        and all(p.get("vence") for p in pagos)
                    )
                    if ok_tarjeta:
                        self.casos.append(_ok(cat, opid, desc))
                    else:
                        self.casos.append(_fallo(cat, opid, desc, f"esperaba pendiente+link_pago+psp+psp_referencia+vence, llegó {pagos}"))
                    if r.cuerpo.get("id"):
                        cliente.solicitud("POST", f"{self.base_v1}/pedidos/{r.cuerpo['id']}/cancelar", headers=self._cabecera(), json_body={"motivo": "prueba de conformidad"}, timeout=self.timeout)

    # clips del local y del producto (docs/medios.md) -------------------------
    # Con el comercio y la oferta de prueba: el nodo guarda el clip tal cual y lo
    # devuelve al leerlo; uno de más de 15 s o sin póster da 422 y no pisa el que
    # estaba. Al final se restaura lo que tenían.
    def _videos(self):
        oferta_id = "01920000-0000-7000-8000-0000000000b1"
        comercio = self._comercio_de_la_oferta(oferta_id)
        if not comercio or not comercio.get("id"):
            self.casos.append(_omitido("videos", "editarComercio", "clips del local y del producto (docs/medios.md)", "no se pudo leer el comercio de la oferta de prueba con GET /ofertas/{id} y GET /comercios/{id}"))
            return
        cid = comercio["id"]
        r = cliente.solicitud("GET", f"{self.base_v1}/ofertas/{oferta_id}", timeout=self.timeout)
        oferta = r.cuerpo if r.ok and r.estado == 200 and isinstance(r.cuerpo, dict) else {}
        clip = {
            "url": "https://conformidad.invalid/clip.mp4", "tipo": "video/mp4",
            "poster": {"url": "https://conformidad.invalid/clip.jpg", "alt": "Póster de prueba"},
            "duracion_s": 8, "ancho": 1080, "alto": 1920, "bytes": 2000000, "con_sonido": False,
            "alt": "Clip de prueba de conformidad",
        }
        largo = {**clip, "duracion_s": 45}
        sin_poster = {k: v for k, v in clip.items() if k != "poster"}
        blancos = [
            ("editarComercio", "el clip del local", f"/comercios/{cid}", "/comercios/{id}", f"/comercios/{cid}", "/comercios/{id}", comercio),
            ("editarOferta", "el clip del producto", f"/comercios/{cid}/ofertas/{oferta_id}", "/comercios/{id}/ofertas/{oferta}", f"/ofertas/{oferta_id}", "/ofertas/{id}", oferta),
        ]
        for opid, que, ruta, plantilla, lectura, lectura_plantilla, original in blancos:
            if not original:
                self.casos.append(_omitido("videos", opid, f"{que} se guarda y se lee tal cual", f"no se pudo leer {lectura}"))
                continue
            desc = f"{que} se guarda con PATCH y GET {lectura_plantilla} lo devuelve tal cual"
            r = cliente.solicitud("PATCH", self.base_v1 + ruta, headers=self._cabecera(), json_body={"videos": [clip]}, timeout=self.timeout)
            if r.ok and r.estado == 403:
                self.casos.append(_omitido("videos", opid, desc, "la sesión de prueba no administra el comercio de la oferta de prueba (403)"))
                continue
            if not r.ok or r.estado != 200:
                self.casos.append(_fallo("videos", opid, desc, r.motivo or f"esperaba 200, llegó {r.estado}"))
                continue
            caso = self._chequear_esquema(opid, f"{que}: la respuesta del PATCH cumple su esquema", plantilla, "patch", r.cuerpo)
            if caso:
                self.casos.append(caso)
            leido = cliente.solicitud("GET", self.base_v1 + lectura, timeout=self.timeout)
            videos = (leido.cuerpo or {}).get("videos") if leido.ok and isinstance(leido.cuerpo, dict) else None
            if videos == [clip]:
                self.casos.append(_ok("videos", opid, desc))
            else:
                self.casos.append(_fallo("videos", opid, desc, f"se mandó {[clip]} y GET {lectura} trae {videos}"))

            for malo, porque in ((largo, "de 45 s"), (sin_poster, "sin póster")):
                desc = f"{que} {porque} responde 422 y no pisa el que estaba"
                r = cliente.solicitud("PATCH", self.base_v1 + ruta, headers=self._cabecera(), json_body={"videos": [malo]}, timeout=self.timeout)
                if not r.ok:
                    self.casos.append(_fallo("videos", opid, desc, r.motivo))
                    continue
                if r.estado != 422:
                    self.casos.append(_fallo("videos", opid, desc, f"esperaba 422, llegó {r.estado}"))
                    continue
                leido = cliente.solicitud("GET", self.base_v1 + lectura, timeout=self.timeout)
                videos = (leido.cuerpo or {}).get("videos") if leido.ok and isinstance(leido.cuerpo, dict) else None
                if videos != [clip]:
                    self.casos.append(_fallo("videos", opid, desc, f"después del 422, GET {lectura} trae {videos}"))
                    continue
                caso = self._chequear_esquema(opid, desc + " con esquemas/error.json", plantilla, "patch", r.cuerpo, "422")
                self.casos.append(caso or _ok("videos", opid, desc))

            cliente.solicitud("PATCH", self.base_v1 + ruta, headers=self._cabecera(), json_body={"videos": original.get("videos") or []}, timeout=self.timeout)

    # fotos subidas al nodo (docs/medios.md): opcional, se omite si no la anuncia --
    # Una JPEG de 16x16 con EXIF (Make "VeredaConformidad" y GPS en Buenos
    # Aires) y una PNG de 4x4. Van fijas y no aleatorias: la misma foto dos
    # veces cuenta una sola para el tope, así la suite no lo gasta de a corridas.
    JPEG_CON_EXIF = base64.b64decode(
        "/9j/4AAQSkZJRgABAQAAAQABAAD/4QCmRXhpZgAATU0AKgAAAAgAAgEPAAIAAAASAAAAJoglAAQAAAABAAAAOAAAAABWZXJlZGFDb25mb3JtaWRhZAAABAABAAIAAAACUwAAAAACAAUAAAADAAAAbgADAAIAAAACVwAAAAAEAAUAAAADAAAAhgAAAAAAAAAiAAAAAQAAACQAAAABAAAADAAAAAEAAAA6AAAAAQAAABYAAAABAAAABQAAAAH/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAAQABADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDIooor5E/SD//Z")
    PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAQAAAAECAIAAAAmkwkpAAAAE0lEQVR4nGPkqrBhgAEmOAsvBwAl7gDG5WhPYQAAAABJRU5ErkJggg==")

    def _medios(self, capacidades):
        cat, opid = "medios", "subirMedio"
        r = cliente.get(self.origen + "/.well-known/vereda.json", timeout=self.timeout)
        nodo = r.cuerpo if r.ok and r.estado == 200 and isinstance(r.cuerpo, dict) else {}
        endpoint = (nodo.get("endpoints") or {}).get("medios")
        medios = nodo.get("medios") if isinstance(nodo.get("medios"), dict) else {}
        if not endpoint:
            self.casos.append(_omitido(cat, opid, "subir fotos al nodo (docs/medios.md)", "el nodo no publica endpoints.medios: es opcional"))
            return
        desc = "con endpoints.medios, /.well-known/vereda.json trae medios con limite_bytes, tipos y maximo_por_comercio"
        errores = self._validar(self.api["components"]["schemas"]["CapacidadMedios"], medios) if medios else None
        if errores is None or errores:
            self.casos.append(_fallo(cat, "verNodo", desc, self._formatear_errores(errores) if errores else "falta 'medios'"))
            return
        self.casos.append(_ok(cat, "verNodo", desc))
        comercio = self._comercio_de_la_oferta("01920000-0000-7000-8000-0000000000b1")
        if not comercio or not comercio.get("id"):
            self.casos.append(_omitido(cat, opid, "subir fotos al nodo", "no se pudo leer el comercio de la oferta de prueba"))
            return
        url = f"{endpoint}?comercio={comercio['id']}"

        def subir(cuerpo, tipo, cabecera=None):
            h = {"Content-Type": tipo, **(self._cabecera() if cabecera is None else cabecera)}
            return cliente.solicitud_cruda("POST", url, headers=h, cuerpo=cuerpo, timeout=self.timeout)

        desc = "una JPEG con EXIF y GPS se sube (201) y la URL sirve una JPEG sin esos metadatos"
        r = subir(self.JPEG_CON_EXIF, "image/jpeg")
        if r.ok and r.estado == 403:
            self.casos.append(_omitido(cat, opid, desc, "la sesión de prueba no administra el comercio de la oferta de prueba (403)"))
            return
        if not r.ok or r.estado != 201 or not isinstance(r.cuerpo, dict):
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 201, llegó {r.estado}: {str(r.cuerpo)[:200]}"))
            return
        caso = self._chequear_esquema(opid, "la respuesta de subirMedio cumple MedioSubido", "/medios", "post", r.cuerpo, "201")
        if caso:
            self.casos.append(caso)
        subida = r.cuerpo
        try:
            f = requests.get(subida.get("url", ""), timeout=self.timeout)
            servida, tipo_servido = f.content if f.status_code == 200 else None, f.headers.get("Content-Type", "")
        except requests.RequestException as e:
            servida, tipo_servido = None, str(e)[:120]
        if servida is None:
            self.casos.append(_fallo(cat, opid, desc, f"GET {subida.get('url')} no respondió 200 ({tipo_servido})"))
        elif not servida.startswith(b"\xff\xd8") or not tipo_servido.startswith("image/jpeg"):
            self.casos.append(_fallo(cat, opid, desc, f"la URL no sirve una JPEG (Content-Type {tipo_servido!r})"))
        elif b"Exif" in servida or b"VeredaConformidad" in servida:
            self.casos.append(_fallo(cat, opid, desc, "la foto servida conserva el EXIF (cámara y ubicación)"))
        else:
            self.casos.append(_ok(cat, opid, desc))

        desc = "la misma foto subida otra vez devuelve la misma URL"
        r = subir(self.JPEG_CON_EXIF, "image/jpeg")
        otra = (r.cuerpo or {}).get("url") if r.ok and r.estado == 201 and isinstance(r.cuerpo, dict) else None
        self.casos.append(_ok(cat, opid, desc) if otra == subida.get("url") else _fallo(cat, opid, desc, f"primero {subida.get('url')}, después {otra} ({r.estado})"))

        if "image/png" in medios["tipos"]:
            desc = "una PNG se sube (201)"
            r = subir(self.PNG, "image/png")
            self.casos.append(_ok(cat, opid, desc) if r.ok and r.estado == 201 else _fallo(cat, opid, desc, r.motivo or f"esperaba 201, llegó {r.estado}"))

        malos = [
            ("texto con Content-Type image/jpeg responde 415 tipo_no_admitido: el nodo mira los bytes", b"no soy una foto", "image/jpeg", None, 415, "tipo_no_admitido"),
            (f"más de limite_bytes ({medios['limite_bytes']}) responde 413 medio_muy_grande", self.JPEG_CON_EXIF + b"\0" * medios["limite_bytes"], "image/jpeg", None, 413, "medio_muy_grande"),
            ("sin token responde 401", self.JPEG_CON_EXIF, "image/jpeg", {}, 401, None),
        ]
        if capacidades.get("custodia_propia") is True:
            ajena = self._sesion_nueva()
            if ajena:
                malos.append(("otra identidad, que no administra el comercio, responde 403", self.JPEG_CON_EXIF, "image/jpeg", {"Authorization": f"Bearer {ajena}"}, 403, None))
        for desc, cuerpo, tipo, cabecera, estado, codigo in malos:
            r = subir(cuerpo, tipo, cabecera)
            if not r.ok or r.estado != estado:
                self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba {estado}, llegó {r.estado}"))
            elif codigo and (r.cuerpo or {}).get("codigo") != codigo:
                self.casos.append(_fallo(cat, opid, desc, f"el código vino {(r.cuerpo or {}).get('codigo')!r}"))
            else:
                self.casos.append(self._chequear_esquema(opid, desc + " con esquemas/error.json", "/medios", "post", r.cuerpo, str(estado)) or _ok(cat, opid, desc))

    # equipo del comercio (docs/equipo.md) -----------------------------------
    # La sesión de prueba es la dueña del comercio de prueba; una identidad nueva
    # de /acceso entra al equipo solo con 'pedidos'. Se prueba lo que no puede
    # fallar: entra con su clave, puede lo suyo y nada más, y sacarla corta ya.
    # notificaciones push (docs/notificaciones-push.md): opcional ---------------
    def _sesiones(self, capacidades):
        """Sesiones a la vista y firma fresca (docs/acceso.md, puntos 6 y 7), con
        una identidad nueva que entra dos veces con la misma clave."""
        cat = "sesiones"
        if capacidades.get("custodia_propia") is not True:
            self.casos.append(_omitido(cat, "listarSesiones", "sesiones de la persona", "el nodo no publica acceso.custodia_propia: true"))
            return
        prueba = acceso.Acceso(self.origen, api=self.api, registry=self.registry, timeout=self.timeout)
        clave = acceso.Clave()
        d = prueba._desafio(clave)
        r = prueba._canje(clave, d, etiqueta="conformidad A") if d else None
        uno = (r.cuerpo or {}).get("token") if r and r.ok and r.estado == 201 and isinstance(r.cuerpo, dict) else None
        dos = (prueba._entrar(clave) or {}).get("token") if uno else None
        if not uno or not dos:
            self.casos.append(_omitido(cat, "listarSesiones", "sesiones de la persona", "no se pudieron abrir dos sesiones por /acceso"))
            return
        base = self.base_v1 + "/yo/sesiones"
        con = lambda token: {"Authorization": f"Bearer {token}"}

        opid, desc = "listarSesiones", "lista las dos sesiones, una sola con actual: true y con la etiqueta declarada, sin el token"
        r = cliente.solicitud("GET", base, headers=con(uno), timeout=self.timeout)
        lista = r.cuerpo if r.ok and r.estado == 200 and isinstance(r.cuerpo, list) else None
        actuales = [x for x in lista or [] if isinstance(x, dict) and x.get("actual") is True]
        if lista is None:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 200 con un array, llegó {r.estado}"))
            return
        if len(lista) != 2 or len(actuales) != 1 or actuales[0].get("etiqueta") != "conformidad A":
            self.casos.append(_fallo(cat, opid, desc, f"llegaron {len(lista)} sesiones, {len(actuales)} actuales: {lista}"))
            return
        if uno in str(lista) or dos in str(lista):
            self.casos.append(_fallo(cat, opid, desc, "la lista trae un token"))
        else:
            self.casos.append(self._chequear_esquema(opid, desc, "/yo/sesiones", "get", lista) or _ok(cat, opid, desc))

        if self.mandato:
            desc = "un token de mandato no ve las sesiones (403)"
            r = cliente.solicitud("GET", base, headers=self._cabecera(mandato=True), timeout=self.timeout)
            self.casos.append(_ok(cat, opid, desc) if r.ok and r.estado == 403 else _fallo(cat, opid, desc, r.motivo or f"esperaba 403, llegó {r.estado}"))

        fresca = capacidades.get("firma_fresca") if isinstance(capacidades.get("firma_fresca"), dict) else None
        opid = "exportarCuenta"
        if not fresca:
            self.casos.append(_omitido(cat, opid, "firma fresca en exportarCuenta", "el nodo no publica acceso.firma_fresca"))
        else:
            url = self.base_v1 + "/yo/exportar"
            path = "/v1/yo/exportar"
            otra = acceso.Clave()
            desc = "una firma fresca de otra clave responde 403 firma_fresca_requerida, aun en fase de gracia"
            r = cliente.solicitud("GET", url, headers={**con(uno), **rfc9421.firma_fresca(metodo="GET", path=path, clave_privada=otra.privada, keyid=otra.publica)}, timeout=self.timeout)
            codigo = (r.cuerpo or {}).get("codigo") if r.ok and isinstance(r.cuerpo, dict) else None
            self.casos.append(_ok(cat, opid, desc) if r.ok and r.estado == 403 and codigo == "firma_fresca_requerida" else _fallo(cat, opid, desc, r.motivo or f"esperaba 403 firma_fresca_requerida, llegó {r.estado} {codigo}"))
            desc = "una firma fresca vencida responde 403 firma_fresca_requerida"
            r = cliente.solicitud("GET", url, headers={**con(uno), **rfc9421.firma_fresca(metodo="GET", path=path, clave_privada=clave.privada, keyid=clave.publica, created=int(time.time()) - 3600)}, timeout=self.timeout)
            codigo = (r.cuerpo or {}).get("codigo") if r.ok and isinstance(r.cuerpo, dict) else None
            self.casos.append(_ok(cat, opid, desc) if r.ok and r.estado == 403 and codigo == "firma_fresca_requerida" else _fallo(cat, opid, desc, r.motivo or f"esperaba 403 firma_fresca_requerida, llegó {r.estado} {codigo}"))
            desc = "con la firma fresca de la clave activa, exportar responde 200"
            r = cliente.solicitud("GET", url, headers={**con(uno), **rfc9421.firma_fresca(metodo="GET", path=path, clave_privada=clave.privada, keyid=clave.publica)}, timeout=self.timeout)
            self.casos.append(_ok(cat, opid, desc) if r.ok and r.estado == 200 else _fallo(cat, opid, desc, r.motivo or f"esperaba 200, llegó {r.estado}"))
            if fresca.get("exigida") is True:
                desc = "el nodo la exige: sin firma fresca responde 403 firma_fresca_requerida"
                r = cliente.solicitud("GET", url, headers=con(uno), timeout=self.timeout)
                codigo = (r.cuerpo or {}).get("codigo") if r.ok and isinstance(r.cuerpo, dict) else None
                self.casos.append(_ok(cat, opid, desc) if r.ok and r.estado == 403 and codigo == "firma_fresca_requerida" else _fallo(cat, opid, desc, r.motivo or f"esperaba 403, llegó {r.estado} {codigo}"))

        opid, desc = "cerrarOtrasSesiones", "cerrar las otras deja afuera a la segunda sesión y no a la actual"
        r = cliente.solicitud("DELETE", base, headers=con(uno), timeout=self.timeout)
        cerradas = (r.cuerpo or {}).get("cerradas") if r.ok and r.estado == 200 and isinstance(r.cuerpo, dict) else None
        y_uno, y_dos = prueba._yo(uno), prueba._yo(dos)
        if cerradas != 1 or not (y_dos.ok and y_dos.estado == 401) or not (y_uno.ok and y_uno.estado == 200):
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"cerradas={cerradas}, /yo con la otra {y_dos.estado}, con la actual {y_uno.estado}"))
        else:
            self.casos.append(_ok(cat, opid, desc))

        opid, desc = "cerrarSesionPorId", "cerrar la propia por id responde 204, el token deja de valer y cerrarla otra vez responde 404"
        url = f"{base}/{actuales[0].get('id')}"
        r = cliente.solicitud("DELETE", url, headers=con(uno), timeout=self.timeout)
        y_uno = prueba._yo(uno)
        otra_vez = cliente.solicitud("DELETE", url, headers=con(self.sesion), timeout=self.timeout)
        if not (r.ok and r.estado == 204) or not (y_uno.ok and y_uno.estado == 401) or not (otra_vez.ok and otra_vez.estado == 404):
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"cerrar {r.estado}, /yo después {y_uno.estado}, otra vez {otra_vez.estado}"))
        else:
            self.casos.append(_ok(cat, opid, desc))

    def _dispositivos(self):
        cat, opid = "push", "registrarDispositivo"
        r = cliente.get(self.origen + "/.well-known/vereda.json", timeout=self.timeout)
        nodo = r.cuerpo if r.ok and r.estado == 200 and isinstance(r.cuerpo, dict) else {}
        push = nodo.get("push") if isinstance(nodo.get("push"), dict) else None
        base = self.base_v1 + "/yo/dispositivos"
        token = uuid.uuid4().hex + uuid.uuid4().hex
        if not push:
            desc = "sin push en /.well-known/vereda.json, registrarDispositivo responde 501 no_implementado"
            r = cliente.solicitud("POST", base, headers=self._cabecera(), json_body={"plataforma": "apns", "app": "ar.vereda.conformidad", "token": token}, timeout=self.timeout)
            if not r.ok:
                self.casos.append(_fallo(cat, opid, desc, r.motivo))
            elif r.estado != 501:
                self.casos.append(_fallo(cat, opid, desc, f"esperaba 501, llegó {r.estado}"))
            else:
                self.casos.append(_ok(cat, opid, desc))
            return
        apps = push.get("apps") or []
        if not apps or not apps[0].get("plataformas"):
            self.casos.append(_fallo(cat, opid, "push.apps trae al menos una app con sus plataformas", f"push es {push}"))
            return
        app, plataforma = apps[0]["app"], apps[0]["plataformas"][0]
        registro = {"plataforma": plataforma, "app": app, "token": token}

        desc = "registrar un token nuevo responde 201 con el dispositivo, sin el token"
        r = cliente.solicitud("POST", base, headers=self._cabecera(), json_body=registro, timeout=self.timeout)
        if not r.ok or r.estado != 201 or not isinstance(r.cuerpo, dict):
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 201, llegó {r.estado}"))
            return
        dispositivo = r.cuerpo
        if token in str(dispositivo):
            self.casos.append(_fallo(cat, opid, desc, "la respuesta trae el token"))
        else:
            self.casos.append(self._chequear_esquema(opid, desc, "/yo/dispositivos", "post", dispositivo, "201") or _ok(cat, opid, desc))

        desc = "registrar el mismo token otra vez responde 200 con el mismo dispositivo"
        r = cliente.solicitud("POST", base, headers=self._cabecera(), json_body=registro, timeout=self.timeout)
        if not r.ok or r.estado != 200:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 200, llegó {r.estado}"))
        elif (r.cuerpo or {}).get("id") != dispositivo.get("id"):
            self.casos.append(_fallo(cat, opid, desc, f"primero {dispositivo.get('id')}, después {(r.cuerpo or {}).get('id')}"))
        else:
            self.casos.append(_ok(cat, opid, desc))

        desc = "una app que el nodo no sabe avisar responde 422 app_no_soportada con detalle.apps"
        r = cliente.solicitud("POST", base, headers=self._cabecera(), json_body={**registro, "app": "ar.vereda.conformidad.inexistente"}, timeout=self.timeout)
        codigo = (r.cuerpo or {}).get("codigo") if r.ok and isinstance(r.cuerpo, dict) else None
        if not r.ok or r.estado != 422 or codigo != "app_no_soportada":
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 422 app_no_soportada, llegó {r.estado} {codigo}"))
        elif not isinstance(((r.cuerpo or {}).get("detalle") or {}).get("apps"), list):
            self.casos.append(_fallo(cat, opid, desc, "falta detalle.apps"))
        else:
            self.casos.append(_ok(cat, opid, desc))

        if self.mandato:
            desc = "un token de mandato no registra dispositivos (401 o 403)"
            r = cliente.solicitud("POST", base, headers=self._cabecera(mandato=True), json_body={**registro, "token": uuid.uuid4().hex}, timeout=self.timeout)
            if not r.ok or r.estado not in (401, 403):
                self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 401 o 403, llegó {r.estado}"))
            else:
                self.casos.append(_ok(cat, opid, desc))

        opid, desc = "listarDispositivos", "el dispositivo registrado aparece en GET /yo/dispositivos"
        r = cliente.solicitud("GET", base, headers=self._cabecera(), timeout=self.timeout)
        ids = [d.get("id") for d in r.cuerpo] if r.ok and r.estado == 200 and isinstance(r.cuerpo, list) else None
        if ids is None or dispositivo.get("id") not in ids:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"llegó {r.estado}, ids {ids}"))
        else:
            self.casos.append(self._chequear_esquema(opid, desc, "/yo/dispositivos", "get", r.cuerpo) or _ok(cat, opid, desc))

        opid, desc = "borrarDispositivo", "borrarlo responde 204, deja de aparecer y borrarlo otra vez responde 404"
        url = f"{base}/{dispositivo.get('id')}"
        r = cliente.solicitud("DELETE", url, headers=self._cabecera(), timeout=self.timeout)
        if not r.ok or r.estado != 204:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 204, llegó {r.estado}"))
            return
        lista = cliente.solicitud("GET", base, headers=self._cabecera(), timeout=self.timeout)
        otra = cliente.solicitud("DELETE", url, headers=self._cabecera(), timeout=self.timeout)
        quedan = [d.get("id") for d in lista.cuerpo] if lista.ok and isinstance(lista.cuerpo, list) else []
        if dispositivo.get("id") in quedan:
            self.casos.append(_fallo(cat, opid, desc, "sigue en GET /yo/dispositivos"))
        elif not otra.ok or otra.estado != 404:
            self.casos.append(_fallo(cat, opid, desc, otra.motivo or f"la segunda vez esperaba 404, llegó {otra.estado}"))
        else:
            self.casos.append(_ok(cat, opid, desc))

    def _equipo(self, capacidades):
        cat = "equipo"
        if capacidades.get("custodia_propia") is not True:
            self.casos.append(_omitido(cat, "invitarAlEquipo", "equipo del comercio (docs/equipo.md)", "hace falta una segunda identidad y el nodo no publica acceso.custodia_propia: true"))
            return
        comercio = self._comercio_de_la_oferta("01920000-0000-7000-8000-0000000000b1")
        if not comercio or not comercio.get("id"):
            self.casos.append(_omitido(cat, "invitarAlEquipo", "equipo del comercio", "no se pudo leer el comercio de la oferta de prueba"))
            return
        cid = comercio["id"]
        base = f"{self.base_v1}/comercios/{cid}/equipo"

        def con(token):
            return {"Authorization": f"Bearer {token}"}

        opid, desc = "verEquipo", "la dueña lee el equipo (200, esquemas/equipo.json)"
        r = cliente.solicitud("GET", base, headers=self._cabecera(), timeout=self.timeout)
        if r.ok and r.estado == 501:
            self.casos.append(_omitido(cat, opid, "equipo del comercio (docs/equipo.md)", "el nodo responde 501: no implementa equipos"))
            return
        if r.ok and r.estado == 403:
            self.casos.append(_omitido(cat, opid, "equipo del comercio", "la sesión de prueba no administra el comercio de la oferta de prueba (403)"))
            return
        if not r.ok or r.estado != 200:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 200, llegó {r.estado}"))
            return
        self.casos.append(self._chequear_esquema(opid, desc, "/comercios/{id}/equipo", "get", r.cuerpo) or _ok(cat, opid, desc))

        miembro, otra = self._sesion_nueva(), self._sesion_nueva()
        if not miembro or not otra:
            self.casos.append(_omitido(cat, "aceptarInvitacion", "equipo del comercio", "no se pudieron abrir dos identidades nuevas por /acceso"))
            return
        r = cliente.solicitud("GET", f"{self.base_v1}/yo", headers=con(miembro), timeout=self.timeout)
        yo = (r.cuerpo or {}).get("identidad") if r.ok and r.estado == 200 and isinstance(r.cuerpo, dict) else None

        opid, desc = "invitarAlEquipo", "la dueña invita con rol 'atención' y permiso 'pedidos' (201, con codigo y enlace vereda://equipo?)"
        r = cliente.solicitud("POST", f"{base}/invitaciones", headers=self._cabecera(), json_body={"rol": "atención", "permisos": ["pedidos"]}, timeout=self.timeout)
        inv = r.cuerpo if r.ok and r.estado == 201 and isinstance(r.cuerpo, dict) else None
        if not inv or not inv.get("codigo") or not str(inv.get("enlace", "")).startswith("vereda://equipo?"):
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"llegó {r.estado}: {str(r.cuerpo)[:200]}"))
            return
        self.casos.append(self._chequear_esquema(opid, desc, "/comercios/{id}/equipo/invitaciones", "post", inv, "201") or _ok(cat, opid, desc))

        opid, desc = "invitarAlEquipo", "permisos que no existen ('exportar') responden 422"
        r = cliente.solicitud("POST", f"{base}/invitaciones", headers=self._cabecera(), json_body={"rol": "x", "permisos": ["exportar"]}, timeout=self.timeout)
        self.casos.append(_ok(cat, opid, desc) if r.ok and r.estado == 422 else _fallo(cat, opid, desc, r.motivo or f"esperaba 422, llegó {r.estado}"))

        opid, desc = "verInvitacion", "la persona invitada ve la invitación antes de aceptarla (200): comercio, rol y permisos, sin codigo ni enlace"
        r = cliente.solicitud("GET", f"{self.base_v1}/equipo/invitaciones/{inv['codigo']}", headers=con(miembro), timeout=self.timeout)
        vista = r.cuerpo if r.ok and r.estado == 200 and isinstance(r.cuerpo, dict) else None
        if not vista:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 200, llegó {r.estado}: {str(r.cuerpo)[:200]}"))
        else:
            mal = [k for k, v in (("rol", "atención"), ("permisos", ["pedidos"]), ("comercio", inv.get("comercio"))) if vista.get(k) != v] + [k for k in ("codigo", "enlace") if k in vista]
            caso = self._chequear_esquema(opid, desc, "/equipo/invitaciones/{codigo}", "get", vista, "200")
            self.casos.append(caso if caso and caso.resultado == "fallo" else (_fallo(cat, opid, desc, f"no coincide: {', '.join(mal)}") if mal else _ok(cat, opid, desc)))

        opid, desc = "aceptarInvitacion", "la persona invitada acepta con su sesión (201): entra con su identidad, el rol y los permisos de la invitación"
        r = cliente.solicitud("POST", f"{self.base_v1}/equipo/aceptar", headers=con(miembro), json_body={"codigo": inv["codigo"]}, timeout=self.timeout)
        m = r.cuerpo if r.ok and r.estado == 201 and isinstance(r.cuerpo, dict) else None
        if not m:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 201, llegó {r.estado}: {str(r.cuerpo)[:200]}"))
            return
        mal = [k for k, v in (("rol", "atención"), ("permisos", ["pedidos"])) if m.get(k) != v] + (["identidad"] if yo and m.get("identidad") != yo else [])
        caso = self._chequear_esquema(opid, desc, "/equipo/aceptar", "post", m, "201")
        self.casos.append(caso if caso and caso.resultado == "fallo" else (_fallo(cat, opid, desc, f"no coincide: {', '.join(mal)}") if mal else _ok(cat, opid, desc)))
        yo = yo or m.get("identidad")

        opid, desc = "aceptarInvitacion", "el mismo código otra vez, con otra identidad, responde 410 invitacion_invalida"
        r = cliente.solicitud("POST", f"{self.base_v1}/equipo/aceptar", headers=con(otra), json_body={"codigo": inv["codigo"]}, timeout=self.timeout)
        self.casos.append(_ok(cat, opid, desc) if r.ok and r.estado == 410 and (r.cuerpo or {}).get("codigo") == "invitacion_invalida" else _fallo(cat, opid, desc, r.motivo or f"llegó {r.estado} {(r.cuerpo or {}).get('codigo') if isinstance(r.cuerpo, dict) else ''}"))

        opid, desc = "verInvitacion", "una invitación ya aceptada responde 410 invitacion_invalida"
        r = cliente.solicitud("GET", f"{self.base_v1}/equipo/invitaciones/{inv['codigo']}", headers=con(otra), timeout=self.timeout)
        self.casos.append(_ok(cat, opid, desc) if r.ok and r.estado == 410 and (r.cuerpo or {}).get("codigo") == "invitacion_invalida" else _fallo(cat, opid, desc, r.motivo or f"llegó {r.estado}"))

        opid, desc = "listarMisComercios", "el comercio aparece en GET /yo/comercios del miembro, con rol y permisos"
        r = cliente.solicitud("GET", f"{self.base_v1}/yo/comercios", headers=con(miembro), timeout=self.timeout)
        suyo = next((c for c in (r.cuerpo if r.ok and isinstance(r.cuerpo, list) else []) if isinstance(c, dict) and c.get("id") == cid), None)
        self.casos.append(_ok(cat, opid, desc) if suyo and suyo.get("permisos") == ["pedidos"] and suyo.get("rol") == "atención" else _fallo(cat, opid, desc, f"llegó {r.estado}: {str(suyo or r.cuerpo)[:200]}"))

        opid, desc = "listarPedidosDelComercio", "con 'pedidos', el miembro lee la bandeja del comercio (200)"
        r = cliente.solicitud("GET", f"{self.base_v1}/comercios/{cid}/pedidos?limite=1", headers=con(miembro), timeout=self.timeout)
        self.casos.append(_ok(cat, opid, desc) if r.ok and r.estado == 200 else _fallo(cat, opid, desc, r.motivo or f"esperaba 200, llegó {r.estado}"))

        sin = [
            ("editarComercio", "PATCH", f"{self.base_v1}/comercios/{cid}", {"notas_para_agentes": comercio.get("notas_para_agentes") or "conformidad"}, "datos"),
            ("metricasDelComercio", "GET", f"{self.base_v1}/comercios/{cid}/metricas", None, "numeros"),
            ("exportarComercio", "GET", f"{self.base_v1}/comercios/{cid}/exportar", None, None),
            ("invitarAlEquipo", "POST", f"{base}/invitaciones", {"rol": "x", "permisos": ["pedidos"]}, "equipo"),
        ]
        for opid, metodo, url, cuerpo, falta in sin:
            desc = f"sin '{falta or 'ser la dueña'}', el miembro recibe 403 sin_permiso y no cambia nada"
            r = cliente.solicitud(metodo, url, headers=con(miembro), json_body=cuerpo, timeout=self.timeout)
            codigo = (r.cuerpo or {}).get("codigo") if isinstance(r.cuerpo, dict) else None
            detalle = ((r.cuerpo or {}).get("detalle") or {}) if isinstance(r.cuerpo, dict) else {}
            if not r.ok or r.estado != 403 or codigo != "sin_permiso":
                self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 403 sin_permiso, llegó {r.estado} {codigo}"))
            elif falta and detalle.get("falta") != falta:
                self.casos.append(_fallo(cat, opid, desc, f"detalle.falta vino {detalle.get('falta')!r}"))
            else:
                self.casos.append(_ok(cat, opid, desc))

        opid, desc = "sacarDelEquipo", "sacar a la dueña responde 403 sin_permiso"
        r = cliente.solicitud("GET", base, headers=con(miembro), timeout=self.timeout)
        duena = (r.cuerpo or {}).get("duena") if r.ok and r.estado == 200 and isinstance(r.cuerpo, dict) else None
        if duena:
            r = cliente.solicitud("DELETE", f"{base}/{duena}", headers=self._cabecera(), timeout=self.timeout)
            self.casos.append(_ok(cat, opid, desc) if r.ok and r.estado == 403 and (r.cuerpo or {}).get("codigo") == "sin_permiso" else _fallo(cat, opid, desc, r.motivo or f"esperaba 403, llegó {r.estado}"))
        else:
            self.casos.append(_fallo(cat, "verEquipo", "un miembro lee el equipo y trae 'duena'", f"llegó {r.estado}"))

        opid, desc = "sacarDelEquipo", "la dueña saca al miembro (204) y desde la llamada siguiente recibe 403 no_es_el_dueno"
        r = cliente.solicitud("DELETE", f"{base}/{yo}", headers=self._cabecera(), timeout=self.timeout)
        if not r.ok or r.estado != 204:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 204, llegó {r.estado}"))
            return
        r = cliente.solicitud("GET", f"{self.base_v1}/comercios/{cid}/pedidos?limite=1", headers=con(miembro), timeout=self.timeout)
        r_yo = cliente.solicitud("GET", f"{self.base_v1}/yo/comercios", headers=con(miembro), timeout=self.timeout)
        sigue = any(isinstance(c, dict) and c.get("id") == cid for c in (r_yo.cuerpo if r_yo.ok and isinstance(r_yo.cuerpo, list) else []))
        if not r.ok or r.estado != 403 or (r.cuerpo or {}).get("codigo") != "no_es_el_dueno":
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"después de sacarlo, la bandeja respondió {r.estado}"))
        elif sigue:
            self.casos.append(_fallo(cat, opid, desc, "el comercio sigue en su GET /yo/comercios"))
        else:
            self.casos.append(_ok(cat, opid, desc))

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
        self._oferta_dice_quien_paga(viaje, pid)
        r = cliente.solicitud("POST", f"{self.base_v1}/viajes/{viaje['id']}/aceptar", headers=self._cabecera(), json_body={}, timeout=self.timeout)
        if not r.ok or r.estado != 200:
            return omitir(f"aceptar el viaje respondió {r.motivo or r.estado}")
        if not self._traspaso_firmado(pid, "retiro", {}):
            return omitir("no se pudo retirar el pedido")

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

        desc_fin = "entregado el pedido, GET /pedidos/{id} ya no trae ubicacion_repartidor"
        if not self._traspaso_firmado(pid, "entrega", {"cobrado_en_mano": True}):
            self.casos.append(_omitido(cat, opid, desc_fin, "no se pudo entregar el pedido"))
            return
        r = cliente.solicitud("GET", f"{self.base_v1}/pedidos/{pid}", headers=self._cabecera(), timeout=self.timeout)
        if r.ok and isinstance(r.cuerpo, dict) and "ubicacion_repartidor" not in r.cuerpo:
            self.casos.append(_ok(cat, opid, desc_fin))
        else:
            self.casos.append(_fallo(cat, opid, desc_fin, r.motivo or f"estado {r.estado}, ubicacion_repartidor={(r.cuerpo or {}).get('ubicacion_repartidor') if isinstance(r.cuerpo, dict) else '?'}"))
        self._rendicion(pid)

    # la oferta dice quién le paga al repartidor, cuánto y cómo ------------
    # docs/repartidores.md, punto d: antes de aceptar, por pedido, 'cobros'
    # con pagador, medio y monto; los de concepto 'envio' suman el envío.
    def _oferta_dice_quien_paga(self, viaje, pid):
        cat, opid = "oferta", "listarViajesOfrecidos"
        caso = self._chequear_esquema(opid, "el viaje ofrecido cumple esquemas/viaje.json", "/viajes/ofrecidos", "get", [viaje])
        if caso:
            self.casos.append(caso)
        desc = "la oferta dice, por pedido, quién le paga el envío al repartidor, cuánto y por qué medio (pago_repartidor.por_pedido[].cobros)"
        pp = next((x for x in (viaje.get("pago_repartidor") or {}).get("por_pedido") or [] if x.get("pedido_id") == pid), None)
        if not pp:
            self.casos.append(_fallo(cat, opid, desc, "pago_repartidor.por_pedido no trae el pedido del viaje"))
            return
        cobros = pp.get("cobros")
        if not isinstance(cobros, list):
            self.casos.append(_fallo(cat, opid, desc, "el pedido no trae 'cobros'"))
            return
        envio = sum(((c.get("monto") or {}).get("centavos") or 0) for c in cobros if c.get("concepto") == "envio")
        monto = (pp.get("monto") or {}).get("centavos") or 0
        if envio != monto:
            self.casos.append(_fallo(cat, opid, desc, f"los cobros de envío suman {envio} centavos y el envío del pedido es {monto}"))
            return
        self.casos.append(_ok(cat, opid, desc))

    # retirar y entregar firmados por el repartidor --------------------------
    # docs/repartidores.md, punto j: con una firma que no verifica, 422 y el
    # pedido no se mueve; con la clave de la suite (custodia propia) firma la
    # suite, y si no, la pone el nodo que la custodia. Lo guardado en
    # firmas.retiro / firmas.entrega verifica sobre el traspaso rearmado.
    def _traspaso_firmado(self, pid, accion, cuerpo) -> bool:
        cat = "firma_repartidor"
        opid = "retirarPedido" if accion == "retiro" else "entregarPedido"
        ruta = f"{self.base_v1}/pedidos/{pid}/" + ("retirar" if accion == "retiro" else "entregar")
        r = cliente.solicitud("GET", f"{self.base_v1}/yo", headers=self._cabecera(), timeout=self.timeout)
        yo = (r.cuerpo or {}).get("identidad") if r.ok and isinstance(r.cuerpo, dict) else None
        if not yo:
            self.casos.append(_omitido(cat, opid, f"{accion} firmado por el repartidor", "GET /yo no dijo la identidad de la sesión"))
            return False

        def traspaso(instante):
            return {"accion": accion, "pedido_id": pid, "repartidor": yo, "instante": instante}

        ahora = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        falsa = acceso.Clave()
        mala = {"firmante": yo, "clave_publica": falsa.publica, "valor": falsa.firmar({"otra": "cosa"}), "instante": ahora}
        desc = f"{opid} con una firma que no verifica responde 422 firma_invalida y no mueve el pedido"
        r = cliente.solicitud("POST", ruta, headers=self._cabecera(), json_body={**cuerpo, "firma": mala}, timeout=self.timeout)
        codigo = (r.cuerpo or {}).get("codigo") if isinstance(r.cuerpo, dict) else None
        if r.ok and r.estado == 422 and codigo == "firma_invalida":
            self.casos.append(_ok(cat, opid, desc))
        else:
            self.casos.append(_fallo(cat, opid, desc, f"llegó {r.estado} {codigo or r.motivo}"))
            if r.ok and r.estado == 200:
                return False

        firma = None
        if self.clave:
            firma = {"firmante": yo, "clave_publica": self.clave.publica, "valor": self.clave.firmar(traspaso(ahora)), "instante": ahora}
        r = cliente.solicitud("POST", ruta, headers=self._cabecera(), json_body={**cuerpo, **({"firma": firma} if firma else {})}, timeout=self.timeout)
        codigo = (r.cuerpo or {}).get("codigo") if isinstance(r.cuerpo, dict) else None
        if r.ok and r.estado == 422 and codigo == "firma_requerida":
            self.casos.append(_omitido(cat, opid, f"{accion} firmado por el repartidor", "la sesión de prueba es de custodia propia y la suite no tiene su clave: pasá la sesión por /acceso"))
            return False
        if not r.ok or r.estado != 200:
            self.casos.append(_fallo(cat, opid, f"{opid} {'con la firma del repartidor' if firma else 'sin firma, con la clave custodiada por el nodo'} responde 200", r.motivo or f"llegó {r.estado} {codigo or ''}"))
            return False

        desc = f"firmas.{accion} es la del repartidor y verifica sobre el traspaso {{accion, pedido_id, repartidor, instante}} contra su historial de claves"
        r = cliente.solicitud("GET", f"{self.base_v1}/pedidos/{pid}", headers=self._cabecera(), timeout=self.timeout)
        guardada = (((r.cuerpo or {}).get("firmas") or {}).get(accion)) if r.ok and isinstance(r.cuerpo, dict) else None
        if not isinstance(guardada, dict):
            self.casos.append(_fallo(cat, opid, desc, f"GET /pedidos/{{id}} no trae firmas.{accion}"))
            return True
        if guardada.get("firmante") != yo:
            self.casos.append(_fallo(cat, opid, desc, f"firmada por {guardada.get('firmante')!r}, no por el repartidor {yo!r}"))
            return True
        ok, motivo = NivelA(self.origen, timeout=self.timeout)._verificar_firma({**traspaso(guardada.get("instante")), "firma": guardada}, {})
        self.casos.append(_ok(cat, opid, desc) if ok else _fallo(cat, opid, desc, motivo))
        return True

    # la rendición del efectivo al comercio, firmada por los dos ------------
    # docs/repartidores.md, punto l: el pedido en efectivo entregado por la
    # repartidora trae 'rendicion' con lo que cobró por cuenta del comercio.
    # Declarar con una firma que no verifica da 422; declarar bien la deja
    # 'declarada'; el comercio confirma el mismo monto y queda 'confirmada', con
    # las dos constancias verificando contra el historial de su actor. Después,
    # otra constancia da 409 rendicion_confirmada. La sesión de prueba es a la
    # vez la repartidora y quien administra el comercio.
    def _rendicion(self, pid):
        cat = "rendicion"
        r = cliente.solicitud("GET", f"{self.base_v1}/pedidos/{pid}", headers=self._cabecera(), timeout=self.timeout)
        pedido = r.cuerpo if r.ok and r.estado == 200 and isinstance(r.cuerpo, dict) else {}
        desc = "entregado un pedido en efectivo por la repartidora, trae rendicion pendiente con lo que cobró por cuenta del comercio"
        rend = pedido.get("rendicion")
        cobrado = sum(((p.get("monto") or {}).get("centavos") or 0) for p in pedido.get("pagos") or []
                      if p.get("metodo") == "efectivo" and p.get("destinatario") == pedido.get("comercio") and not p.get("pagador"))
        if not isinstance(rend, dict):
            self.casos.append(_fallo(cat, "verPedido", desc, "GET /pedidos/{id} no trae 'rendicion'"))
            return
        if rend.get("estado") != "pendiente" or (rend.get("monto") or {}).get("centavos") != cobrado:
            self.casos.append(_fallo(cat, "verPedido", desc, f"estado {rend.get('estado')!r}, monto {(rend.get('monto') or {}).get('centavos')} y los pagos en efectivo al comercio suman {cobrado}"))
            return
        self.casos.append(_ok(cat, "verPedido", desc))
        monto = rend["monto"]
        ruta = f"{self.base_v1}/pedidos/{pid}/rendicion"
        yo = pedido.get("repartidor")

        ahora = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        falsa = acceso.Clave()
        mala = {"firmante": yo, "clave_publica": falsa.publica, "valor": falsa.firmar({"otra": "cosa"}), "instante": ahora}
        desc = "declararRendicion con una firma que no verifica responde 422 firma_invalida y no agrega constancia"
        r = cliente.solicitud("POST", ruta, headers=self._cabecera(), json_body={"monto": monto, "firma": mala}, timeout=self.timeout)
        codigo = (r.cuerpo or {}).get("codigo") if isinstance(r.cuerpo, dict) else None
        if r.ok and r.estado == 422 and codigo == "firma_invalida":
            self.casos.append(_ok(cat, "declararRendicion", desc))
        else:
            self.casos.append(_fallo(cat, "declararRendicion", desc, f"llegó {r.estado} {codigo or r.motivo}"))
            if r.ok and r.estado == 200:
                return

        firma = None
        if self.clave:
            constancia = {"accion": "rendida", "pedido_id": pid, "actor": yo, "monto": monto, "instante": ahora}
            firma = {"firmante": yo, "clave_publica": self.clave.publica, "valor": self.clave.firmar(constancia), "instante": ahora}
        if not self._constancia(pid, ruta, "declararRendicion", "rendida", yo, monto, firma, "declarada"):
            return
        if not self._constancia(pid, ruta + "/confirmar", "confirmarRendicion", "recibida", pedido.get("comercio"), monto, None, "confirmada"):
            return

        desc = "con la rendición confirmada, otra constancia responde 409 rendicion_confirmada"
        r = cliente.solicitud("POST", ruta, headers=self._cabecera(), json_body={"monto": monto}, timeout=self.timeout)
        codigo = (r.cuerpo or {}).get("codigo") if isinstance(r.cuerpo, dict) else None
        self.casos.append(_ok(cat, "declararRendicion", desc) if r.ok and r.estado == 409 and codigo == "rendicion_confirmada"
                          else _fallo(cat, "declararRendicion", desc, f"llegó {r.estado} {codigo or r.motivo}"))

    def _constancia(self, pid, ruta, opid, accion, actor, monto, firma, estado) -> bool:
        cat = "rendicion"
        r = cliente.solicitud("POST", ruta, headers=self._cabecera(), json_body={"monto": monto, **({"firma": firma} if firma else {})}, timeout=self.timeout)
        codigo = (r.cuerpo or {}).get("codigo") if isinstance(r.cuerpo, dict) else None
        if r.ok and r.estado == 422 and codigo == "firma_requerida":
            self.casos.append(_omitido(cat, opid, f"constancia '{accion}' firmada", "la clave de su actor es de custodia propia y la suite no la tiene"))
            return False
        desc = f"{opid} responde 200 y deja la rendición '{estado}'"
        rend = (r.cuerpo or {}).get("rendicion") if r.ok and r.estado == 200 and isinstance(r.cuerpo, dict) else None
        if not isinstance(rend, dict) or rend.get("estado") != estado:
            self.casos.append(_fallo(cat, opid, desc, f"llegó {r.estado} {codigo or r.motivo or ''}, rendicion.estado={(rend or {}).get('estado')!r}"))
            return False
        caso = self._chequear_esquema(opid, "el pedido con la constancia cumple esquemas/pedido.json", ruta.split("/v1", 1)[1].replace(pid, "{id}"), "post", r.cuerpo)
        if caso:
            self.casos.append(caso)
        self.casos.append(_ok(cat, opid, desc))
        desc = f"la constancia '{accion}' es de {actor} y verifica sobre {{accion, pedido_id, actor, monto, instante}} contra su historial de claves"
        ultima = (rend.get("constancias") or [None])[-1]
        if not isinstance(ultima, dict) or ultima.get("accion") != accion or ultima.get("actor") != actor or ultima.get("monto") != monto:
            self.casos.append(_fallo(cat, opid, desc, f"la última constancia es {ultima!r}"))
            return True
        ok, motivo = NivelA(self.origen, timeout=self.timeout)._verificar_firma(ultima, {})
        self.casos.append(_ok(cat, opid, desc) if ok else _fallo(cat, opid, desc, motivo))
        return True

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
            r_conf = self._confirmar(cid, {}, cabecera=self._cabecera(mandato=True))
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

    # 5. la persona ve qué hizo su agente ---------------------------------------
    def _actividad_mandato(self):
        # Corre después de _mandato_tope, que crea carritos con el mandato: esa
        # escritura tiene que aparecer en la actividad (docs/mandatos.md).
        cat = "mandato"
        opid = "verActividadDeMandato"
        ruta = "/mandatos/{id}/actividad"
        desc = "después de que el agente crea un carrito con el mandato, su actividad lo muestra (crearCarrito sobre un carrito)"
        r_list = cliente.solicitud("GET", f"{self.base_v1}/mandatos", headers=self._cabecera(), timeout=self.timeout)
        activos = [m for m in (r_list.cuerpo if r_list.ok and isinstance(r_list.cuerpo, list) else []) if isinstance(m, dict) and m.get("estado") == "activo"]
        if len(activos) != 1:
            self.casos.append(_omitido(cat, opid, desc, f"GET /mandatos no identificó un único mandato activo (hay {len(activos)})"))
            return
        url = f"{self.base_v1}/mandatos/{activos[0].get('id')}/actividad"

        r = cliente.solicitud("GET", url, headers=self._cabecera(), timeout=self.timeout)
        if not r.ok or r.estado != 200 or not r.cuerpo_es_json:
            self.casos.append(_fallo(cat, opid, desc, r.motivo or f"esperaba 200, llegó {r.estado}"))
        else:
            caso = self._chequear_esquema(opid, "la actividad del mandato cumple PaginaDeActividad", ruta, "get", r.cuerpo)
            if caso:
                self.casos.append(caso)
            entradas = (r.cuerpo or {}).get("actividad") if isinstance(r.cuerpo, dict) else None
            if any(isinstance(e, dict) and e.get("operacion") == "crearCarrito" and (e.get("entidad") or {}).get("tipo") == "carrito" for e in entradas or []):
                self.casos.append(_ok(cat, opid, desc))
            else:
                self.casos.append(_fallo(cat, opid, desc, f"ninguna entrada crearCarrito/carrito entre {len(entradas or [])}"))

        r_ag = cliente.solicitud("GET", url, headers=self._cabecera(mandato=True), timeout=self.timeout)
        desc_ag = "la actividad la lee la persona con su sesión: con el token del mandato responde 403"
        if not r_ag.ok:
            self.casos.append(_fallo(cat, opid, desc_ag, r_ag.motivo))
        elif r_ag.estado in (401, 403):
            self.casos.append(_ok(cat, opid, desc_ag))
        else:
            self.casos.append(_fallo(cat, opid, desc_ag, f"esperaba 403, llegó {r_ag.estado}"))

    # 6. revocación inmediata ------------------------------------------------
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


def _tope_alcanzado(r) -> Optional[dict]:
    """El detalle de un 429 tope_alcanzado (docs/topes.md), o None."""
    if not (r and r.ok and r.estado == 429 and isinstance(r.cuerpo, dict) and r.cuerpo.get("codigo") == "tope_alcanzado"):
        return None
    detalle = r.cuerpo.get("detalle")
    return detalle if isinstance(detalle, dict) else {}


def _espera(r, maximo=65) -> int:
    try:
        espera = int((r.cabeceras or {}).get("Retry-After") or 60)
    except ValueError:
        espera = 60
    return min(max(espera, 1), maximo)


def correr(origen, **kwargs) -> List[Caso]:
    return NivelB(origen, **kwargs).correr()
