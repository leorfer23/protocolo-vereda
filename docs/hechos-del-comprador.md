# Hechos del comprador

Salvaguarda S4 de `docs/antifraude.md`. Quien arriesga su mercadería decide con información, sin que
Vereda decida por él: cuando entra un pedido, el comercio ve **hechos** de quien compra ("cuenta de
hace 3 días · primer pedido acá · 0 entregados", "41 entregados · 2 años", "1 sin retirar"). Nunca un
puntaje, un color ni un "riesgo". Quien mira saca su conclusión.

Esquema: `esquemas/usuario.json#/$defs/hechos`. En el pedido: `partes.usuario.hechos`. El comprador:
`GET /yo/hechos` (`verMisHechos`, MCP `mis_hechos`).

## Quién los ve

- **El comercio del pedido**: la dueña, un miembro de su equipo con permiso `pedidos` y un agente
  con mandato `administrar`. En cada pedido suyo, activo o terminado.
- **El comprador**: los suyos, en `GET /yo/hechos` y en `partes.usuario.hechos` de sus pedidos. Ve
  exactamente lo mismo que el comercio: nada se calcula a sus espaldas.
- **Nadie más.** No están en la ficha pública de la persona ni en `verificacion`, y el repartidor no
  los ve. No hay forma de pedir los de otra persona sin un pedido de por medio.

## Las reglas

Todo cuenta pedidos de la identidad como `usuario` en **este nodo**. Un pedido cuenta una sola vez,
cuando se cierra (`entregado` o `cancelado`); uno abierto todavía no cuenta en nada, tampoco el pedido
que se está mirando.

| Campo | Qué cuenta |
|---|---|
| `alta` | El día que la identidad entró al nodo (`verificacion.historial.alta`). |
| `antiguedad_dias` | Días de calendario entre `alta` y hoy, con el reloj del nodo (el mismo de `alta`): una cuenta de anoche a las 23:50 tiene un día a las 00:10. Se calcula al leer. |
| `entregados` | Pedidos en `entregado`, con cualquier comercio. Igual a `verificacion.historial.pedidos_entregados`. |
| `no_retirado` | Pedidos cerrados con `motivo_codigo: no_retirado` (`docs/carrito-y-reserva.md`, "No vino"). |
| `no_recibido` | Pedidos cerrados con `motivo_codigo: no_recibido`. |
| `descargos` | De esos dos, en cuántos el comprador dejó su versión firmada (`no_vino.descargo`). Quedan las dos: nadie arbitra. |
| `cancelados_despues_de_aceptar` | Pedidos cerrados con `motivo_codigo: cancelado_por_usuario` cuyo `historial` tiene un `aceptado` antes de la cancelación. Cancelar antes de que el comercio acepte no cuenta: arrepentirse a tiempo no le hace daño a nadie. |
| `transferencias_revertidas` | Pedidos con un cobro por transferencia en estado `revertido` (S2). Mientras el nodo no tenga `revertido`, no lo manda. |
| `contacto_confirmado` | Si la persona confirmó un teléfono o un email por desafío (`POST /yo/contacto`). Nunca cuál. |

Solo en un pedido, porque hablan de ese pedido y de ese comercio:

| Campo | Qué dice |
|---|---|
| `entregados_con_el_comercio` | De `entregados`, los que fueron con el comercio de este pedido. |
| `primer_pedido_con_el_comercio` | `true` si al crearse este pedido la persona no tenía ningún otro con este comercio, en ningún estado. Se fija al crear el pedido. |
| `por_mandato` | `true` si el pedido trae `via.mandato_id`: lo armó un agente con mandato, aunque la persona haya aprobado la confirmación. |

Lo que **no** cuenta en contra, a propósito: `rechazado_por_comercio`, `sin_respuesta_del_comercio`,
`cancelado_por_comercio`, `sin_repartidor`, `pago_vencido` y `nodo_no_disponible`. Son cosas que
decidió o dejó de hacer otro, o que el comprador soltó antes de que alguien moviera un dedo.

## Cómo lo calcula el nodo

- Un agregado por identidad (y por identidad y comercio para `entregados_con_el_comercio`), que se
  actualiza en la misma transacción en que se cierra el pedido: leer un pedido no recorre el
  historial. `antiguedad_dias` y `contacto_confirmado` se leen al vuelo.
- Cualquiera con acceso a los pedidos del comprador (él mismo, con `GET /yo/exportar`) recalcula
  cada número con las reglas de arriba y tiene que dar igual.

## Lo que no hace

- No bloquea, no esconde ni ordena nada por estos hechos. No hay umbral del nodo ni del protocolo.
- Lo que el comercio quiera exigir lo pone él, público en su ficha (`efectivo.pedidos_entregados_minimo`,
  `transferencia.pedidos_entregados_minimo`, requisitos de primera compra en `docs/topes.md`).
- No viaja entre nodos: cuenta solo lo que pasó en este nodo.
