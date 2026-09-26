# Carrito y reserva

Armar un carrito no retiene nada. El stock y los cupos se reservan al confirmar, y solo mientras el cobro está vigente.

## Por qué no se reserva al armar

La red es sin permiso y los agentes arman carritos con el alcance `armar`, que no gasta. Si agregar al carrito reservara, cualquiera podría dejar a un comercio sin stock sin pagar un peso. Reservar exige haber creado un pedido, que exige el alcance `pedir` y genera un cobro.

## El ciclo

1. **Armado.** Cada `POST /carritos/{id}/items` consulta disponibilidad y responde `valido`, `incompleto` o `no_disponible`. No descuenta stock ni cupos. El carrito vence a las 24 h sin cambios (`vence`); es solo limpieza. Un carrito vencido responde `410 carrito_vencido`.
2. **Confirmación.** `POST /carritos/{id}/confirmar` verifica disponibilidad, reserva y crea el pedido en una sola operación atómica. Si algo se agotó en el medio, responde `409` con `oferta_no_disponible` o `cupo_agotado`, no crea el pedido y deja el carrito en `no_disponible`. Con el comercio cerrado tampoco hay pedido: `409 comercio_cerrado`. Sin `programado_para` manda `abierto_ahora` (su `apertura_manual` vigente o, si no, sus `horarios`); un pedido programado se toma si los `horarios` cubren `programado_para`. El carrito no cambia y se puede confirmar cuando abra.
3. **Consentimiento de datos.** Si el comercio declara `datos.lista_de_clientes: true` en su ficha, el cuerpo de la confirmación lleva `acepta_lista_de_clientes`. En `true`, el comercio puede guardar nombre y contacto de la persona más allá del pedido; ausente o en `false`, el nodo no se los entrega pasado el pedido activo. Se pregunta una sola vez por comercio y no condiciona el pedido: decir que no lo confirma igual.
4. **Ventana de pago.** El pedido nace `creado` con un cobro `pendiente` cuyo `vence` es la creación más `ventana_pago_min` del comercio (5 a 60 minutos, 15 por defecto). Mientras tanto el pedido retiene lo reservado.
5. **Pago a tiempo.** `pago.confirmado`, pedido `pagado`. La reserva pasa a ser consumo.
6. **Vencimiento o fallo.** `pago.vencido` o `pago.fallido`; el pedido pasa a `cancelado` con `motivo_codigo` `pago_vencido` o `pago_fallido`; se libera lo reservado y se emite `oferta.stock_cambiado`. El carrito sigue existiendo: se puede confirmar de nuevo si todavía hay disponibilidad.

## Qué se reserva

- Stock `numerico`: las unidades del pedido. La `cantidad` que publica la oferta ya descuenta lo reservado, además de `reserva_mostrador`.
- `cupo_por_dia` de la oferta y cupos de franja de la modalidad: mismo tratamiento.
- Stock `binario`: no hay nada que contar. Si falta al preparar, el comercio lo resuelve con `faltante` o sustitución, como siempre.

## Elegir cómo pagar

El comercio publica qué medios acepta en `medios_cobro`. Si acepta más de uno, el comprador elige al confirmar con `metodo_pago` (`efectivo` o `transferencia`).

- Sin `metodo_pago` elige el comercio: el primero que acepta para esa modalidad, con el efectivo adelante cuando está, porque es el que no necesita a nadie más.
- Un medio que el comercio no acepta es `422` y no crea el pedido: `efectivo_no_disponible` si pidió efectivo, `medio_no_disponible` si pidió otro. Los dos traen `detalle.medios_cobro`, los que sí acepta, para que la persona elija de nuevo.
- Elegir efectivo no saltea las condiciones del comercio (abajo): si no las cumple, también es `422 efectivo_no_disponible`.
- `metodo_envio` es otra cosa: cómo se le paga el envío al repartidor cuando va directo a él (`docs/repartidores.md`).

## Efectivo

El efectivo no pasa por ningún PSP: se cobra en mano. Es un medio de cobro de primera clase, y el comercio decide cómo lo acepta.

- El cobro nace `en_mano`, sin `vence`. El pedido va de `creado` a `aceptado` sin pasar por `pagado`.
- Como reserva sin haber pagado, la reserva se acota por el otro lado: el comercio tiene `plazo_aceptacion_min` (1 a 60 minutos con el comercio abierto, 10 por defecto) para aceptar o rechazar. Si no responde, el pedido se cancela con `sin_respuesta_del_comercio` y se libera todo. Ese plazo vale para cualquier pedido, no solo en efectivo.
- El comercio se defiende de pedidos falsos con `efectivo.pedidos_entregados_minimo` (historial que le exige al usuario), `efectivo.modalidades` (por ejemplo, efectivo solo en retiro) y `efectivo.monto_maximo`. Si el usuario no cumple, confirmar responde `efectivo_no_disponible` y puede elegir otro medio.
- Al entregar, quien entrega envía `cobrado_en_mano: true`: el pago pasa a `confirmado` y el pedido a `entregado`.
- **¿Con cuánto pagás?** Al confirmar, el comprador puede decir con qué billete paga (`paga_con_centavos`). Queda en el pago como `paga_con` y lo ven el comercio y el repartidor (también en el viaje, `por_pedido[].paga_con`), para llevar cambio. No es obligatorio; si es menor que lo que paga en mano, `422 paga_con_insuficiente`.
- Con repartidor, el efectivo lo cobra el repartidor. `reparto` dice cuánto es del comercio y cuánto del envío; cómo se lo rinden entre ellos es asunto de ellos. La red lo muestra y no lo ejecuta, igual que con las devoluciones.
- Una propina al nodo (`propina_nodo_centavos`) nunca va en efectivo: es una transferencia aparte a la cuenta del nodo, y si no se hace no pasa nada (`docs/sostenimiento.md`).

## Transferencia directa

Vereda nunca maneja plata: con `metodo: transferencia` la plata va del comprador directo a la cuenta del comercio, sin PSP en el medio.

- El comercio carga su alias en `PATCH /comercios/{id}`, campo `privado.cuenta_cobro.alias` (y `titular` opcional). Vive en `privado`: nunca sale en la ficha pública ni se federa.
- Al confirmar el carrito, el cobro nace `pendiente` con su `vence` (`ventana_pago_min` del comercio) y con `instrucciones`: alias, titular, monto y una referencia corta para el concepto. Las instrucciones las ve únicamente el comprador, y solo mientras el pedido está activo.
- **Centavos únicos.** `instrucciones.monto` es lo que hay que transferir, y el nodo lo hace único entre los cobros `pendiente` por transferencia del mismo destinatario: si otro pendiente ya pide el mismo monto, descuenta los centavos libres más chicos (1 a 99) y lo anota en `instrucciones.ajuste_centavos` (siempre 0 o negativo: nunca se cobra de más). Así la transferencia se reconoce sola por el monto, sin depender del concepto que escriba la persona en su banco. Los centavos los absorbe el destinatario; al confirmarse o vencer el cobro, ese monto queda libre otra vez. Si no queda ninguno libre, el nodo no ajusta y el comercio distingue por `referencia`. Es el default del protocolo; el comercio lo apaga con `privado.cuenta_cobro.centavos_unicos: false`. Si la persona transfiere el monto redondo igual, el comercio confirma como siempre: la diferencia es suya.
- El comprador transfiere por fuera de Vereda y avisa con `POST /pedidos/{id}/transferencia`, con un `comprobante` opcional. Esto no confirma el cobro: el nodo no vio ninguna plata y no dice que sí. Publica `pago.transferencia_declarada`.
- El comercio confirma cuando ve la plata con `POST /pedidos/{id}/transferencia/confirmar`. Ahí el cobro pasa a `confirmado` y el pedido a `pagado`. Es el único que puede: es el único que ve su cuenta.
- Si nadie confirma antes del `vence`, se aplica igual que cualquier otro pago pendiente: `vencido`, pedido `cancelado` con `pago_vencido`, se libera lo reservado.
- El envío al repartidor usa los mismos dos pasos con `concepto: envio`: avisa quien pagó y confirma el repartidor, que es quien ve su cuenta. Quién le paga, cuándo vence y por qué no cancela el pedido está en `docs/repartidores.md`.

## Retiro por el usuario

- Con modalidad `retiro` no hay viaje ni repartidor: de `listo` el pedido pasa a `entregado`.
- El pedido lleva un `codigo_retiro` que ve solo el usuario. Al pasar a buscar se lo dice al comercio, que lo envía en `entregar` y firma la entrega. Sin código válido no hay `entregado`, y sin `entregado` no hay reseña.
- Retiro con efectivo es pagar en el mostrador: el comercio envía el código y `cobrado_en_mano` en la misma llamada.
- Si nadie pasa a buscar, el comercio cancela con `no_retirado` según su política de cancelación publicada.

## Pedido grupal

- Al cerrar el grupo se reserva todo y nace un cobro por participante, todos con el mismo `vence`.
- Si vence el cobro de un participante, pasa a `no_pago`, se libera su reserva y se emite `grupo.participante_no_pago`. Qué pasa después lo decide el comercio en `grupal.si_falta_un_pago`: con `sigue` (por defecto) salen sus ítems y el pedido continúa con los demás; con `cancela` se cancela todo con `pago_vencido`.
- Lo que ya pagaron los otros no cambia. Si la división del envío dejó una parte sin cubrir, `totales.envio` baja en esa parte; el comercio lo ve antes de aceptar y el repartidor ve el monto antes de tomar el viaje.
- Si no paga nadie, el pedido se cancela con `pago_vencido`.
