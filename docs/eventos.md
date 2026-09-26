# Eventos y webhooks

Todo cambio de estado se publica como un evento (`esquemas/evento.json`), idempotente por `id`, con secuencia monótona por entidad y firmado por el nodo.

## Canales

| Canal | Para quién | Cómo |
| --- | --- | --- |
| SSE `GET /eventos?desde=<id>` | Apps y agentes conectados | Stream; reconectar con el último id visto |
| Webhook `POST /webhooks` | Agentes, PSP, sistemas del comercio | HTTP POST firmado; reintentos exponenciales durante 24 h; el receptor responde 2xx |
| Push (APNs, FCM) | El teléfono de la persona, con la app cerrada | Opcional. Solo un aviso sin datos personales para algunos eventos; lo que pasó se lee en la API. Ver `docs/notificaciones-push.md` |
| Federación `POST /federacion/entrantes` | Otros nodos | Firma HTTP del nodo emisor; en orden por entidad; mismos reintentos que el webhook. Ver `docs/federacion.md` |

## Quién recibe cada evento por SSE

`GET /eventos` le manda a cada actor solo lo que puede ver:

- Los eventos públicos del nodo (catálogo, claves, vinculaciones, denuncias).
- Los de las entidades de las que es parte: el comprador, el comercio y el repartidor de un pedido o un viaje; el otorgante de un mandato; los participantes de un grupo o una ronda; los del chat.
- **Todo lo que ve un comercio lo ve también quien lo administra.** La identidad del comercio y la persona que lo administra (la sesión que lo dio de alta, o quien quedó como dueña tras un reclamo resuelto) son actores distintos; la bandeja del local se abre con la sesión de la persona. Si la ficha cambia de dueño, la nueva lo ve desde ese momento y la anterior deja de verlo. Un miembro del equipo con `pedidos` ve los de los pedidos y cotizaciones del comercio, y nada más de él (`docs/equipo.md`). Un agente que escucha con un mandato de esa persona (scope `leer`) ve lo mismo que ella.

Nadie más: un actor ajeno a un pedido no recibe sus eventos.

## Firma del webhook

Cabecera `Vereda-Firma: ed25519=<base64url>` sobre el cuerpo crudo, con la clave pública del nodo publicada en `.well-known/vereda.json`. El receptor verifica antes de procesar. Un secreto compartido opcional (`secreto` al registrar) va en `Vereda-Secreto` como segunda capa.

## Tipos

| Tipo | Cuándo |
| --- | --- |
| `pedido.creado`, `pedido.pagado`, `pedido.aceptado`, `pedido.rechazado`, `pedido.preparando`, `pedido.listo`, `pedido.asignado`, `pedido.en_camino`, `pedido.entregado`, `pedido.cancelado` | Transiciones del pedido. `pedido.preparando` sale con el primer ítem que resuelve el comercio en un pedido `aceptado` (`resolverItemPedido`), junto con su `item.*` |
| `item.confirmado`, `item.sustitucion_propuesta`, `item.sustitucion_respondida`, `item.faltante`, `item.pesado` | Ítem por ítem, en preparación |
| `pago.pendiente`, `pago.confirmado`, `pago.vencido`, `pago.fallido` | Desde el adaptador de PSP (siempre después de re-consultar al proveedor) o al confirmar transferencia/efectivo. `pago.confirmado` de tarjeta lleva `confirmado_por: psp`. Una devolución rechazada por el proveedor también sale como `pago.fallido`, con la devolución en `datos.pago` |
| `pago.reembolsado` | El proveedor confirmó una devolución, pedida con `reembolsarPago` o hecha por el comercio directo en su proveedor. `datos.pago` es la devolución (`concepto: devolucion`, `reembolsa` el cobro original) (`docs/cobro-con-psp.md`) |
| `pago.contracargo` | Informativo: el proveedor avisó un contracargo. No cambia ningún estado ni mueve plata en el nodo |
| `comercio.cobrador_cambiado` | Uno de los proveedores de pago del comercio (tiene uno por `psp`, varios a la vez) cambió de estado: `datos.psp` siempre, y `datos.cobrador` con su `estado` (`conectado`, `vencido`, `revocado`, `credenciales_rechazadas`), o sin `datos.cobrador` si se desconectó. Solo al comercio y a quien lo administra con permiso `datos`; nunca trae credenciales ni tokens |
| `pago.transferencia_declarada` | El comprador avisa que ya transfirió (`POST /pedidos/{id}/transferencia`), en transferencia directa sin PSP |
| `viaje.ofrecido`, `viaje.aceptado`, `viaje.rechazado`, `viaje.soltado`, `viaje.parada_completada`, `viaje.completado` | Despacho. `viaje.soltado`: el repartidor dejó un viaje ya aceptado y vuelve a asignarse. `viaje.ofrecido`: a cada repartidor al que se le ofrece le llega aparte, con el viaje entero en `datos.viaje`, como lo ve en `GET /viajes/ofrecidos` (monto, distancia, peso, paradas y quién le paga cada envío y cómo, `docs/repartidores.md`, punto d); las partes de los pedidos reciben el aviso sin `datos.viaje`, porque un viaje puede llevar direcciones de otros compradores |
| `pedido.descargo` | El comprador dejó su versión de un "no vino" (`dejarDescargo`), con el pedido y su `no_vino.descargo`. Al comercio y al repartidor del pedido. El cierre por "no vino" en sí sale como `pedido.cancelado`, con `motivo_codigo` `no_retirado` o `no_recibido` y `no_vino` (`docs/carrito-y-reserva.md`) |
| `rendicion.declarada`, `rendicion.confirmada`, `rendicion.en_desacuerdo` | Rendición del efectivo al comercio (`docs/repartidores.md`, punto l): el repartidor declaró cuánto le dio, el comercio confirmó el mismo monto o dijo otro. Solo al comercio y al repartidor del pedido, con `entidad` el pedido y la rendición entera en `datos.rendicion` |
| `pedido.sin_repartidor`, `pedido.pasa_a_retiro` | Asignación (`docs/repartidores.md`): se cumplió `plazo_asignacion_min` sin repartidor y el comercio eligió `avisar` o `retiro` |
| `suscripcion.ocurrencia_abierta`, `suscripcion.ocurrencia_generada`, `suscripcion.pausada`, `suscripcion.cancelada`, `suscripcion.precio_cambia` | Suscripciones |
| `ronda.abierta`, `ronda.cerrada`, `ronda.en_camino`, `ronda.entregada` | Rondas |
| `grupo.participante_unido`, `grupo.cerrado`, `grupo.pedido_generado`, `grupo.participante_no_pago` | Pedidos grupales |
| `cotizacion.solicitada`, `cotizacion.presupuestada`, `cotizacion.aceptada`, `cotizacion.vencida` | Cotizaciones |
| `mensaje.nuevo` | Chat |
| `mandato.otorgado`, `mandato.revocado`, `mandato.requiere_confirmacion`, `mandato.confirmado` | Agentes. `mandato.otorgado` le llega también al otorgante en todas sus sesiones: si no lo dio él, lo ve |
| `sesion.abierta` | Se abrió una sesión de la persona (`docs/acceso.md`, punto 6), con `datos: {id, etiqueta?, forma}`. Solo a ella, nunca a un agente ni a otro actor |
| `oferta.stock_cambiado`, `oferta.precio_cambiado` | Catálogo (público) |
| `comercio.abierto`, `comercio.cerrado` | Cambió `abierto_ahora` del comercio: empezó o terminó una franja de `horarios`, o el comercio lo pisó con `apertura_manual` (público) |
| `vinculacion.verificada`, `vinculacion.caida`, `vinculacion.vencida` | Una vinculación cambió de estado al comprobarse (`docs/identidad-y-verificacion.md`). Público |
| `atestacion.recibida` | Alguien atestiguó sobre el actor. En `cliente_frecuente` es el aviso para que la persona acepte o rechace |
| `denuncia.recibida`, `denuncia.respondida`, `denuncia.estado_cambiado` | Denuncias de suplantación. Públicos: la denuncia ya lo es |
| `reclamo.recibido`, `reclamo.resuelto`, `reclamo.contradicho`, `reclamo.vencido` | Reclamos de propiedad de una ficha. `reclamo.resuelto` es el cambio de dueño |
| `clave.rotada`, `clave.comprometida` | Claves de un actor o del nodo (público). Quien tenga la clave en caché la vuelve a pedir |

## Idempotencia

Toda operación que crea algo lleva `Idempotency-Key`. El mismo key con el mismo cuerpo devuelve la misma respuesta; con otro cuerpo, 409. Los eventos se deduplican por `id` en el receptor.
