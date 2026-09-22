# Sostenimiento del nodo

Un nodo cuesta plata: un servidor, una base de datos, un dominio y los tokens de los agentes que lo
administran. Alguien lo paga. En Vereda se paga como se sostiene un proyecto de código abierto: con
aportes voluntarios de quienes lo usan, a la vista de todos, y sin que nadie quede afuera por no
aportar.

No hay comisión. No hay plata en el medio. Nada de esto pasa por Vereda, porque Vereda no es nadie:
es un protocolo. Cada nodo tiene un operador —una persona, una cooperativa, un club de barrio— y es
ese operador el que pide, recibe y rinde cuentas.

## Principios

1. **Sin comisión.** El nodo no se queda con un porcentaje de ningún pedido, no retiene cobros y no
   cobra entre nodos. El aporte sugerido es un monto fijo, nunca un porcentaje.
2. **Sin plata en el medio.** Lo que va al nodo es una transferencia directa a la cuenta de su
   operador, como cualquier otro cobro de la red (`esquemas/pago.json`). El nodo no custodia ni
   descuenta nada de lo que le pagan al comercio o al repartidor.
3. **Voluntario y sin castigo.** Aportar o no aportar no cambia el ranking, la reputación, la
   visibilidad, los plazos, el acceso a la API ni ninguna otra cosa. Un comercio con `modo: ninguno`
   opera exactamente igual que uno que aporta. Tampoco hay premio: no existe un sello de
   "aportante".
4. **Transparente.** El nodo publica a qué cuenta se aporta, cuánto sugiere, cuánto recibió y en qué
   lo gastó, mes por mes.
5. **Sin gatekeeper.** Nadie aprueba el aporte de nadie, ni se lo pide a un comercio para darlo de
   alta. El comercio elige solo, en su ficha, y lo cambia cuando quiere.

## Quién paga qué

| Quién | Qué | Cuándo | Cómo | Dónde se ve |
| --- | --- | --- | --- | --- |
| Comercio | `aporte_nodo` por pedido | Un monto fijo por cada pedido entregado | Transferencia a `sostenimiento.cuenta`, aparte del pedido | Línea "Para el nodo" del reparto; `GET /comercios/{id}/aporte` |
| Comercio | `aporte_nodo` mensual | Un monto fijo por mes | Transferencia a `sostenimiento.cuenta` | `GET /comercios/{id}/aporte` |
| Comprador | `propina_nodo` | Opcional, al confirmar el carrito o después de la entrega | Solo transferencia a `sostenimiento.cuenta`, aunque el pedido sea en efectivo | Línea "Para el nodo" del reparto y `totales.propina_nodo` |
| Repartidor | Nada | — | — | — |

- **El comercio elige** en `aporte_nodo` de su ficha (`esquemas/comercio.json`): `ninguno` (el
  default), `por_pedido` o `mensual`, y el monto. El nodo publica un `monto_sugerido_por_pedido` y un
  `monto_sugerido_mensual`, pero son sugerencias: el comercio pone lo que quiere. Se configura con
  `PUT /comercios/{id}/aporte` o la herramienta MCP `aporte_configurar`.
- **Por pedido**, el monto vigente se congela en el reparto al crear el pedido, como los precios. Al
  pasar el pedido a `entregado`, el nodo genera un pago `aporte_nodo` pendiente, con `pagador` el
  comercio, `destinatario` el nodo e instrucciones de transferencia. Un pedido cancelado no genera
  aporte.
- **Mensual**, el nodo genera al empezar cada mes un pago `aporte_nodo` pendiente con `periodo`
  (`AAAA-MM`) y sin pedido.
- **La propina del comprador** se pide solo si el nodo publica `acepta_propinas_de_usuarios`. Nunca
  viene sugerida ni preseleccionada: la app y los agentes la ofrecen solo si la persona la busca. Un
  nodo que no acepta propinas responde `422 propina_nodo_no_aceptada`.
- **El repartidor no aporta.** Su envío y sus propinas son enteros suyos.

## El reparto: "Para el nodo"

Cada pedido trae su `reparto` calculado por el nodo (`esquemas/pedido.json`). Las apps lo muestran
agrupado en tres líneas —para el comercio, para el repartidor y **Para el nodo**— y la del nodo
está siempre, aunque sea 0. Que se vea el 0 es el punto: el nodo no se queda con nada que no esté
escrito ahí.

- `aporte_nodo` lleva `pagador: comercio`. Sale de lo que cobra el comercio: no se suma a lo que paga
  el comprador, que ve cuánto de lo suyo el comercio eligió pasarle al nodo.
- `propina_nodo` lleva `pagador: comprador` (el default) y sí se suma al total.
- La línea se llama "Para el nodo", nunca "Para Vereda" ni "comisión".

## Cobro sin intermediario

Todo lo que va al nodo es un pago de `esquemas/pago.json` con `metodo: transferencia` y `destinatario`
la identidad `nodo@<dominio>` del nodo. La cuenta es `sostenimiento.cuenta`, que a diferencia de la
de un comercio o un repartidor es pública a propósito: es la de quien pide aportes a la vista de
todos, y cualquiera comprueba que el titular que le muestra su banco es el publicado.

- Quien paga declara la transferencia: el comprador con `POST /pedidos/{id}/transferencia` y
  `concepto: propina_nodo`; el comercio con `POST /comercios/{id}/aporte/transferencia`.
- Solo el operador del nodo la confirma, al ver la plata en su cuenta, con sus propias herramientas.
  Es el único que puede: es el único que ve la cuenta.
- Un aporte o una propina sin pagar vence a los 30 días y queda `vencido`. Nunca retiene stock,
  nunca cancela un pedido, nunca genera una deuda que se cobre de otra forma.

## Transparencia: lo que el nodo publica

`GET /sostenimiento`, sin token y con caché, y el mismo bloque en `sostenimiento` de
`/.well-known/vereda.json` (`esquemas/sostenimiento.json`):

- `cuenta` (alias y titular), `monto_sugerido_por_pedido`, `monto_sugerido_mensual`,
  `acepta_propinas_de_usuarios`, `quien_paga`.
- `gastos_publicados`, un período por mes: pedidos entregados, cuántos comercios aportaron, aportes
  y propinas recibidos, y gastos en servidor, tokens y otros, con una nota libre del operador.
- Lo recibido son **conteos automáticos** de pagos confirmados; lo gastado lo carga el operador. Un
  nodo que gasta menos de lo que recibe lo dice en la nota, y qué hace con la diferencia también.

La ficha de cada comercio dice lo que el comercio **declaró** (`aporte_nodo`). Si después transfirió
o no, el nodo no lo publica comercio por comercio: solo el total y cuántos aportaron.

## Lo que un nodo NO puede hacer con esto

- Cobrar un porcentaje de los pedidos, retener parte de un cobro o descontar el aporte de lo que le
  pagan al comercio.
- Hacer del aporte una condición para darse de alta, operar, aparecer en la búsqueda, usar una
  modalidad o acceder a la API.
- Ordenar, destacar, bajar o filtrar por aporte. El ranking y la reputación
  (`docs/ranking-y-despacho.md`, `docs/resenas.md`) no leen `aporte_nodo` ni los pagos al nodo.
- Publicar quién aportó y quién no, o marcar a un comercio por no aportar.
- Sugerir o preseleccionar la propina del comprador, o cobrarla en efectivo o por un PSP.
- Cobrarle al repartidor, o cobrar entre nodos (`docs/federacion.md`).
- Llamar a la línea "Para Vereda": el operador es el que recibe y el que rinde cuentas.

Todo esto es verificable desde afuera: el reparto de cada pedido, la ficha de cada comercio y los
gastos publicados son públicos, y el orden de la búsqueda se puede recalcular con la fórmula.
