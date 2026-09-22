# Repartidores

Tres personas usan Vereda con el mismo poder: quien compra, quien vende y quien lleva. Este
documento define al que lleva. Las tres decisiones de fondo son de Leo (2026-09-22):

- **Cualquiera es repartidor.** Sin screening, sin aprobación, sin datos que cargue un tercero. Se
  declara solo y reparte al instante.
- **El comercio elige cómo consigue repartidor y responde ante el comprador por la entrega.** Puede
  usar el pool público, sus propios repartidores o el que eligió el comprador, en el orden que quiera.
- **Al repartidor le paga, directo, quien lo contrató.** Comercio o comprador, en efectivo o por
  transferencia a su alias. La plata nunca pasa por la red.

Todo lo que sigue es configurable por el comercio o por la persona, y nada es obligatorio salvo la
transparencia: cada regla que afecta a otro está publicada donde ese otro la puede leer antes. Cada
punto dice qué operación de `openapi.yaml` y qué esquema lo sostienen. Todo existe primero como API y
como herramienta MCP (scope `repartir`); ninguna parte depende de una pantalla.

## a. Modos de asignación

Cada comercio declara en su ficha pública, bloque `envios` de `esquemas/comercio.json`, de dónde
salen los repartidores de sus pedidos:

| Modo | De dónde sale el repartidor | Cómo se le ofrece |
| --- | --- | --- |
| `propios` | Repartidores vinculados al comercio (punto g) | A todos los propios disponibles a la vez, durante `espera_propios_min` (5 por defecto); lo toma el primero que acepta |
| `usuario` | El que nombró el comprador al confirmar el carrito (punto h) | Solo a él, durante `espera_usuario_min` (10 por defecto) |
| `pool` | Cualquier repartidor disponible de la red | El despacho público de tres fases de `docs/ranking-y-despacho.md` |

`envios.asignacion` es la lista de modos **en el orden en que se prueban**: `["propios", "pool"]`
primero ofrece a los propios y, si ninguno acepta en su espera, pasa al pool. Un modo que no aplica
se salta: `usuario` sin repartidor nombrado, `propios` sin propios disponibles. Sin bloque `envios`,
rige `["pool"]`, que es exactamente el despacho que la red tenía antes de este documento.

La cuenta arranca cuando el pedido está `listo` (o antes, si el comercio adelanta el despacho para
cumplir el ETA) y el plazo total es `plazo_asignacion_min` (30 por defecto). Si se cumple sin
repartidor, rige `si_nadie_acepta`:

| `si_nadie_acepta` | Qué pasa | Evento |
| --- | --- | --- |
| `avisar` (default) | El pedido espera la decisión del comercio (punto b). Mientras tanto nada se cancela solo | `pedido.sin_repartidor` |
| `retiro` | El pedido pasa a modalidad `retiro`, sin cobrar envío, con su `codigo_retiro` para el comprador. El comprador puede cancelar sin cargo si no le sirve retirar | `pedido.pasa_a_retiro` |
| `cancelar` | Se cancela con `motivo_codigo: sin_repartidor`. Lo que ya se cobró lo devuelve el comercio, como toda devolución (`docs/carrito-y-reserva.md`); la red lo muestra, no lo ejecuta | `pedido.cancelado` |

Cómo se consiguió el repartidor de cada pedido queda en `pedido.asignacion.modo` y en `viaje.modo`.

## b. El comercio decide pedido por pedido

El orden de la ficha es el default, no una jaula. `POST /pedidos/{id}/asignar` (herramienta
`pedido_asignar`, scope `administrar`) pisa el orden solo para ese pedido, mientras no esté
`en_camino`:

- `modo: comercio` — lo lleva el propio comercio, sin repartidor aparte ni viaje; entrega con
  `POST /pedidos/{id}/entregar` como en retiro.
- `modo: propio` — a sus propios; con `repartidor`, solo a uno.
- `modo: pool` — al despacho público.
- `modo: usuario` — acepta el repartidor que propuso el comprador.

Sirve para responder a `pedido.sin_repartidor`, para relanzar un viaje que el repartidor soltó y para
decidir sobre la propuesta del comprador cuando el comercio no tiene `usuario` en su orden.

## c. Quién responde ante el comprador

La red no arbitra (`docs/federacion.md`, Disputas): no hay fondo de garantía, ni reembolso, ni
reversión. Lo que este documento fija es **a quién le reclama el comprador**, con qué evidencia y hasta
dónde. La evidencia es siempre el historial firmado del pedido; ahora también la firma `retiro`
(`pedido.firmas.retiro`), que el repartidor pone al retirar y marca el traspaso.

| Modo | Quién eligió al repartidor | Quién responde ante el comprador | Hasta cuándo responde el comercio | `pedido.asignacion.responsable_entrega` |
| --- | --- | --- | --- | --- |
| `comercio` | Nadie: lo lleva el comercio | El comercio | Hasta la entrega al comprador | `comercio` |
| `propio` | El comercio | El comercio | Hasta la entrega al comprador | `comercio` |
| `pool` | El comercio, al elegir el pool | El comercio | Hasta la entrega al comprador | `comercio` |
| `usuario` | El comprador | La relación entre el comprador y su repartidor | Hasta entregarle el pedido en mano al repartidor (`firmas.retiro`) | `usuario_y_repartidor` |

> **Decisión a confirmar por Leo.** La fila `usuario` es un supuesto del Lead: si el comprador eligió
> a su repartidor, el comercio cumple entregándoselo en mano, y lo que pase en el camino es entre el
> comprador y el repartidor que él contrató. Si Leo decide otra cosa, cambia esta fila y el enum de
> `responsable_entrega`; nada más.

En todos los modos rige lo mismo que en federación: la fuente de verdad del pedido es el nodo del
comercio, cada operador responde por los actores que hospeda, y el desacuerdo se refleja en la
reputación firmada de las tres partes (punto e).

## d. Cobro P2P al repartidor

El repartidor cobra directo, como el comercio. La tarifa por tramo es pública (`tarifa_envio` en
`/.well-known/vereda.json`, la fija la cooperativa y la aplica la red) y sale en
`viaje.pago_repartidor` antes de aceptar. Lo que cambia según el modo es **quién le paga**:

| Situación | Paga | Cómo | Cómo queda en `pago.json` |
| --- | --- | --- | --- |
| `usuario` | El comprador, siempre: lo contrató él | Efectivo en mano al entregar, o transferencia al alias del repartidor | `concepto: envio`, `destinatario`: el repartidor, sin `pagador` |
| `propio` o `pool` con `cobro_envio: al_repartidor` (default) | El comprador, por cuenta del comercio | Igual que arriba | Igual que arriba |
| `propio` o `pool` con `cobro_envio: al_comercio` | El comercio | El comprador le paga el envío al comercio con los productos; el comercio le paga al repartidor en efectivo al retirar o por transferencia | `concepto: envio`, `destinatario`: el repartidor, `pagador`: el comercio |
| Envío bonificado por promoción (`docs/promociones.md`) | El comercio, la parte bonificada | Efectivo al retirar o transferencia | Un pago `envio` con `pagador`: el comercio por esa parte |
| `comercio` (lo lleva él) | — | El envío es del comercio y va en su cobro | Sin pago al repartidor |
| Propina | Quien la da | Igual que el envío | `concepto: propina_repartidor` |

El medio lo elige quien paga dentro de lo que el repartidor acepta (`cobro.metodos` de su perfil, que
es público). El comprador lo dice al confirmar con `metodo_envio`; el despacho del pool solo ofrece el
viaje a repartidores que aceptan ese medio.

- **Efectivo.** El pago nace `en_mano` cuando el repartidor acepta el viaje. Quien lo cobra lo marca:
  al entregar, `cobrado_en_mano` en `POST /pedidos/{id}/entregar`; si paga el comercio al retirar,
  `cobrado_en_mano` en `POST /pedidos/{id}/retirar`.
- **Transferencia.** El pago nace `pendiente` cuando el repartidor acepta, con `instrucciones` que
  llevan el alias de `repartidor.privado.cobro`. Las ve únicamente quien paga y solo mientras el
  viaje está activo. Los pasos son los mismos que con el comercio: quien pagó avisa
  `POST /pedidos/{id}/transferencia` con `concepto: envio`, y el repartidor, que es el único que ve
  su cuenta, confirma `POST /pedidos/{id}/transferencia/confirmar` con `concepto: envio`
  (herramienta `cobro_confirmar`). Cualquier otro que intente confirmar recibe 403
  `no_es_el_destinatario`.
- **Vencimiento.** Un pago al repartidor vence 24 h después de la entrega y **nunca cancela el
  pedido**: queda `vencido` como constancia de que no se marcó recibido, sale en `sin_confirmar` de
  sus ganancias, y lo que corresponda se dice en la reseña. La red no persigue deudas.

El caso ya existente del efectivo con repartidor no cambia: si los productos también son en
efectivo, el repartidor cobra todo en la puerta y `pedido.reparto` dice cuánto es de quién.

## e. Reputación del repartidor

Las reseñas siguen `esquemas/resena.json` sin cambios: solo sobre un pedido entregado, firmadas, una
por par autor-destinatario por pedido, dentro de 7 días, sin edición ni borrado, con revelación
simultánea por par. Con el repartidor hay cuatro sentidos:

| Autor → destinatario | Entra en | Pesos |
| --- | --- | --- |
| Comprador → repartidor | Reputación del repartidor | `c = 1`, `v = 0,7` fijo (se cancela), `r` = pedidos que ese repartidor le entregó a ese comprador, `k` y `f` como en `docs/resenas.md` |
| Comercio → repartidor | Reputación del repartidor | Igual; `r` = viajes de ese repartidor para ese comercio |
| Repartidor → comprador | Reputación del comprador | Igual que la reseña de un comercio al comprador (`docs/resenas.md`) |
| Repartidor → comercio | Se publica en las reseñas del comercio con `rol_autor: repartidor` | No entra en la reputación del comercio, que mide a sus compradores; la ve cualquier repartidor en `GET /actores/{identidad}/resenas` antes de aceptar un viaje |

Por qué `c = 1` y `v` se cancela: la cercanía existe para frenar granjas de cuentas lejanas, y a un
repartidor solo lo puede reseñar alguien a quien le entregó adentro de su zona; y nadie elige
repartidor del pool por afinidad, así que todos ven el mismo número. `f = 0` si el autor es el mismo
repartidor. La ráfaga se detecta igual, con el repartidor como destinatario.

```
promedio = (Σ wᵢ · pᵢ + 3 · µ_repartidores) / (Σ wᵢ + 3)
```

No hay término de recompra: el comprador no elige al repartidor del pool, así que "volver" no mide
nada. En su lugar, el perfil muestra hechos que no son opinión (`repartidor.json#/$defs/reputacion`):

- `viajes_completados`.
- **Rechazar no penaliza**: una oferta rechazada, o vencida sin respuesta, no queda en ningún lado.
- **Soltar sí se ve**: un viaje aceptado y después dejado (`POST /viajes/{id}/soltar`, herramienta
  `viaje_soltar`) cuenta en `viajes_soltados`, y aparte en `soltados_con_pedido_retirado` si ya tenía
  la mercadería. El viaje vuelve a asignarse por el orden del comercio (`viaje.soltado`).

La reputación no entra en el despacho del pool: el algoritmo público sigue siendo cercanía y
restricciones. Es información para el comercio que arma su lista de propios y para el comprador que
elige uno de confianza. Nadie queda excluido por su número.

Perfil público: `GET /repartidores/{identidad}` (`repartidor.json#/$defs/publico`, herramienta
`ver_repartidor`), sin token y cacheable: nombre, vehículo, cooperativa, medios de cobro,
verificaciones y reputación. Nunca ubicación, zona, disponibilidad ni alias.

## f. Zona de trabajo y restricciones

Declaradas por el repartidor en `PUT /repartidor` (`repartidor.json#/$defs/declaracion`):

- `zona`: un polígono cerrado o `{centro, radio_km}`. El pool **solo le ofrece viajes con todas sus
  paradas adentro de la zona**.
- `vehiculo`, `caja_termica`, `capacidad_kg`: el pool no le ofrece un viaje que requiere caja
  térmica si no la tiene, ni uno que pasa su capacidad.
- `cobro.metodos`: el pool no le ofrece un viaje cuyo envío se paga con un medio que no acepta.

A los propios y al repartidor nombrado por el comprador se les ofrece aunque el viaje salga de su
zona: es un pedido directo, que ven entero antes de aceptar. Las restricciones de frío y peso sí se
aplican siempre.

## g. Repartidor propio de un comercio

No es otro tipo de cuenta: es una identidad de repartidor común, dada de alta sola, con un vínculo
de dos mitades:

- el comercio la pone en `privado.repartidores_propios` (`PATCH /comercios/{id}`, herramienta
  `comercio_editar`), y
- el repartidor pone al comercio en `propio_de` (`PUT /repartidor`, herramienta
  `repartidor_perfil`).

Es propio mientras está en las dos listas. Cualquiera de los dos lo corta sacando al otro de la suya,
sin avisar ni pedir permiso. La lista del comercio no se publica: que alguien reparta para un
comercio es dato del repartidor. Un propio sigue pudiendo tomar viajes del pool y de otros comercios.

## h. Repartidor de confianza del comprador

- La persona guarda los suyos en `preferencias.repartidores_de_confianza` (`esquemas/usuario.json`),
  privados como el resto de sus preferencias; su agente los lee con `mis_preferencias`.
- Al confirmar el carrito nombra uno en `repartidor` (`POST /carritos/{id}/confirmar`, herramienta
  `carrito_confirmar`) y elige `metodo_envio`.
- **Consentimiento del repartidor**, en dos niveles: `acepta_elegido_por_usuario` en su perfil (si es
  false, nombrarlo responde 422 `repartidor_no_acepta` y el carrito no se confirma) y, siempre, aceptar o rechazar ese viaje
  en particular.
- Si el comercio tiene `usuario` en su orden, se le ofrece en ese turno. Si no, queda como propuesta
  en `pedido.asignacion.propuesto_por_usuario` y el comercio la acepta o no con
  `POST /pedidos/{id}/asignar` (punto b). El comprador lo sabe antes: el orden está en la ficha.
- Si su repartidor rechaza o no responde, sigue el orden del comercio. Lo que cambia es quién le paga
  y quién responde: ver puntos c y d.

## i. Herramientas MCP del repartidor

Scope nuevo de mandato: `repartir` (`esquemas/mandato.json`, `securitySchemes` de `openapi.yaml`).
Sirve para operar como repartidor; nunca para comprar ni para administrar un comercio. Una
herramienta por operación, en `mcp/herramientas.json`:

| Herramienta | Operación |
| --- | --- |
| `mi_repartidor` | `GET /repartidor` (`verMiRepartidor`) |
| `repartidor_perfil` | `PUT /repartidor` (`declararRepartidor`) |
| `repartidor_disponibilidad` | `PUT /repartidor/disponibilidad` (`fijarDisponibilidad`) |
| `repartidor_ubicacion` | `PUT /repartidor/ubicacion` (`reportarUbicacion`) |
| `viajes_ofrecidos` | `GET /viajes/ofrecidos` (`listarViajesOfrecidos`) |
| `viaje_aceptar` | `POST /viajes/{id}/aceptar` (`aceptarViaje`) |
| `viaje_rechazar` | `POST /viajes/{id}/rechazar` (`rechazarViaje`) |
| `viaje_soltar` | `POST /viajes/{id}/soltar` (`soltarViaje`) |
| `viaje_retirar` | `POST /pedidos/{id}/retirar` (`retirarPedido`) |
| `viaje_entregar` | `POST /pedidos/{id}/entregar` (`entregarPedido`) |
| `cobro_confirmar` | `POST /pedidos/{id}/transferencia/confirmar` (`confirmarTransferencia`) |
| `mis_viajes` | `GET /repartidor/viajes` (`listarMisViajes`) |
| `mis_ganancias` | `GET /repartidor/ganancias` (`verMisGanancias`) |

Y dos de los otros lados: `ver_repartidor` (público, `verRepartidor`) y `pedido_asignar`
(comercio, `asignarRepartidor`).

**Historial y ganancias.** `GET /repartidor/viajes` pagina por cursor, como la bandeja del comercio,
e incluye los soltados; las ofertas rechazadas no dejan rastro. `GET /repartidor/ganancias`
(`repartidor.json#/$defs/ganancias`) agrega por día, semana, mes o total los pagos cuyo destinatario
es el repartidor: solo cuenta como cobrado lo `confirmado`, separa efectivo de transferencia y muestra
aparte lo que quedó sin marcar recibido. El nodo no guarda nada nuevo para calcularlo.

## j. Qué es configurable y qué no

| Quién | Configura | Dónde |
| --- | --- | --- |
| Comercio | Orden de modos, esperas, plazo total, qué pasa si nadie acepta, a quién se paga el envío, lista de propios; y pedido por pedido, quién lo lleva | `comercio.envios`, `comercio.privado.repartidores_propios`, `POST /pedidos/{id}/asignar` |
| Repartidor | Vehículo, restricciones, zona, medios de cobro y alias, cooperativa, de quién es propio, si acepta ser nombrado; y viaje por viaje, aceptar, rechazar o soltar | `PUT /repartidor`, `/viajes/{id}/*` |
| Comprador | Repartidores de confianza, a quién nombra, cómo paga el envío | `preferencias.repartidores_de_confianza`, `POST /carritos/{id}/confirmar` |

Lo único obligatorio es la transparencia:

- el orden de asignación y a quién se le paga el envío están en la ficha pública del comercio;
- los medios de cobro, las verificaciones y la reputación del repartidor están en su perfil público;
- el monto, la distancia, el peso y cómo se cobra están en el viaje antes de aceptarlo;
- quién eligió al repartidor y quién responde está en cada pedido (`pedido.asignacion`).

Nadie aprueba a nadie: ni el nodo a un repartidor, ni la red a un comercio que usa sus propios, ni el
comercio al repartidor que eligió el comprador —ese solo decide si lo acepta para su pedido.
