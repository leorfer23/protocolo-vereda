# Promociones y puntos

Las promociones son del comercio, son públicas (`GET /comercios/{id}/promociones`, sin token) y se calculan con el algoritmo de esta página. Cualquier app o agente tiene que llegar al mismo monto que el nodo. No mueven el ranking: `p` en `docs/ranking-y-despacho.md` es el precio de lista.

## Qué se puede expresar

| Lo que dice el cartel | Tipo | Cómo |
| --- | --- | --- |
| 2x1 | `lleva_n` | `cada: 2`, `descuento_pct: 100` |
| 3x2 | `lleva_n` | `cada: 3`, `descuento_pct: 100` |
| Segunda unidad al 70 % | `lleva_n` | `cada: 2`, `descuento_pct: 70` |
| 3x2 combinando sabores | `lleva_n` | `mezclable: true` |
| Llevando 6, 10 % menos; llevando 12, $1.600 cada una | `escala_cantidad` | un tramo por escalón |
| 10 % desde $30.000, 15 % desde $60.000 | `escala_canasta` | un tramo por escalón |
| Envío gratis desde $30.000 | `escala_canasta` | `sobre: envio`, 100 % |
| 10 % en efectivo, 5 % retirando, martes de verdulería | `descuento` | con `condiciones` |
| Puntos por volver | `comercio.fidelidad` | ver abajo |

Todo lo comercial lo decide el comercio: qué promociones publica, si se acumulan, contra qué total mide la escalera, cuánto vale un punto y cuánto se puede pagar con puntos. Lo único fijo es el algoritmo, para que todos lleguen a la misma cuenta.

`condiciones` acota cualquiera: vigencia, días, modalidades, medios de cobro, primera compra (con requisitos opcionales para que una identidad nueva no alcance: contacto confirmado, pedidos entregados en la red), máximo de unidades, tope de descuento.

## El algoritmo

Se corre al armar el carrito (para mostrar) y al confirmar (para congelar).

1. **Candidatas.** Promociones `activa` del comercio cuyas `condiciones` se cumplen en ese instante, en la hora del comercio, con la modalidad y el medio de cobro elegidos. Una de `primera_compra` con `primera_compra_requisitos` además pide que la persona los cumpla en ese instante, según su verificación pública (`docs/topes.md`).
2. **Por ítem.** Para cada ítem dentro del `alcance`:
   - `lleva_n`: solo ofertas que se piden en unidades enteras. Se ordenan las unidades de mayor a menor precio, se arman grupos de `cada`, y en cada grupo completo la más barata lleva el descuento. Con `mezclable`, el grupo junta unidades de todos los ítems del alcance.
   - `escala_cantidad`: vale el tramo más alto con `desde` menor o igual a la cantidad, para todas las unidades.
   - `descuento`: porcentaje o monto por unidad, nunca por debajo de cero.
   - Se descuenta sobre `precio_unitario`; los extras de opciones no se descuentan.
   - Entre las no acumulables gana la que más descuenta; si empatan, la de `id` menor. Después se aplican las `acumulable`, en orden de `id`, sobre el precio ya descontado.
3. **Por canasta.** Sobre el total de productos de los ítems del `alcance`. El comercio elige en `base` contra qué se miden los tramos: `descontado` (por defecto), el total tras el paso 2; o `lista`, a precio de lista. El porcentaje se aplica siempre sobre el total ya descontado. Gana el tramo más alto alcanzado. Se elige por separado la mejor sobre `productos` y la mejor sobre `envio`.
4. **Puntos.** El canje va último. No baja de cero, no toca envío ni propinas y no supera `fidelidad.canje_maximo_pct` del total de productos.
5. **Redondeo.** Cada descuento se redondea hacia abajo al centavo.
6. **Topes.** `maximo_unidades` y `tope_descuento` recortan el resultado de su promoción.

Al confirmar, el resultado queda en `descuentos_aplicados` y `totales.descuentos`, congelado igual que los precios. Si pesables, faltantes o sustituciones cambian las cantidades, el nodo recalcula con las mismas promociones sobre las cantidades finales y el resultado va a `total_final`; un faltante puede hacer perder un tramo.

Los topes de un mandato se comparan contra el total ya descontado. En una suscripción, cada ocurrencia se calcula con las promociones vigentes cuando se genera su pedido.

## Ejemplo

Tres gaseosas de $1.950, dos yerbas de $5.400 y un aceite de $16.000. Promociones: 3x2 en gaseosas y 10 % desde $30.000. La persona canjea 50 puntos de $10.

| Paso | Cuenta | Queda |
| --- | --- | --- |
| Lista | 3 × 1.950 + 2 × 5.400 + 16.000 | $32.650 |
| 3x2 en gaseosas | la tercera gratis: −$1.950 | $30.700 |
| 10 % desde $30.000 | sobre $30.700: −$3.070 | $27.630 |
| Canje de 50 puntos | −$500 | $27.130 |

`totales.descuentos` es $5.520. Con un punto cada $1.000, al entregarse gana 27 puntos.

El orden importa: con `base: descontado`, el tramo de canasta se mide después del 3x2. Con $32.650 de lista alcanza igual, pero con una yerba menos ($27.250 de lista, $25.300 tras el 3x2) no llegaría.

## Puntos

- Los define el comercio en `fidelidad`: cuánto hay que gastar por punto y cuánto vale cada punto. Valen solo en ese comercio.
- Se ganan al pasar el pedido a `entregado`, sobre lo pagado en productos, redondeando hacia abajo. Un pedido cancelado devuelve los canjeados.
- El saldo lo lleva el nodo del comercio. `GET /yo/puntos` devuelve cada saldo firmado por su comercio; el usuario guarda el último como comprobante.
- Si vencen, vencen primero los más viejos.
- Un agente canjea con alcance `armar`, pero debería preguntar antes: la persona puede preferir juntarlos.

## Lo que el protocolo no hace

No hay cupones de la red, ni promociones pagadas por la red, ni posiciones destacadas para quien hace promociones. Un descuento es una decisión de precio del comercio, y se ve.
