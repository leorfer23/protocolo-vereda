# Eventos y webhooks

Todo cambio de estado se publica como un evento (`esquemas/evento.json`), idempotente por `id`, con secuencia monótona por entidad y firmado por el nodo.

## Canales

| Canal | Para quién | Cómo |
| --- | --- | --- |
| SSE `GET /eventos?desde=<id>` | Apps y agentes conectados | Stream; reconectar con el último id visto |
| Webhook `POST /webhooks` | Agentes, PSP, sistemas del comercio | HTTP POST firmado; reintentos exponenciales durante 24 h; el receptor responde 2xx |
| Federación `POST /federacion/entrantes` | Otros nodos | Firma HTTP del nodo emisor; en orden por entidad; mismos reintentos que el webhook. Ver `docs/federacion.md` |

## Firma del webhook

Cabecera `Vereda-Firma: ed25519=<base64url>` sobre el cuerpo crudo, con la clave pública del nodo publicada en `.well-known/vereda.json`. El receptor verifica antes de procesar. Un secreto compartido opcional (`secreto` al registrar) va en `Vereda-Secreto` como segunda capa.

## Tipos

| Tipo | Cuándo |
| --- | --- |
| `pedido.creado`, `pedido.pagado`, `pedido.aceptado`, `pedido.rechazado`, `pedido.preparando`, `pedido.listo`, `pedido.asignado`, `pedido.en_camino`, `pedido.entregado`, `pedido.cancelado` | Transiciones del pedido |
| `item.confirmado`, `item.sustitucion_propuesta`, `item.sustitucion_respondida`, `item.faltante`, `item.pesado` | Ítem por ítem, en preparación |
| `pago.pendiente`, `pago.confirmado`, `pago.vencido`, `pago.fallido` | Desde el adaptador de PSP |
| `pago.transferencia_declarada` | El comprador avisa que ya transfirió (`POST /pedidos/{id}/transferencia`), en transferencia directa sin PSP |
| `viaje.ofrecido`, `viaje.aceptado`, `viaje.rechazado`, `viaje.soltado`, `viaje.parada_completada`, `viaje.completado` | Despacho. `viaje.soltado`: el repartidor dejó un viaje ya aceptado y vuelve a asignarse |
| `pedido.sin_repartidor`, `pedido.pasa_a_retiro` | Asignación (`docs/repartidores.md`): se cumplió `plazo_asignacion_min` sin repartidor y el comercio eligió `avisar` o `retiro` |
| `suscripcion.ocurrencia_abierta`, `suscripcion.ocurrencia_generada`, `suscripcion.pausada`, `suscripcion.cancelada`, `suscripcion.precio_cambia` | Suscripciones |
| `ronda.abierta`, `ronda.cerrada`, `ronda.en_camino`, `ronda.entregada` | Rondas |
| `grupo.participante_unido`, `grupo.cerrado`, `grupo.pedido_generado`, `grupo.participante_no_pago` | Pedidos grupales |
| `cotizacion.solicitada`, `cotizacion.presupuestada`, `cotizacion.aceptada`, `cotizacion.vencida` | Cotizaciones |
| `mensaje.nuevo` | Chat |
| `mandato.otorgado`, `mandato.revocado`, `mandato.requiere_confirmacion`, `mandato.confirmado` | Agentes |
| `oferta.stock_cambiado`, `oferta.precio_cambiado`, `comercio.abierto`, `comercio.cerrado` | Catálogo (público) |
| `vinculacion.verificada`, `vinculacion.caida`, `vinculacion.vencida` | Una vinculación cambió de estado al comprobarse (`docs/identidad-y-verificacion.md`). Público |
| `atestacion.recibida` | Alguien atestiguó sobre el actor. En `cliente_frecuente` es el aviso para que la persona acepte o rechace |
| `denuncia.recibida`, `denuncia.respondida`, `denuncia.estado_cambiado` | Denuncias de suplantación. Públicos: la denuncia ya lo es |
| `clave.rotada`, `clave.comprometida` | Claves de un actor o del nodo (público). Quien tenga la clave en caché la vuelve a pedir |

## Idempotencia

Toda operación que crea algo lleva `Idempotency-Key`. El mismo key con el mismo cuerpo devuelve la misma respuesta; con otro cuerpo, 409. Los eventos se deduplican por `id` en el receptor.
