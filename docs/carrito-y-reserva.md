# Carrito y reserva

Armar un carrito no retiene nada. El stock y los cupos se reservan al confirmar, y solo mientras el cobro está vigente.

## Por qué no se reserva al armar

La red es sin permiso y los agentes arman carritos con el alcance `armar`, que no gasta. Si agregar al carrito reservara, cualquiera podría dejar a un comercio sin stock sin pagar un peso. Reservar exige haber creado un pedido, que exige el alcance `pedir` y genera un cobro.

## El ciclo

1. **Armado.** Cada `POST /carritos/{id}/items` consulta disponibilidad y responde `valido`, `incompleto` o `no_disponible`. No descuenta stock ni cupos. El carrito vence a las 24 h sin cambios (`vence`); es solo limpieza. Un carrito vencido responde `410 carrito_vencido`.
2. **Confirmación.** `POST /carritos/{id}/confirmar` verifica disponibilidad, reserva y crea el pedido en una sola operación atómica. Si algo se agotó en el medio, responde `409` con `oferta_no_disponible` o `cupo_agotado`, no crea el pedido y deja el carrito en `no_disponible`.
3. **Ventana de pago.** El pedido nace `creado` con un cobro `pendiente` cuyo `vence` es la creación más `ventana_pago_min` del comercio (5 a 60 minutos, 15 por defecto). Mientras tanto el pedido retiene lo reservado.
4. **Pago a tiempo.** `pago.confirmado`, pedido `pagado`. La reserva pasa a ser consumo.
5. **Vencimiento o fallo.** `pago.vencido` o `pago.fallido`; el pedido pasa a `cancelado` con `motivo_codigo` `pago_vencido` o `pago_fallido`; se libera lo reservado y se emite `oferta.stock_cambiado`. El carrito sigue existiendo: se puede confirmar de nuevo si todavía hay disponibilidad.

## Qué se reserva

- Stock `numerico`: las unidades del pedido. La `cantidad` que publica la oferta ya descuenta lo reservado, además de `reserva_mostrador`.
- `cupo_por_dia` de la oferta y cupos de franja de la modalidad: mismo tratamiento.
- Stock `binario`: no hay nada que contar. Si falta al preparar, el comercio lo resuelve con `faltante` o sustitución, como siempre.

## Efectivo

Con `metodo: efectivo` el cobro nace `en_mano`, sin `vence`. La reserva dura hasta que el comercio acepta o rechaza.

## Abierto

- Pedido grupal con N cobros: qué pasa con la reserva si vence el cobro de un participante y no el de los demás.
- Efectivo: no hay plazo para que el comercio acepte o rechace, así que la reserva no tiene fin garantizado.
