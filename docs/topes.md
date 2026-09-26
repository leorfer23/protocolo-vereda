# Topes públicos

Salvaguarda S9 de `docs/antifraude.md`: frenar la inundación de pedidos y las granjas de
identidades sin que nadie juzgue a nadie. Hay dos clases de reglas, y las dos son públicas y
deterministas:

- **Topes del nodo, iguales para todos.** Números fijos que el nodo publica en `topes` de
  `/.well-known/vereda.json` y aplica a cualquier identidad por igual. No hay lista de sospechosos,
  puntaje ni excepción.
- **Requisitos del comercio.** Lo que cada comercio le pide a quien paga sin pagar antes (efectivo),
  a quien paga por transferencia, o a quien estrena su promo de primera compra. Están en su ficha y
  en sus promociones, y se comprueban contra la verificación pública de la persona.

Una persona honesta no los ve nunca: los topes quedan muy por encima de lo que hace alguien
comprando.

## Topes del nodo

| Tope | Qué cuenta | Default del protocolo |
| --- | --- | --- |
| `pedidos_sin_pagar_por_identidad` | Pedidos de la persona en estado `creado` a la vez, en cualquier comercio del nodo | 3 |
| `pedidos_por_minuto_por_identidad` | Pedidos confirmados por la persona en 60 s, con su sesión o con sus mandatos | 5 |
| `mensajes_por_minuto_por_pedido` | Mensajes que una identidad manda en 60 s en el chat de un mismo pedido | 20 |
| `acceso_por_minuto_por_ip` | Pedidos a `/acceso` desde una misma IP en 60 s | 30 |

- **Por identidad, no por IP.** Detrás de una misma IP hay mucha gente: el CGNAT de una red móvil,
  un edificio, una oficina. Un tope por IP en los pedidos castigaría a todos por uno. El único tope
  por IP está en `/acceso`, que es donde se fabrican identidades.
- **Un pedido `creado` reserva sin haber pagado**: el stock y los cupos quedan retenidos hasta que
  vence el cobro (transferencia) o hasta que el comercio acepta (efectivo). Por eso se acota cuántos
  puede tener abiertos una persona a la vez. Un pedido pagado, aceptado o cancelado deja de contar.
- **Mensajes, por quien escribe.** El tope es de cada identidad en cada pedido: si uno inunda el
  chat, el otro puede seguir contestando.
- **Ventanas fijas de 60 s** para los topes por minuto. Con varias instancias, cada una puede llevar
  su cuenta: el tope es contra el abuso barato, no contra un ataque distribuido.
- Un nodo puede elegir otros valores. Los publica, y son los mismos para todos. Aplicar un tope que
  no publica no es conforme.

## Cuando se pasa un tope

`429 tope_alcanzado`, sin crear nada, con:

- `Retry-After`: los segundos hasta que el tope deja pasar de nuevo. En los topes por minuto, lo que
  falta de la ventana. En `pedidos_sin_pagar_por_identidad`, hasta que vence el primero de esos
  cobros; si ninguno vence solo (efectivo esperando al comercio), hasta su `plazo_aceptacion_min`.
- `detalle` (`esquemas/error.json#/$defs/detalle_tope`): `tope` (su nombre en `topes`), `maximo` y,
  en `pedidos_sin_pagar_por_identidad`, `pedidos`: los que están esperando pago.
- `mensaje` en palabras para la persona, que una app o un agente muestra tal cual. Por ejemplo:
  "Tenés 3 pedidos esperando pago. Pagá o cancelá uno para hacer otro."

Un cliente respeta `Retry-After` y no reintenta antes. Un agente le dice el motivo a la persona en
vez de reintentar en silencio.

## Requisitos del comercio

- **Efectivo:** `efectivo.pedidos_entregados_minimo`, `efectivo.modalidades` y
  `efectivo.monto_maximo` (`docs/carrito-y-reserva.md`).
- **Transferencia:** `transferencia.pedidos_entregados_minimo`. La transferencia directa también
  reserva sin haber pagado, hasta que vence el cobro. Sin cumplirlo, confirmar responde
  `422 medio_no_disponible` con `detalle.requisito`, `detalle.minimo`, `detalle.tiene` y
  `detalle.medios_cobro` (los que sí puede usar); la persona elige otro medio.
- **Promo de primera compra:** `condiciones.primera_compra_requisitos` en la promoción, solo junto a
  `primera_compra: true`:
  - `contacto_confirmado: true`: la persona confirmó un teléfono o un email (`POST /yo/contacto`).
  - `entregados_en_la_red_minimo`: pedidos entregados en toda la red, en cualquier comercio.

  Sin cumplirlos la promo no es candidata (`docs/promociones.md`, paso 1), como cualquier otra
  condición: el carrito se arma igual, sin ese descuento.

"Pedidos entregados en la red" es siempre `verificacion.historial.pedidos_entregados` de la persona
(`GET /actores/{identidad}/verificacion`): el mismo número que ve cualquiera. Así el comprador puede
saber de antemano si cumple, y cualquier app llega a la misma respuesta que el nodo.

Los requisitos se ven en la ficha y en la promo, con palabras: "Transferencia: desde tu segundo
pedido entregado en Vereda", "Promo de primera compra: con contacto confirmado".
