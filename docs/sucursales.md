# Sucursales

Un comercio grande tiene varios locales: una distribuidora con depósito en Warnes y locales en Caballito y Flores, una cadena de farmacias. Cada local tiene su stock, su horario, su zona y la gente que atiende. Quien compra le compra a **su** sucursal: el de Miami quiere McDonald's Miami, no el de Nevada. Cómo abastece la marca a sus locales (un depósito que alimenta a varios, un local que le pasa mercadería a otro) es asunto de la marca, y el protocolo no se mete.

La investigación está en `docs/investigaciones/sucursales.md`. Lo que se decidió:

1. **Cada sucursal es un comercio.** Tiene su ficha, su stock, su zona, sus horarios, su equipo, su cuenta de cobro y su reputación. Carrito, reserva, pedido, despacho, cobro y reseñas no cambian: son de la sucursal que atiende.
2. **La marca es un comercio más, la casa.** Las sucursales la nombran en `sucursal_de`. La casa puede vender como cualquier local o ser solo la marca (`vende: false`).
3. **El catálogo se carga una vez.** Una sucursal con `hereda_catalogo` publica las ofertas de la casa como propias y pisa solo stock, disponibilidad y precio.
4. **Se le compra a la sucursal que te atiende.** Quien entra por la marca cae en su sucursal: la más cercana que llega a su dirección. Puede elegir otra. El pedido es de esa sucursal, y ella responde por él.
5. **Adentro de la marca, manda la marca.** El protocolo no rutea pedidos entre locales ni modela depósitos. Si la sucursal se abastece de un depósito, lo ve el comprador solo como el stock que la sucursal publica.
6. **Ningún pedido se divide.** Si hace falta de dos locales, son dos carritos, como en Instacart. Dividir complica efectivo, reparto, reseñas y reclamos, y nadie lo hace para entregas en el día.

## El vínculo

- `sucursal_de` es la **identidad** de la casa (`actor@nodo`), no un id: así una sucursal puede vivir en otro nodo cuando haya federación.
- Nadie aprueba una sucursal, pero el vínculo tiene que ser cierto: quien escribe `sucursal_de` tiene que administrar los dos comercios con permiso `datos` (la dueña, un miembro con `datos` en ambos, o un agente con el mandato `administrar` de alguien así). Si no, `403 sin_permiso`. Apuntar a un comercio que no existe, a sí mismo o a otra sucursal, `422 casa_invalida`: la cadena tiene un solo nivel.
- La casa no elige sus sucursales: las sucursales la nombran. Su ficha publica `sucursales` (solo lectura, la escribe el nodo) con identidad, id, `nombre_sucursal`, dirección si es pública y `abierto_ahora` de cada una.
- Soltar el vínculo es `sucursal_de: null`. La sucursal sigue siendo un comercio; deja de heredar catálogo y de recibir carritos de la marca.
- Una casa con sucursales no puede ser sucursal de otra (`422 casa_invalida`).
- Las sucursales de la misma dueña ya están vinculadas (`docs/identidad-y-verificacion.md`): sus reseñas entre sí pesan 0 y no son homónimos cerca.

`nombre_sucursal` ("Caballito", "Depósito Warnes") es lo que las apps muestran después de la marca: "Santa Elena · Caballito".

## La casa que no vende

`vende: false` dice que la casa es solo la marca: no aparece en `buscarComercios` como tienda ni tiene ofertas propias a la venta, y un carrito con `comercio_id` de la casa responde `422 comercio_no_vende`. Sí recibe carritos a la marca (`casa`), que nacen en una sucursal. Sin vender, `modalidades` y `politica_cancelacion` dejan de ser obligatorias. Default: `true`.

## Catálogo heredado

Una sucursal con `hereda_catalogo: true` (y `sucursal_de` puesto):

- Publica **todas las ofertas de la casa** como suyas: mismo `id` de oferta, `comercio_id` de la sucursal y `heredada_de` con la identidad de la casa. Nombre, descripción, fotos, opciones, variantes y atributos son los de la casa y se editan en la casa.
- Pisa por oferta, con `actualizarStock` como siempre, solo `stock`, `disponible` y `precio_centavos` (y por variante). Un sistema de stock manda un `PUT /comercios/{sucursal}/stock` por sucursal.
- **Sin fila propia**, una oferta heredada con `stock` numérico en la casa tiene stock `0` en la sucursal: el stock de un local no se presta a otro. Una con stock binario (sin número) hereda `disponible` y precio de la casa.
- Puede tener además ofertas propias, que se crean y editan como siempre.
- `editarOferta` sobre una oferta heredada en la sucursal responde `409 oferta_heredada` con `detalle.editar_en` (la casa), salvo los tres campos que pisa.
- Una oferta que la casa borra o despublica desaparece de todas sus sucursales.

Las búsquedas, el carrito y el pedido tratan una oferta heredada como una propia de la sucursal. El precio que ve el comprador es el de la sucursal.

## Comprarle a la marca: tu sucursal

El protocolo solo resuelve **qué sucursal te atiende**, y lo hace por geografía, igual para todas las marcas:

- `POST /carritos` con `casa` (su identidad) en lugar de `comercio_id`, más `direccion` o `punto` y, si es para retirar, `modalidad: "retiro"`. El carrito nace en **tu sucursal**: entre las que llegan a esa dirección (en retiro, todas), la abierta más cercana; si ninguna está abierta, la más cercana. Un empate lo gana la de mejor puntaje en `docs/ranking-y-despacho.md`. El carrito lo dice en `sucursal_elegida: {casa, motivo}`.
- Ninguna llega a esa dirección: `422 sin_sucursal_disponible`.
- Quien compra puede elegir otra: `POST /carritos/{id}/sucursal` con `comercio_id` muda el carrito a otra sucursal de la misma casa. Los ítems pasan por `oferta_id` (el mismo en todas si es heredada) o, si no, por `ean`; lo que no está queda en `faltantes`. Precio y stock se revalidan con los de la sucursal nueva y lo de la vieja se libera. Solo antes de confirmar.
- Si algo no está en tu sucursal y sí en otra que llega a tu dirección, el carrito lo marca en `faltantes[].en_sucursales`, para que quien compra decida. El nodo nunca muda solo.
- El pedido es de la sucursal y lleva `casa` (solo lectura) para mostrar "Santa Elena · Caballito".

## Adentro de la marca

- **Abastecimiento.** Un depósito que alimenta a varios locales, una sucursal que le pasa mercadería a otra, una cocina central: logística de la marca. Lo único que el protocolo ve es el stock que cada sucursal publica con `actualizarStock`, venga de donde venga. Un depósito que no le vende al público no necesita estar en Vereda; si la marca quiere mostrarlo, es un comercio con `vende: false`.
- **Quién prepara.** Si la marca prepara un pedido en otro lado y lo manda desde ahí, el pedido sigue siendo de la sucursal que vendió: ella responde por la entrega, el cobro y la reseña. Si el retiro o el envío salen de otra dirección, la sucursal la informa en el pedido como hoy.
- **Precios y catálogo.** La marca decide si todas sus sucursales venden igual (catálogo heredado, sin pisar precio) o si cada una fija el suyo.

## Buscar

- `buscarComercios` y `buscarOfertas` aceptan `agrupar=casa`: de cada marca vuelve una sola sucursal, la primera en el orden pedido, con `otras_sucursales` (cuántas más de la misma marca llegan a ese punto). Sin `agrupar`, cada sucursal es un resultado, como hoy.
- Una casa con `vende: false` no sale en `buscarComercios`, pero sus sucursales llevan `casa` para que las apps la muestren.
- `GET /comercios/{id}/sucursales` (y la herramienta MCP `sucursales_ver`) lista las sucursales de una casa, con `lat`/`lng` opcionales para ordenar por distancia y marcar las que llegan.

## Reputación

La reputación es de la sucursal: es la que preparó y entregó. La casa publica además `reputacion_casa` (solo lectura): la misma fórmula de `docs/resenas.md` sobre las reseñas de todas sus sucursales y las propias. Las apps pueden mostrarla en la ficha de la marca, siempre junto a la de cada sucursal y nunca en su lugar.

## Cobro

Cada sucursal tiene su `privado.cuenta_cobro` y sus `cobradores`; pueden repetir la misma cuenta. Por eso **los centavos únicos y la referencia única son por cuenta de cobro**, no por comercio: dos cobros pendientes a la misma cuenta, aunque sean de dos sucursales, nunca piden el mismo monto ni la misma referencia (`docs/carrito-y-reserva.md`).

## Equipo

Cada sucursal tiene su equipo, porque cada local tiene su encargado. La dueña es la misma en todas. Un miembro que tiene que estar en todas se invita en cada una.

## Errores

| Situación | HTTP | `codigo` |
| --- | --- | --- |
| `sucursal_de` a un comercio que no existe, a sí mismo, a una sucursal, o desde una casa con sucursales | 422 | `casa_invalida` |
| `sucursal_de` o `hereda_catalogo` sin `datos` en los dos comercios | 403 | `sin_permiso` |
| `hereda_catalogo` sin `sucursal_de` | 422 | `casa_invalida` |
| Carrito con `comercio_id` de una casa con `vende: false` | 422 | `comercio_no_vende` |
| Carrito a la marca sin ninguna sucursal abierta que llegue | 422 | `sin_sucursal_disponible` |
| Mudar el carrito a un comercio que no es de la misma marca | 422 | `no_es_sucursal` |
| Editar en la sucursal lo que es de la casa | 409 | `oferta_heredada` |

## Fuera de alcance, a propósito

- Pedidos divididos entre sucursales.
- Ruteo de pedidos entre locales, depósitos y traspasos de stock: son de la marca.
- Fidelidad compartida entre sucursales (`fidelidad_de`), equipo con alcance a todas las sucursales y sucursales en otro nodo: van después, sobre este mismo modelo.
