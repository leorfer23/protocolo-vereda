# Sucursales: cómo modela Vereda un comercio con varios locales

Borrador de diseño, 2026-09-28. Disparador: Santa Elena, distribuidora de alimentos con varias
sucursales, cada una con su stock. La pregunta es doble: qué cambia en el protocolo y qué ve quien
compra.

## 1. Qué hay hoy en el protocolo

- `esquemas/comercio.json` tiene `sucursal_de` ("Si es sucursal, el comercio padre"). Es el único
  rastro. El nodo lo guarda (`nucleo/tipos_entidades.go`) pero no lo valida ni lo usa: ninguna ruta
  lista sucursales, `buscarComercios` no agrupa y nadie comprueba que el padre sea de la misma dueña.
- `docs/identidad-y-verificacion.md`: las sucursales de una cadena quedan **vinculadas por `dueno`**
  (y por `cuit` o `cuenta_cobro` si los comparten). Consecuencias que ya valen: las reseñas y
  atestaciones entre ellas pesan 0, y una sucursal propia no cuenta como homónimo cerca
  (`api/identidad_test.go` lo prueba).
- **Todo lo transaccional cuelga del comercio**: `oferta.comercio_id`, `stock` (binario o numérico, con
  `reserva_mostrador`), `carrito` (se crea contra un `comercio_id`), `pedido.comercio`, `horarios`,
  `abierto_ahora`, `ubicacion.zona_entrega`, `modalidades`, `medios_cobro`,
  `privado.cuenta_cobro`, `cobradores`, `envios`, `equipo`, `reputacion`, cumplimiento
  (`docs/ranking-y-despacho.md`), métricas y fidelidad.
- `PUT /comercios/{id}/stock` (`actualizarStock`) ya es el lote pensado para "supermercados con
  sistema": por `oferta_id` (y `variante_id`) se pisan `stock`, `disponible` y `precio_centavos`. Es
  justo lo que una sucursal necesita pisar sobre un catálogo común.
- `lista.json` ya resuelve ítems genéricos (EAN, catálogo maestro, texto) contra un comercio al
  pedir. Es el mismo patrón de "resolver contra quién" que usaría el ruteo de la opción C.
- El despacho sale de `ubicacion.direccion` del comercio: el repartidor retira donde está el local.

Conclusión: el modelo actual ya es "cada local es un comercio". Falta la capa de marca: agrupar,
compartir catálogo y, opcionalmente, rutear.

## 2. Cómo lo resuelve el mercado

| Plataforma | ¿Cada local es un listado? | ¿Quién elige el local? | Stock / precio por local | ¿Divide pedidos? |
| --- | --- | --- | --- | --- |
| Rappi, PedidosYa, iFood, Uber Eats | Sí: cada local es una tienda con su id | El comprador, entre los que llegan a su dirección | Sí, por tienda (catálogo y disponibilidad por `store_id` / `merchantId`) | No |
| DoorDash (retail) | Business con catálogo común, Stores con inventario | El comprador, por dirección | Sí: stock y precio por store | No |
| Instacart | Retailer (marca) y tienda | El comprador, por dirección; en retiro elige el local | Sí: precio, disponible y anticipación por tienda | No: varias tiendas son varios carritos |
| Shopify | Una tienda, varias Locations | Ruteo automático (cercanía, menos divisiones, prioridad); en retiro elige el comprador | Stock por location; precio por producto/mercado | Sí |
| Tiendanube | Una tienda, varios centros de distribución | El comercio (asigna centros a productos) | Stock por location (`inventory_levels`, con `priority`) | No documentado |
| Mercado Libre (multi-origen) | Una publicación; el stock se suma | ML automático (por stock y logística) | Stock por depósito; precio por publicación | No documentado |
| Google (inventario local) | Producto + `store_code` | El comprador, por cercanía | Stock y precio por local (pisan el feed) | No aplica |

Lectura:

1. **Delivery de comida y almacén (lo más parecido a Vereda hoy): cada local es una tienda.** La
   cadena existe para administrar (una API key, un tablero con todos los locales, pausa global), no
   para comprar. Las calificaciones son por tienda (Uber Eats lo confirma).
2. **Retail/grocery: catálogo común, stock y precio por local.** El comprador elige por dirección, o
   el local si retira. Varias tiendas son varios carritos, no un pedido dividido.
3. **E-commerce: una tienda, el comercio rutea.** Tiene sentido cuando se envía por correo y el
   origen da casi igual. Dividir pedidos es de Shopify y trae costos (dos envíos, dos seguimientos).
4. **Casi nadie divide un pedido entre locales para entrega en el día.** Donde hay división es
   logística de paquetería.

Fuentes:
- Rappi, stock por tienda: https://dev-portal.rappi.com/en/managing-availability-rests-api/ · https://dev-portal.rappi.com/en/api-reference/stores/
- PedidosYa, cadenas y catálogo por vendor: https://developer.pedidosya.com/en/documentation/introduction · https://developer.pedidosya.com/en/documentation/catalog-api-overview
- iFood, catálogo por merchant: https://developer.ifood.com.br/en-US/docs/guides/catalog/v2/ · https://developer.ifood.com.br/en-US/docs/guides/modules/merchant/workflow/
- Uber Eats, varios locales y reseñas por tienda: https://help.uber.com/merchants-and-restaurants/article/adding-multiple-locations-to-restaurant-manager-/?nodeId=ccd696ac-6e06-4951-9cf8-70005bdd912e · https://help.uber.com/en/merchants-and-restaurants/article/how-can-i-view-customer-reviews-and-feedback-in-uber-eats-manager?nodeId=25a280eb-2e90-4124-b52d-c79a83263ba1 · https://developer.uber.com/docs/eats/guides/store-integration
- DoorDash, Business / Store / Catalog / Inventory: https://developer.doordash.com/en-US/docs/marketplace/retail/store_management/overview/
- Instacart, tienda por dirección, varias tiendas, precio y stock por tienda: https://www.instacart.com/help/section/809794019/648593957 · https://www.instacart.com/help/section/2893565984/2936616438 · https://docs.instacart.com/catalog/catalog_api/item/overview/
- Shopify, locations, ruteo y división: https://help.shopify.com/en/manual/fulfillment/setup/locations · https://help.shopify.com/en/manual/fulfillment/setup/order-routing/understanding-order-routing · https://help.shopify.com/en/manual/fulfillment/setup/locations/fulfillment · https://help.shopify.com/en/manual/fulfillment/setup/delivery-methods/pickup-in-store
- Tiendanube, multi-inventario: https://tiendanube.github.io/api-documentation/multi-inventory-guides · https://ayuda.tiendanube.com/es_MX/centros-de-distribucion/como-configurar-multiples-centros-de-distribucion-en-mi-tiendanube
- Mercado Libre, stock multi-origen: https://developers.mercadolibre.com.ar/es_ar/stock-multi-origen · https://developers.mercadolibre.com.ar/en_us/product-identifiers/full-and-flex-coexistence
- Google, inventario local: https://support.google.com/merchants/answer/14819809 · https://support.google.com/merchants/answer/13869896

Sin confirmar con fuente primaria: el ruteo entre locales de Rappi y PedidosYa, cómo cuelgan las
reseñas en PedidosYa, iFood y DoorDash, y si Shopify o ML tienen precio por local. Algunas páginas
de ML y DoorDash respondieron 403 y se leyeron por el resumen del buscador.

## 3. Qué tiene que respetar cualquier opción

- **Sin gatekeeper.** Nadie aprueba una sucursal. Lo único que el nodo exige es que el vínculo sea
  cierto: la misma dueña, o que el padre lo acepte.
- **La política es del comercio y es pública.** Si hay ruteo, la regla la elige la marca, sale en
  su ficha y el protocolo sugiere un default sin imponerlo.
- **API y MCP primero.** Todo sale como operación y como herramienta MCP; las apps pintan.
- **Efectivo y P2P.** La plata va del comprador a una cuenta del comercio, sin pasar por Vereda. El
  modelo tiene que decir **a qué cuenta** va cuando hay varias sucursales.
- **Reputación de pedidos entregados.** Una reseña es de un pedido, y el pedido es de quien lo
  preparó y lo entregó.
- **Federable.** Una sucursal podría vivir en otro nodo más adelante, así que el vínculo se
  referencia por identidad (`actor@nodo`) y no por id interno.
- **Simple para Santa Elena.** Tiene que salir con lo que ya existe más poco.

## 4. Opciones

### Opción A: cada sucursal es un comercio (con marca y catálogo compartido)

Es el modelo de Rappi, PedidosYa, iFood, Uber Eats y DoorDash, y es el que el protocolo ya tiene a
medias.

**Modelo de datos**

- `comercio.sucursal_de`: pasa a ser la **identidad** del padre (`actor@nodo`), no un id. El nodo lo
  acepta solo si quien lo escribe administra los dos (la dueña, o un miembro con `datos` en ambos);
  si no, `403 sin_permiso`. En federación, el padre lo confirma listando la sucursal (abajo).
- Padre (la "casa"): un comercio común. Suma `sucursales` (readOnly, lo calcula el nodo:
  identidades, nombre corto y ubicación de cada una). Si la casa no vende al público, lo dice con
  `vende: false` (campo nuevo, default `true`): no aparece en `buscarComercios` como tienda, solo como
  ficha de marca. Opcional para el primer corte: alcanza con que la casa central sea una sucursal más.
- Sucursal: `nombre_sucursal` opcional ("Caballito", "Depósito Warnes"). Las apps muestran
  "Santa Elena · Caballito".
- **Catálogo heredado** (lo que evita cargar 2.000 productos N veces): `catalogo_de` en la
  sucursal, con la identidad de la casa. Las ofertas de la casa aparecen en la sucursal con el
  `comercio_id` de la sucursal y el mismo `id` de oferta. La sucursal pisa por oferta solo `stock`,
  `disponible` y, si quiere, `precio`, con el `actualizarStock` que ya existe. Sin fila propia, rige lo
  de la casa, salvo el stock numérico, que por default es 0 en la sucursal (no se hereda stock de otro
  local). Una sucursal puede además tener ofertas propias.

**Quien compra**

- `buscarComercios` en un punto trae las sucursales que llegan ahí, cada una con su distancia,
  horario, stock, envío y reputación. Default recomendado en las apps: **una tarjeta por marca**, con la
  sucursal que mejor rankea para ese punto, y "3 sucursales más" desplegable. Se agrega
  `agrupar=marca` a `buscarComercios` y `buscarOfertas` para que el nodo lo haga igual para agentes y
  apps.
- `buscarOfertas` ("aceite girasol 5 L cerca") trae la oferta de la sucursal con stock más cercana,
  con "también en Caballito (a 2,1 km)".
- El carrito es de una sucursal, como hoy. Si falta algo, la app ofrece "en la sucursal X lo tienen";
  cambiar de sucursal traslada el carrito (misma oferta, mismo id) y revalida stock y precio.
- La ficha de marca (la casa) muestra las sucursales en un mapa, con abierto/cerrado y la
  reputación de cada una.

**El comercio**

- Da de alta la casa y luego cada sucursal con `sucursal_de` (y `catalogo_de` si comparte catálogo).
  Por MCP: `comercio_crear` con esos campos, más `sucursales_ver`.
- Carga el catálogo una vez en la casa y cada sucursal (o su sistema) manda el stock por
  `actualizarStock`. Un distribuidor con sistema hace un PUT por sucursal cada N minutos.
- Equipo: cada sucursal tiene el suyo (encargado por local, que es lo natural). La dueña es la misma
  identidad en todas. Más adelante: un miembro de la casa con alcance `todas_las_sucursales`, para no
  invitar N veces.

**Carrito, pedido, pago, reseñas**

- Carrito, reserva, pedido, despacho, cumplimiento y cancelación: por sucursal, sin cambios.
- Cobro: cada sucursal declara su `privado.cuenta_cobro` y sus `cobradores`. Pueden ser la misma
  cuenta. **Ojo, bug latente:** los centavos y la referencia únicos se calculan "por destinatario". Si
  varias sucursales comparten alias y "destinatario" es el comercio, dos pedidos de dos sucursales
  pueden pedir el mismo monto a la misma cuenta. Hay que definir la unicidad **por cuenta de cobro**
  (hash del alias), no por comercio. Lo mismo con la fidelidad: puntos por sucursal, o `fidelidad_de`
  la casa para compartir saldo (más adelante).
- Reseñas y reputación: por sucursal, porque es quien entregó. La ficha de marca muestra un agregado
  (suma de las reseñas de las sucursales con la misma fórmula) marcado como "de la marca", y nunca
  esconde la de cada una. Ya está resuelto que no se reseñan entre ellas (vinculadas por dueño).

**Pros**

- Casi todo ya funciona: carrito, reserva, pedido, despacho desde el local correcto, efectivo,
  transferencia, cumplimiento y reseñas por quien de verdad atendió.
- Es lo que el comprador argentino ya conoce de Rappi y PedidosYa.
- Cada sucursal tiene horarios, zona, envíos y política propios, sin inventar un "depósito" con
  medio comercio adentro.
- Federa: una sucursal es un actor más.

**Contras**

- Sin agrupación, el buscador muestra la misma marca 5 veces (se resuelve con `agrupar=marca`).
- Si la casa central tiene lo que el local cercano no, el comprador tiene que cambiar de sucursal a
  mano (o la app se lo sugiere).
- Herencia de catálogo: el nodo tiene que componer "oferta de la casa + fila de la sucursal" al
  leer. Es el cambio más grande de esta opción.

**Complejidad:** nodo baja a media (validar el vínculo, listar sucursales, agrupar, herencia de
catálogo); apps baja (agrupar tarjetas, ficha de marca, "cambiar de sucursal").

### Opción B: un comercio con varios puntos de despacho (modelo Shopify / Tiendanube / ML)

La marca es el comercio; las sucursales son `puntos` dentro de él.

**Modelo de datos**

- `comercio.puntos[]`: `{ id, nombre, direccion, zona_entrega, horarios, apertura_manual, modalidades? }`.
  `ubicacion` y `horarios` del comercio pasan a ser la unión o el default.
- `oferta.stock.por_punto`: `{ punto_id: cantidad }`. `disponible` se calcula por punto.
- `comercio.ruteo`: `{ modo: "cercano_con_todo" | "prioridad" | "elige_comprador" | "manual", prioridad?: [punto_id] }`,
  público. Default recomendado: `cercano_con_todo` (el punto más cercano que tiene todo el carrito;
  si ninguno, el más cercano y se marcan faltantes).
- `carrito.punto_id` (propuesto por el nodo, cambiable si el comercio deja elegir) y
  `pedido.punto_id` (congelado al crear; el comercio lo puede reasignar antes de aceptar, con evento
  `pedido.punto_cambiado`).
- `actualizarStock` suma `punto_id` por fila.

**Quien compra:** ve un solo Santa Elena, un catálogo, una reputación. Al confirmar ve "Sale de la
sucursal Caballito" (en retiro elige el punto). No tiene que saber nada de sucursales.

**El comercio:** un solo catálogo, un solo equipo, una sola bandeja con filtro por punto; decide el
ruteo.

**Carrito, pedido, pago, reseñas:** un cobro y una cuenta, un solo destinatario. La reputación es de
la marca: una sucursal mala se diluye en el promedio. El despacho tiene que salir de
`pedido.punto_id` y no de `comercio.ubicacion`. El cumplimiento es de la marca.

**Pros:** es la mejor experiencia de "le compro a Santa Elena" y la herramienta más cómoda para una
distribuidora con un solo sistema de stock.

**Contras:**

- Toca medio protocolo: zona de entrega, `abierto_ahora`, `buscarComercios` por punto, despacho,
  ETA, modalidades por punto, reserva por punto, permisos de equipo por punto (el encargado de
  Caballito no debería ver Warnes), métricas por punto.
- Esconde a quien entrega de verdad: la reseña de un pedido de Caballito le baja el puntaje a Warnes.
  Es opaco para el comprador y choca con "reputación de quien entregó".
- Ruteo automático = el nodo decide por el comercio. Si la regla es pública y elegida por el
  comercio, pasa; pero es lógica nueva que cada nodo tiene que implementar igual (suite de
  conformidad).
- Dos formas de modelar lo mismo si convive con `sucursal_de`.

**Complejidad:** nodo alta; apps media (casi nada visible, pero reescribir checkout y bandeja con
puntos).

### Opción C: sucursales como comercios más un carrito "a la marca" con ruteo (híbrida)

Es A más una puerta de entrada tipo B, sin meter depósitos dentro del comercio.

**Modelo de datos:** todo lo de A, más:

- En la casa, `ruteo`: `{ modo: "cercana_con_todo" | "cercana" | "prioridad" | "elige_comprador", prioridad?: [identidad] }`,
  público en la ficha. Default recomendado: `elige_comprador` en retiro y `cercana_con_todo` con
  envío.
- `POST /carritos` acepta `marca` (identidad de la casa) en lugar de `comercio_id`, con `direccion` o
  `modalidad: retiro`. El nodo aplica la regla pública, elige la sucursal y el carrito nace de esa
  sucursal, con `ruteado_por: { marca, modo, motivo }` para que se vea por qué. Mientras se arma, si un
  ítem no está en esa sucursal y sí en otra que cumple la regla, el carrito responde
  `no_disponible` con `faltantes[].en_sucursal` ("en Caballito sí hay") y la app o el agente
  decide si mudarse.
- El pedido sigue siendo de una sucursal. Nada de pedidos divididos: si hace falta de dos locales,
  son dos carritos (como Instacart).

**Quien compra:** "Pedile a Santa Elena". La app o el agente muestran la marca; al elegir productos
el nodo ya asignó sucursal, y el checkout dice "Te lo manda Santa Elena Caballito". En retiro
elige el local en un mapa.

**El comercio:** lo de A, más elegir la regla de ruteo en la ficha de la casa.

**Carrito, pedido, pago, reseñas:** como A. El ruteo solo decide **a qué comercio** se le arma el
carrito; después es un pedido normal. Pago a la cuenta de la sucursal (o la misma cuenta de todas),
reseña a la sucursal y agregado de marca a la vista.

**Pros:** la experiencia de B ("le compro a la marca") con la contabilidad de A (cada pedido de
quien lo entrega). El ruteo es una capa fina, opcional y pública, sin tocar reserva, despacho ni
reputación. Encaja con el patrón de `lista.json` (resolver contra un comercio al pedir).

**Contras:** es A más una operación nueva; el ruteo con stock ("cercana_con_todo") tiene que mirar el
stock de N sucursales al crear el carrito. No resuelve el pedido dividido (a propósito).

**Complejidad:** nodo media (A más resolver la regla al crear el carrito); apps baja (entrada por
marca, "te lo manda X", "mudarse de sucursal").

## 5. Comparación rápida

| | A: sucursal = comercio | B: puntos dentro del comercio | C: A + carrito a la marca |
| --- | --- | --- | --- |
| Cambios en esquemas | Pocos (`sucursal_de`, `catalogo_de`, `nombre_sucursal`) | Muchos (puntos, stock por punto, ruteo, pedido) | A + `ruteo`, `marca` en carrito |
| Quien compra ve | Marca agrupada, elige sucursal (o la cercana) | Solo la marca | La marca; el nodo asigna sucursal |
| Stock por local | Sí, stock propio de cada comercio | Sí, `por_punto` | Sí, como A |
| Reputación | Por sucursal + agregado de marca | Solo marca | Por sucursal + agregado de marca |
| Pagos | Cuenta por sucursal (puede repetirse) | Una cuenta | Como A |
| Equipo | Por sucursal (natural) | Requiere permisos por punto | Como A |
| Federación | Gratis | Todos los puntos en un nodo | Gratis |
| Riesgo de encerrarnos | Bajo | Alto (difícil volver atrás) | Bajo |

## 6. Recomendación

**C como destino, construido por partes, arrancando por A.** Motivos:

- El protocolo ya piensa en comercio por local y lo usa en todas partes: carrito, reserva, despacho,
  cobro P2P, cumplimiento, reseñas. B rompe esa unidad para ganar una experiencia que C consigue con
  una capa fina.
- La reputación sigue siendo de quien entregó, que es el principio. La marca se ve como agregado,
  nunca como reemplazo.
- El ruteo, cuando llegue, es política pública de la marca con un default sugerido, no un algoritmo
  del nodo. Y queda en su propio documento, como `ranking-y-despacho.md`.
- Lo que el mercado hace en delivery en el día (Rappi, PedidosYa, iFood, Uber Eats, DoorDash e
  Instacart) es A; el ruteo automático tipo Shopify o ML es de paquetería.
- No dividir pedidos: nadie lo hace para entrega en el día y complica pago, efectivo y reseñas.

## 7. Primer corte para que Santa Elena salga ya

Objetivo: vender con stock por sucursal esta semana, sin decisiones que después haya que deshacer.

1. **Cada sucursal es un comercio** con la misma dueña, `sucursal_de` apuntando a la casa central y
   `nombre_sucursal`. La casa central es también una sucursal que vende (sin `vende: false` todavía).
2. **El nodo valida `sucursal_de`**: la misma dueña en los dos, si no `403`. Escribe `sucursales`
   (readOnly) en la ficha de la casa. `GET /comercios/{id}/sucursales` y herramienta MCP
   `sucursales_ver`.
3. **`agrupar=marca` en `buscarComercios`** (y en `buscarOfertas` si entra): una sucursal por marca,
   la mejor según el orden pedido, y `otras_sucursales: n`. Las apps muestran "Santa Elena ·
   Caballito" y "3 sucursales más".
4. **Catálogo: sin herencia todavía.** Santa Elena tiene sistema: carga el mismo catálogo en cada
   sucursal por API (`crearOferta` en lote o un script de carga) y manda stock y precio por
   `actualizarStock` a cada una. Para no encerrarnos, las ofertas de las sucursales llevan el **mismo
   `ean` o una clave externa común** (`atributos.sku` o un campo `sku` nuevo), así después la
   herencia (`catalogo_de`) es una migración y no un rediseño.
5. **Cobro:** si todas las sucursales comparten alias, arreglar la unicidad de centavos y referencia
   para que sea **por cuenta de cobro** y no por comercio. Es un cambio chico en el nodo y conviene
   hacerlo antes de que salga, porque si no dos pedidos de dos sucursales pueden pedir el mismo monto
   a la misma cuenta.
6. **Reputación:** por sucursal, sin agregado de marca todavía. Las apps muestran la de la sucursal.
7. **Nada de ruteo ni pedidos divididos.** Quien compra ve la sucursal más cercana que le llega y
   puede elegir otra.

Queda para después, en este orden: herencia de catálogo (`catalogo_de`), reputación agregada en la
ficha de marca, miembro de equipo con alcance a todas las sucursales, `vende: false` para una casa
que solo es marca, carrito a la marca con `ruteo` (opción C) y, al final, `fidelidad_de`.

## 8. Preguntas abiertas para Santa Elena

- ¿Cuántas sucursales y cuántos productos? ¿El precio cambia por sucursal o es lista única?
- ¿Venden a consumidor final, a almacenes (mayorista) o a los dos? Si es mayorista, pesan más los
  mínimos de compra, `consolidada` y `franja` que la cercanía.
- ¿Una sola cuenta de cobro (un CUIT) o una por sucursal?
- ¿Su sistema puede empujar stock por sucursal cada N minutos? ¿Con qué identificador de producto?
- ¿Cada sucursal reparte con su gente, o hay un depósito que reparte para todas? Si reparte uno solo,
  ese depósito es el comercio y las otras sucursales son solo para retiro, y el diseño cambia poco:
  la sucursal de retiro es otro comercio con solo `retiro`.
