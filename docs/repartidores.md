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
(`pedido.firmas.retiro`), que el repartidor pone al retirar y marca el traspaso, y la de entrega
(punto j).

| Modo | Quién eligió al repartidor | Quién responde ante el comprador | Hasta cuándo responde el comercio | `pedido.asignacion.responsable_entrega` |
| --- | --- | --- | --- | --- |
| `comercio` | Nadie: lo lleva el comercio | El comercio | Hasta la entrega al comprador | `comercio` |
| `propio` | El comercio | El comercio | Hasta la entrega al comprador | `comercio` |
| `pool` | El comercio, al elegir el pool | El comercio | Hasta la entrega al comprador | `comercio` |
| `usuario` | El comprador | La relación entre el comprador y su repartidor | Hasta entregarle el pedido en mano al repartidor (`firmas.retiro`) | `usuario` |

**Decisión de Leo (2026-09-22).** Si el comprador eligió a su repartidor, la responsabilidad es del
comprador: tiene que elegir a alguien de confianza, el comercio cumple entregándoselo en mano, y lo
que pase en el camino es entre el comprador y el repartidor que él contrató.

En todos los modos rige lo mismo que en federación: la fuente de verdad del pedido es el nodo del
comercio, cada operador responde por los actores que hospeda, y el desacuerdo se refleja en la
reputación firmada de las tres partes (punto e).

## d. Cobro P2P al repartidor

El repartidor cobra directo, como el comercio. La tarifa por tramo es pública (`tarifa_envio` en
`/.well-known/vereda.json`, la fija la cooperativa y la aplica la red) y sale en
`viaje.pago_repartidor` antes de aceptar. Lo que cambia según el modo es **quién le paga**:

| Situación | Paga | Cómo | Cómo queda en `pago.json` |
| --- | --- | --- | --- |
| `usuario` | El comprador, siempre: lo contrató él | Efectivo en mano al entregar, o transferencia al alias del repartidor | `concepto: envio`, `destinatario`: el repartidor, sin `pagador` (ausente = paga el comprador) |
| `propio` o `pool` con `cobro_envio: al_repartidor` (default) | El comprador, por cuenta del comercio | Igual que arriba | Igual que arriba |
| `propio` o `pool` con `cobro_envio: al_comercio` | El comercio | El comprador le paga el envío al comercio con los productos; el comercio le paga al repartidor en efectivo al retirar o por transferencia | `concepto: envio`, `destinatario`: el repartidor, `pagador`: el comercio |
| Envío bonificado por promoción (`docs/promociones.md`) | El comercio, la parte bonificada | Efectivo al retirar o transferencia | Un pago `envio` con `pagador`: el comercio por esa parte |
| `comercio` (lo lleva él) | — | El envío es del comercio y va en su cobro | Sin pago al repartidor |
| Propina | Quien la da | Igual que el envío | `concepto: propina_repartidor` |

El medio lo elige quien paga dentro de lo que el repartidor acepta (`cobro.metodos` de su perfil, que
es público). El comprador lo dice al confirmar con `metodo_envio`; el despacho del pool solo ofrece el
viaje a repartidores que aceptan ese medio.

**La oferta dice todo esto antes de aceptar.** Cada viaje ofrecido (`listarViajesOfrecidos`,
`verViaje` y el evento `viaje.ofrecido`) trae, por pedido, `pago_repartidor.por_pedido[].cobros`
(`esquemas/viaje.json#/$defs/cobro`): quién le paga (`comprador` o `comercio`), por qué medio
(`efectivo` o `transferencia`), cuánto y por qué concepto (`envio` o `propina_repartidor`). Son los
mismos pagos que nacen en el pedido si acepta, dichos antes y calculados para ese repartidor: si no
acepta efectivo, lo que le paga el comercio sale por transferencia; si no declaró alias, sale en
efectivo. Los `envio` de un pedido suman su `monto`. Con efectivo, quién paga dice cuándo cobra: el
comercio al retirar, el comprador al entregar. En modo `usuario` el pagador es siempre `comprador`, y
`viaje.modo` dice que es el comprador que lo eligió. Un pago bonificado del comercio es un segundo
`cobro` con `pagador: comercio`.

**En modo `usuario` el monto también se arregla entre ellos.** El comprador lo dice al confirmar el
carrito, `monto_envio_acordado_centavos` (`POST /carritos/{id}/confirmar`, herramienta
`carrito_confirmar`): opcional, y si falta rige `tarifa_envio`, la pública. El repartidor lo ve en
`viaje.pago_repartidor` antes de aceptar, igual que la tarifa pública en cualquier otro modo, y decide
si le sirve. Lo que se cobra y lo que queda en `pago.json` (`concepto: envio`) es ese monto, acordado
o público, nunca otro.

- **Efectivo.** Si el comprador dijo con qué billete paga, el viaje lo trae en `por_pedido[].paga_con`, para llevar cambio. El pago nace `en_mano` cuando el repartidor acepta el viaje. Quien lo cobra lo marca:
  al entregar, `cobrado_en_mano` en `POST /pedidos/{id}/entregar`; si paga el comercio al retirar,
  `cobrado_en_mano` en `POST /pedidos/{id}/retirar`.
- **Transferencia.** El pago nace `pendiente` cuando el repartidor acepta, con `instrucciones` que
  llevan el alias de `repartidor.privado.cobro`. Las ve únicamente quien paga y solo mientras el
  viaje está activo. El monto exacto, con los centavos únicos, lo ve también el repartidor en
  `pago.monto_a_transferir`, para reconocer la transferencia en su cuenta. Los pasos son los mismos que con el comercio: quien pagó avisa
  `POST /pedidos/{id}/transferencia` con `concepto: envio`, y el repartidor, que es el único que ve
  su cuenta, confirma `POST /pedidos/{id}/transferencia/confirmar` con `concepto: envio`
  (herramienta `cobro_confirmar`). Cualquier otro que intente confirmar recibe 403
  `no_es_el_destinatario`.
- **Vencimiento.** Un pago al repartidor vence 24 h después de la entrega y **nunca cancela el
  pedido**: queda `vencido` como constancia de que no se marcó recibido, sale en `sin_confirmar` de
  sus ganancias, y lo que corresponda se dice en la reseña. La red no persigue deudas.

El caso ya existente del efectivo con repartidor no cambia: si los productos también son en
efectivo, el repartidor cobra todo en la puerta y `pedido.reparto` dice cuánto es de quién. Lo que
es del comercio se lo da como dice el punto l: después de entregar, o adelantado al retirar.

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
- `rendiciones`: cómo rindió el efectivo que cobró por cuenta de los comercios (punto l, "A la
  vista"). Conteos, nunca montos.
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
  `carrito_confirmar`), elige `metodo_envio` y, si ya arregló el precio con él,
  `monto_envio_acordado_centavos` (punto d; sin ese campo rige la tarifa pública).
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
| `viaje_ver` | `GET /viajes/{id}` (`verViaje`) |
| `viaje_aceptar` | `POST /viajes/{id}/aceptar` (`aceptarViaje`) |
| `viaje_rechazar` | `POST /viajes/{id}/rechazar` (`rechazarViaje`) |
| `viaje_soltar` | `POST /viajes/{id}/soltar` (`soltarViaje`) |
| `viaje_retirar` | `POST /pedidos/{id}/retirar` (`retirarPedido`) |
| `viaje_entregar` | `POST /pedidos/{id}/entregar` (`entregarPedido`) |
| `cobro_confirmar` | `POST /pedidos/{id}/transferencia/confirmar` (`confirmarTransferencia`) |
| `rendicion_declarar` | `POST /pedidos/{id}/rendicion` (`declararRendicion`) |
| `viaje_no_recibido` | `POST /pedidos/{id}/no-vino` con `no_recibido` (`marcarNoVino`) |
| `mis_viajes` | `GET /repartidor/viajes` (`listarMisViajes`) |
| `mis_ganancias` | `GET /repartidor/ganancias` (`verMisGanancias`) |

Y tres de los otros lados: `ver_repartidor` (público, `verRepartidor`), `pedido_asignar`
(comercio, `asignarRepartidor`) y `rendicion_confirmar` (comercio, `confirmarRendicion`).

**Historial y ganancias.** `GET /repartidor/viajes` pagina por cursor, como la bandeja del comercio,
e incluye los soltados; las ofertas rechazadas no dejan rastro. `GET /repartidor/ganancias`
(`repartidor.json#/$defs/ganancias`) agrega por día, semana, mes o total los pagos cuyo destinatario
es el repartidor: solo cuenta como cobrado lo `confirmado`, separa efectivo de transferencia y muestra
aparte lo que quedó sin marcar recibido. El nodo no guarda nada nuevo para calcularlo.

**Releer un viaje.** `GET /viajes/{id}` devuelve el viaje entero, con todas sus paradas, a su
repartidor, al repartidor a quien se le está ofreciendo y al comercio de cualquier pedido del viaje.
El comprador no lo lee: sigue su pedido con `GET /pedidos/{id}`, y un viaje puede llevar las
direcciones de otros compradores. A cualquier otro, 404, como si no existiera.

## j. La firma del repartidor al retirar y al entregar

El retiro y la entrega los firma el repartidor con su clave, como una reseña o un mandato. Es la
evidencia del punto c: `pedido.firmas.retiro` marca el traspaso y `pedido.firmas.entrega` la entrega.

**Qué se firma.** El JCS (RFC 8785) de `pedido.json#/$defs/traspaso`:

```json
{ "accion": "entrega", "instante": "2026-09-21T15:04:05-03:00",
  "pedido_id": "01926b3a-...", "repartidor": "marta@vereda.ar" }
```

`accion` es `retiro` o `entrega`, `repartidor` es el firmante y `instante` es el de la firma. Todo
sale del pedido y de la firma guardada, así que cualquiera rearma el traspaso y verifica, sin que el
nodo guarde nada más. No lleva el código de retiro ni montos: el código es del comprador, y lo que se
cobró ya está en `pedido.pagos`. Los bytes exactos están en `ejemplos/vectores-firma.json` →
`traspaso-entrega`.

**Cómo la manda.** Con la clave en el teléfono (custodia propia), el repartidor firma al tocar
"retiré" o "entregué" y manda la `firma` (`comunes.json#/$defs/firma`) en el cuerpo de
`POST /pedidos/{id}/retirar` o `POST /pedidos/{id}/entregar`. Un solo campo: el nodo rearma el
traspaso con la acción de la ruta, el id del pedido y la identidad de la sesión.

**Qué hace el nodo.**

| Caso | Respuesta |
| --- | --- |
| `firma` verifica (pasos de `docs/claves-y-firmas.md` contra el historial del repartidor) | Mueve el pedido y guarda la firma tal cual en `firmas.retiro` o `firmas.entrega` |
| Sin `firma` y el nodo custodia la clave del repartidor | Firma el nodo, sobre el mismo traspaso |
| Sin `firma`, con sesión y custodia propia | 422 `firma_requerida`; el pedido no se mueve |
| Sin `firma`, por mandato (`repartir`) | Mueve el pedido sin esa firma: un agente no firma por la persona; el historial dice quién y cuándo |
| `firmante` distinto de quien actúa, o `instante` a más de 5 minutos del reloj del nodo | 422 `firma_invalida` |
| No verifica, clave fuera del historial o comprometida | 422 `firma_invalida`, `clave_desconocida` o `clave_comprometida` |

Un 422 no mueve nada: el repartidor vuelve a firmar y reintenta. En modalidad `retiro` entrega el
comercio y la prueba es el código del comprador; esta firma es la del repartidor.

## k. Qué es configurable y qué no

| Quién | Configura | Dónde |
| --- | --- | --- |
| Comercio | Orden de modos, esperas, plazo total, qué pasa si nadie acepta, a quién se paga el envío, cuándo le rinden el efectivo, lista de propios; y pedido por pedido, quién lo lleva | `comercio.envios`, `comercio.privado.repartidores_propios`, `POST /pedidos/{id}/asignar` |
| Repartidor | Vehículo, restricciones, zona, medios de cobro y alias, cooperativa, de quién es propio, si acepta ser nombrado; y viaje por viaje, aceptar, rechazar o soltar | `PUT /repartidor`, `/viajes/{id}/*` |
| Comprador | Repartidores de confianza, a quién nombra, cómo paga el envío | `preferencias.repartidores_de_confianza`, `POST /carritos/{id}/confirmar` |

Lo único obligatorio es la transparencia:

- el orden de asignación, a quién se le paga el envío y cuándo se le rinde el efectivo están en la
  ficha pública del comercio;
- los medios de cobro, las verificaciones y la reputación del repartidor, con cómo rindió el
  efectivo, están en su perfil público, y cómo confirmó el comercio lo que le rindieron, en su ficha;
- el monto, la distancia, el peso, quién paga cada envío y por qué medio, y cuánto efectivo se le
  va a deber al comercio y cuándo, están en el viaje antes de aceptarlo;
- quién eligió al repartidor y quién responde está en cada pedido (`pedido.asignacion`).

Nadie aprueba a nadie: ni el nodo a un repartidor, ni la red a un comercio que usa sus propios, ni el
comercio al repartidor que eligió el comprador —ese solo decide si lo acepta para su pedido.

## l. La rendición del efectivo al comercio

Con un pedido en efectivo que lleva un repartidor, el comprador le paga todo en la puerta:
productos, envío, propina. Lo de los productos es del comercio, y el repartidor se lo tiene que dar.
La red no ve esa plata ni la custodia; lo que hace es que las dos partes dejen dicho, cada una con su
clave, cuánto se dio y cuánto se recibió. **Decisión de Leo (2026-09-23).**

**Cuándo, lo elige el comercio.** `envios.rendicion_efectivo` en su ficha pública:

| Valor | Qué pasa | Riesgo para el repartidor |
| --- | --- | --- |
| `despues_de_entregar` (default) | El repartidor cobra en la entrega y después le da al comercio lo suyo | Ninguno de plata: no pone nada de su bolsillo |
| `al_retirar` | El repartidor le paga al comercio al retirar, adelantando esa plata, y la recupera al cobrar en la entrega | Adelanta: si en la puerta no le pagan, la plata la puso él |

**Qué se debe.** `pedido.rendicion.monto`: la suma de los pagos en efectivo del comprador al
comercio que cobra el repartidor en la entrega (`productos`, `propina_comercio` y, con
`cobro_envio: al_comercio`, el `envio`). Lo que el comercio le paga al repartidor (su envío con
`al_comercio`) sigue siendo un pago aparte, con su propio `cobrado_en_mano` al retirar (punto d):
pueden arreglarlo en el mismo encuentro, pero cada cosa queda dicha por separado.

La rendición existe solo en pedidos con repartidor (modos `propio`, `pool` y `usuario`) en los que
el repartidor cobra algo en mano por cuenta del comercio. Nace `pendiente` cuando el repartidor
acepta el viaje, con el `modo` del comercio congelado en ese momento. Si el pedido se cancela sin
ninguna constancia, desaparece: no pasó plata de mano. Con constancias queda como está.

**Lo ve antes de aceptar.** Cada pedido del viaje ofrecido trae
`pago_repartidor.por_pedido[].rendicion` (`esquemas/viaje.json#/$defs/rendicion`): cuánto le va a
deber al comercio y `cuando`. Con `al_retirar`, ese es el monto que tiene que llevar encima para
retirar. Ausente si no cobra nada en mano por cuenta del comercio.

**Dos constancias firmadas.** Cada parte firma su parte, sobre
`pedido.json#/$defs/constancia_rendicion`:

```json
{ "accion": "rendida", "actor": "marta@vereda.ar", "instante": "2026-09-21T15:30:00-03:00",
  "monto": { "centavos": 1234000, "moneda": "ARS" }, "pedido_id": "01926b3a-..." }
```

| Quién | Operación | Herramienta | Acción | Desde cuándo |
| --- | --- | --- | --- | --- |
| Repartidor | `POST /pedidos/{id}/rendicion` (`declararRendicion`) | `rendicion_declarar` | `rendida`: "te di $X" | `al_retirar`: desde que aceptó el viaje, y antes de retirar. `despues_de_entregar`: desde que el pedido está `entregado` |
| Comercio | `POST /pedidos/{id}/rendicion/confirmar` (`confirmarRendicion`) | `rendicion_confirmar` | `recibida`: "recibí $X" | Después de una `rendida` |

El cuerpo es `{monto, firma?}`. El nodo arma la constancia con la acción de la ruta, el id del
pedido, el actor (el repartidor, o la identidad del comercio: firma con la clave del comercio,
no con la de quien lo administra) y el instante de la firma, y la agrega entera a
`pedido.rendicion.constancias`, que no se edita ni se borra. A diferencia del traspaso, lleva el
monto: es justamente lo que se firma. Las reglas de la firma son las del punto j: la manda el
teléfono si tiene la clave; si no viene y el nodo custodia la clave, firma el nodo; con sesión y
custodia propia, 422 `firma_requerida`; por mandato, la constancia queda sin firma, porque un agente
no firma por la persona. Los bytes exactos están en `ejemplos/vectores-firma.json` →
`rendicion-rendida`.

**Estados.** `pedido.rendicion.estado` sale de las constancias:

| Estado | Cuándo | Qué ve el repartidor | Qué ve el comercio | Evento |
| --- | --- | --- | --- | --- |
| `pendiente` | Sin ninguna `rendida` | Cuánto debe y cuándo | Cuánto le deben | — |
| `declarada` | La última `rendida` todavía no tiene `recibida` después | Que declaró y espera | Que el repartidor dice haberle dado $X, para confirmar | `rendicion.declarada` |
| `confirmada` | La última `recibida`, posterior a la última `rendida`, dice el mismo monto | Cerrada | Cerrada | `rendicion.confirmada` |
| `en_desacuerdo` | La última `recibida`, posterior a la última `rendida`, dice otro monto | Las dos versiones | Las dos versiones | `rendicion.en_desacuerdo` |

Los tres eventos llegan al comercio y al repartidor del pedido, con la rendición entera en
`datos.rendicion`. Al comprador no: es entre ellos, y su copia del pedido no trae `rendicion`.
`confirmada` es final: otra constancia responde 409 `rendicion_confirmada`. Una `recibida` sin una
`rendida` antes responde 409 `rendicion_sin_declarar`; una `rendida` antes de tiempo, 409
`rendicion_antes_de_tiempo`; cualquiera en un pedido sin rendición, 409 `rendicion_no_aplica`.

**Si el comercio no confirma, o dice otro monto.** Nada vence, nada se castiga y nadie arbitra
(`docs/federacion.md`, Disputas). Queda a la vista de los dos, firmado:

- Sin confirmar, la rendición sigue `declarada` con la firma del repartidor: es su constancia de
  que dijo haber pagado, con fecha.
- En desacuerdo, están las dos versiones firmadas. Si se arregla (el repartidor completa la
  diferencia, o el comercio contó mal), cualquiera agrega otra constancia y, cuando la última de
  cada uno coincide, queda `confirmada`. Las anteriores siguen ahí.
- Lo que corresponda se dice en la reseña, en los dos sentidos (punto e). La red no persigue deudas:
  lo que hace es contar, a la vista (abajo).

**Con `al_retirar`, el retiro espera la rendición.** Si el comercio eligió que el repartidor le pague
al retirar, `retirarPedido` (y `viaje_retirar`) no mueve el pedido hasta que la rendición está
`confirmada`: el repartidor declaró cuánto le dio y el comercio dijo lo mismo. Antes responde 409
`rendicion_pendiente`, con `detalle.estado` (`pendiente`, `declarada` o `en_desacuerdo`) y un
`mensaje` que dice qué falta ("Declará cuánto le diste al comercio" o "Falta que el comercio
confirme que recibió $X"). Es la regla que el comercio eligió y el repartidor vio en la oferta
(`rendicion.cuando`), no un castigo. Con `despues_de_entregar` el retiro es el de siempre.

**A la vista.** Cómo le fue a cada uno con las rendiciones es público, en conteos y nunca montos
(`pedido.json#/$defs/rendiciones`):

- **Repartidor**, en `repartidor.reputacion.rendiciones` (su perfil público, `GET
  /repartidores/{identidad}`, herramienta `ver_repartidor`): lo que ve el comercio al elegir a
  quién le da el pedido ("Rindió 57 de 57" o "2 en desacuerdo · 1 sin rendir hace más de 24 h").
- **Comercio**, en `comercio.rendiciones` (su ficha) y en cada pedido de la oferta de viaje, en
  `pago_repartidor.por_pedido[].rendicion.comercio`: lo que ve el repartidor antes de aceptar
  ("Confirmó 57 de 57"), porque el que no confirma lo que recibió también hace daño.

Las reglas, para el actor como repartidor o como comercio de un pedido, sobre todas sus
rendiciones (las que desaparecieron al cancelarse sin constancias no existen):

| Campo | Repartidor | Comercio |
| --- | --- | --- |
| `total` | Rendiciones de pedidos `entregado`, más las que tienen alguna constancia | Rendiciones con al menos una `rendida` |
| `rendidas` | Estado `confirmada` | Estado `confirmada` |
| `en_desacuerdo` | Estado `en_desacuerdo` | Estado `en_desacuerdo` |
| `pendientes_mas_24h` | Estado `pendiente` y el pedido `entregado` hace más de 24 h | Estado `declarada` y la última `rendida` tiene más de 24 h |

Son estados de hoy, no historia: una rendición en desacuerdo que se arregla pasa a `rendidas`, y
una pendiente que se declara sale de `pendientes_mas_24h`. `total`, `rendidas` y `en_desacuerdo`
se actualizan con cada constancia y cada entrega; `pendientes_mas_24h` depende del reloj, y la
recalcula el mantenimiento horario del nodo, así que puede llegar con hasta una hora de atraso.
Cualquiera que tenga las rendiciones de un actor llega a los mismos números.

Nada vence ni castiga: no excluye a nadie del pool, no ordena el despacho, no baja el ranking. Es
un hecho para quien decide: el comercio que arma su lista de propios o acepta al repartidor del
comprador, y el repartidor que mira una oferta.


## m. Entregar con código

Es lo mismo que el retiro por el local, que ya usa código (`docs/carrito-y-reserva.md`): el
comprador ve "Tu código: 4821" en su pedido y se lo dice a quien le entrega, que lo escribe al tocar
"entregué". Protege contra el "no llegó" (`docs/antifraude.md`, S6): con el código, la entrega deja
una recepción firmada, no solo la palabra del repartidor.

**El código.** Todo pedido con envío (toda modalidad menos `retiro`) lleva `codigo_entrega`, cuatro
dígitos que genera el nodo al crear el pedido. Lo ve únicamente el comprador, y su agente con
`leer`; la copia del comercio y la del repartidor lo omiten. Si el pedido pasa a retiro
(`pedido.pasa_a_retiro`), lleva `codigo_retiro` en su lugar.

**La regla es del comercio, y pública.** Cada modalidad con envío dice en la ficha
`codigo_entrega`:

| Regla | Cuándo hay que pedir el código |
| --- | --- |
| `nunca` (default) | Nunca. Si el comprador lo da igual, se puede mandar y deja la recepción firmada |
| `solo_efectivo` | Cuando quien entrega cobra algo en mano (hay pagos `en_mano` al entregar) |
| `siempre` | En toda entrega |

La regla vigente al crear el pedido se congela en `pedido.modalidad.codigo_entrega`: cambiarla
después no toca los pedidos en curso. Con el default nada cambia para nadie.

**Qué hace el nodo en `POST /pedidos/{id}/entregar`.**

| Caso | Respuesta |
| --- | --- |
| `codigo_entrega` coincide | Entrega y firma `firmas.recepcion` (abajo) |
| La regla pide código, no vino, y vino `foto` | Entrega igual y deja `sin_codigo: {motivo: no_lo_dio, foto}` |
| La regla pide código y no vino ni código ni `foto` | 422 `codigo_entrega_requerido`; el pedido no se mueve |
| La regla es `nunca` y no vino código | Entrega como siempre, sin `sin_codigo` |
| `codigo_entrega` no coincide | 422 `codigo_entrega_invalido` con `detalle.intentos_restantes`; el intento cuenta |
| Ya hubo 5 intentos equivocados | Cualquier código responde 422 `codigo_agotado`; con `foto` entrega y deja `sin_codigo: {motivo: intentos_agotados, foto}` |

Si el comprador no está (lo deja en portería, con un vecino), se entrega con foto, como hoy. No es
un bloqueo ni una sanción: `sin_codigo` queda a la vista del comprador, del comercio y del
repartidor, y cada uno saca su conclusión: es un hecho registrado, no un juicio del nodo.

Si no hay nadie a quien dejárselo, el repartidor no entrega: pasados 10 minutos de la hora prometida
marca `no_recibido` desde la puerta, con su ubicación firmada, y vuelve con el pedido al comercio
(`docs/carrito-y-reserva.md`, "No vino").

**Tope de intentos.** Cinco equivocados por pedido, para `codigo_entrega` y para `codigo_retiro`: con
cuatro dígitos, sin tope, el código se adivina probando. Cada intento equivocado cuenta aunque
responda 422 y el pedido no se mueva. El mensaje dice cuántos quedan ("El código no coincide. Te
quedan 3 intentos"), y `detalle.intentos_restantes` lo da en número. Agotados, en retiro también se
entrega con foto: el comercio no queda con la mercadería trabada, y el pedido queda `sin_codigo`
con `intentos_agotados`.

**La recepción firmada.** Con un código válido, sea de entrega o de retiro, el nodo firma con su
clave `pedido.json#/$defs/recepcion`:

```json
{ "accion": "recepcion", "entrego": "marta@vereda.ar", "instante": "2026-09-21T15:04:05-03:00",
  "pedido_id": "01926b3a-...", "usuario": "juan@vereda.ar" }
```

y la guarda en `pedido.firmas.recepcion`, con `firmante` = el dominio del nodo. `entrego` es quien
mandó el código, el `actor` del paso a `entregado` en `historial`: el repartidor, o la persona
del comercio en retiro o si lleva él. No lleva el código. Se
verifica contra las claves del nodo en `/.well-known/vereda.json`. Qué prueba y qué no, en
`docs/claves-y-firmas.md`, "Recepción con código".

La firma de la entrega (punto j) no cambia: el repartidor sigue firmando su traspaso, con o sin
código. Son dos hechos distintos: "entregué" lo dice el repartidor; "le dieron el código del
comprador" lo atestigua el nodo.

**Por MCP.** El agente del comprador lee su código con `estado_pedido`; el del repartidor lo manda
en `viaje_entregar` (y el del comercio que lleva él, en `pedido_entregar`), con `codigo_entrega`.
