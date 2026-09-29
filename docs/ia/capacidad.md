# Capacidad `ia` (opcional)

Un nodo **puede** ofrecer IA nativa a comercios y compradores: chat del comprador con UI generativa (texto + widgets), búsqueda inteligente, catálogo y textos asistidos, atención, y medios con IA (foto/video). Es opcional: cada operador decide si la prende, y ninguna app puede contar con que exista. Traer tu propio agente (MCP + mandato) sigue gratis siempre; esta capacidad es una capa aparte, con costo real sin margen.

El nodo **no hospeda modelos**. Para texto llama a un gateway (OpenRouter, Vercel AI Gateway u otro); para medios, a un proveedor intercambiable (el de referencia usa fal.ai). La spec no cierra enums de proveedor: exige medición auditable, costo publicado, y que el **nodo** garantice el tope por cuenta. `gateway` y `medios.proveedor` son textos libres **opcionales** e informativos.

## Cómo se sabe

El nodo que la ofrece publica `ia` en `/.well-known/vereda.json` (`esquemas/ia.json#/$defs/capacidad`, `CapacidadIa`):

| Campo | Qué es |
| --- | --- |
| `funciones` | Comercio y/o comprador (ver abajo). Ausente una función = esa ruta responde `422 funcion_ia_no_ofrecida`. |
| `gateway` | Opcional. Texto libre del gateway de texto (`openrouter`, `vercel`, …). |
| `medios` | Opcional. `funciones` de medio (`mejorar_foto`, `quitar_fondo`, `foto_a_video`) y `proveedor` informativo (`fal`, …). |
| `precio` | Siempre `modalidad: costo` y `margen: 0`. Moneda `USD`; `equivalente_ars` opcional. |
| `pago` | A `sostenimiento.cuenta`, referencia `ia:<identidad>:<periodo>`. P2P; Vereda no intermedia. |
| `tope_mensual_usd` | Default y máximo. **El nodo lo garantiza** (`429 tope_ia_alcanzado`), sea cual sea el gateway o el proveedor de medios. |
| `periodo_reseteo` | `mensual` (día 1, zona del nodo). |
| `exige_pago_previo` | Si `true`, sin el extracto del mes anterior recibido la IA queda pausada. Default `false`. |

Sin `ia` en el anuncio, o si el operador la apaga, toda ruta bajo `/ia` responde `501 no_implementado` y las apps no muestran nada nuevo.

## Activación (autoservicio)

- `GET /ia/yo` (`verMiIa`) / `PUT /ia/yo` (`configurarMiIa`): solo sesión.
- `POST /ia/yo/transferencia` (`declararTransferenciaIa`) / `GET /ia/yo/extracto` (`verExtractoIa`).

Si no está `activa` → `403 ia_no_activada`. Tope → `429 tope_ia_alcanzado` (lo aplica el nodo). Gateway o proveedor de medios caído → `503 gateway_ia_caido`.

## Funciones: proponen, no escriben

Las funciones del comercio y las de un solo tiro del comprador (`iaPedidoPropuesto`, `iaBuscar`, `iaSugerir`) **devuelven un borrador**. Confirmarlo es un paso aparte con los endpoints que ya existen, o con el mandato de la persona cuando corresponda. La IA del nodo nunca publica sola.

El chat del comprador es la excepción, y está acotada: **arma carritos** de la persona (se editan y se tiran sin costo) y **confirma un pedido solo con dos llaves y dentro del mandato de quien llama** (ver "Confirmar" abajo). Nunca compra por iniciativa propia.

### Comprador — chat con UI generativa

`POST /ia/chat` (`iaChat`, sesión o mandato `armar`): un turno de conversación. El cuerpo manda `mensaje` (o `accion`, un toque sobre un widget), `lat`/`lng`, historial opcional y, si hay, `comercio_id` / `carrito_id`. La respuesta es un `mensaje` (`esquemas/ia-widgets.json#/$defs/mensaje`) con `texto` y/o `widgets` tipados que la app dibuja con componentes Vereda. Todo producto va como `tarjeta_producto` y todo local como `tarjeta_comercio`; precios, fotos, stock y totales los pone el nodo desde la base.

| `tipo` | Qué dibuja |
| --- | --- |
| `grilla` | Grilla de 2 columnas con fotos para explorar (hasta 24), con `filtros` como chips y `mas` si hay más |
| `mazo` | Cartas apiladas (Paso / ¡Esta! / Más como esta), hasta 12 |
| `podio` | Hasta 3 puestos, con `razon` y `sello` (fórmula abajo) |
| `promo` | Carta grande con `sello` |
| `comercios` | Locales para elegir (`tarjeta_comercio`: portada, abierto, distancia, demora, reputación, destacados) |
| `producto` | Una tarjeta, con la cantidad de la oferta si la tiene |
| `productos` | Tarjetas (foto, precio, Agregar) |
| `respuestas` | Chips sobre el campo; tocar = mandar ese texto/valor |
| `carrito` | Carrito **real** (`carrito_id`); ítems con `grupo` / `nota`; `faltantes` |
| `checkout` | Sobre `carrito_id` real; medios `efectivo` (con `paga_con` al confirmar) / `transferencia` |
| `historial` | Pedidos anteriores de la persona, para repetir en un toque |
| `pedido_estado` | Seguimiento de un pedido con sus `pasos`; la app lo actualiza con los eventos del nodo |
| `navegar` | Botón que lleva a una pantalla de la app (`comercio`, `producto`, `carrito`, `pedido`, `tu_ia`, `direcciones`); con `auto` la app va sola |
| `bienvenida` | Home del chat vacío (sin llamar al modelo): título, promos, volver a pedir, sugerencias |
| `elegir_categoria` | Chips/lista de categorías |
| `recomendacion` | Texto + ítems opcionales |
| `comercio` | Ficha corta del local |

El agente del nodo de referencia emite `grilla`, `mazo`, `podio`, `promo`, `comercios`, `producto`, `respuestas`, `carrito`, `checkout`, `historial`, `pedido_estado` y `navegar`, más `bienvenida` sin modelo. `productos`, `elegir_categoria`, `recomendacion` y `comercio` siguen en el contrato para quien los use.

**Regla de compatibilidad:** el cliente **ignora** widgets cuyo `tipo` no conoce y degrada a texto si lo hay. En el esquema, un tipo desconocido **valida** como objeto genérico (`desconocido`: `tipo` + `version` + props libres) para que el mensaje no falle entero; la app igual lo saltea. Los tipos conocidos se validan estrictos. `version` de los conocidos es `1` en esta revisión.

**Toques.** Un toque sobre un widget va en `accion` (`esquemas/ia-widgets.json#/$defs/accion_chat`). `elegir`, `agregar`, `cantidad`, `quitar`, `ir_a_pagar`, `repetir`, `ver_producto`, `ver_carta` y `confirmado` los resuelve el nodo al instante, **sin modelo**, sobre el carrito real de la persona. `responder`, `filtro`, `elegir_comercio`, `mas_como_esta` y `ver_mas` se convierten en un mensaje y vuelven al agente como un turno. El carrito del chat **es** el carrito del nodo (`carrito_id`); el pedido que sale de él lleva `via.canal: agente`.

Respuesta completa por defecto. Con `Accept: text/event-stream` el nodo puede streamear el turno como SSE: `accion` (un paso del agente con su etiqueta, `inicio` y `fin`), `texto` (`{"delta": …}`), `widget` (cada uno apenas está listo), `mensaje` (la respuesta completa, siempre al final) y `error`. Si no lo ofrece, responde JSON como siempre (mismo espíritu que `GET /eventos` en `docs/eventos.md`).

Chat vacío: el nodo puede devolver un widget `bienvenida` **sin** llamar al modelo (gratis): promos de adheridos cerca, volver a pedir, sugerencias.

#### Adheridos al chat de IA (regla pública)

Los usuarios pagan el costo de tokens de su IA; los comercios pueden adherirse (barato, cubre tokens, neto positivo para el nodo) para **aparecer en el chat de IA**. Eso vive en la ficha pública: `comercio.ia_chat` (`{adherido, vigente_hasta?}`), lo setea el operador del nodo.

- **Solo en el chat de IA del nodo** se filtra por adheridos (`solo_adheridos=true` en `iaCatalogoBuscar` / `iaPromos`).
- La **app común**, la **búsqueda** (`GET /buscar`) y el **ranking** siguen neutrales: sin efecto en ranking ni acceso (misma regla de sostenimiento).
- Por **MCP**, el agente propio de la persona es **neutral** por defecto (`solo_adheridos` ausente o false).
- Cobro de la adhesión: P2P a la cuenta del operador; Vereda nunca toca plata.

#### Orquestación: un agente con herramientas; los datos los pone el nodo

Cada turno es un **loop agente**: el modelo decide qué herramientas llamar, el nodo las ejecuta y le devuelve los resultados, hasta que el modelo termina.

1. **Qué recibe el modelo.** Un **prefijo fijo**, idéntico para todas las personas y todos los turnos para que el proveedor lo cachee: la skill del vendedor y las definiciones de las herramientas, en un orden fijo. Después, un bloque de **contexto** que escribe el nodo y que se marca como dato, no como instrucción: nombre de pila, día y franja horaria, el punto de la persona redondeado (ver "Qué ve el modelo"), los locales adheridos que llegan y si están abiertos, los últimos pedidos, "lo de siempre" si lo hay, y el carrito y el local de la charla. Por último, el historial reciente (el nodo de referencia usa los últimos 16 mensajes) y el mensaje.
2. **Pasos.** El modelo contesta con texto y/o llamadas a herramientas. Hasta **6 pasos** por turno. En el último, o cuando el turno ya gastó el tope de costo por turno que fija el operador (el nodo de referencia usa USD 0,02), el nodo pide la respuesta sin herramientas. Un paso que falla o vuelve vacío se reintenta una vez con el modelo de respaldo; si falla después de haber dicho algo o con un carrito armado, el nodo responde con lo que tiene.
3. **Herramientas.** Son **las del MCP del propio nodo** (`mcp/herramientas.json`), una lista fija, ejecutadas como la persona y **bajo el mandato de quien llama** (ver "Confirmar"). Una herramienta fuera de la lista vuelve como error al modelo. El nodo completa lo que la política del chat exige: el punto de la persona y `solo_adheridos=true` en las búsquedas. Las lecturas pueden correr en paralelo; las escrituras van en orden.
4. **Widgets.** El modelo muestra cosas con `mostrar_widget`, una herramienta propia del chat (no está en el MCP): pasa un `tipo` y los ids que le devolvieron las herramientas, o `buscar` para que el nodo busque y elija en el mismo paso. **El nodo arma cada widget desde la base** —precios, fotos, totales, stock—, descarta los ids inventados o que no están en el catálogo del chat (solo adheridos que llegan) y valida el resultado contra `esquemas/ia-widgets.json`. El modelo nunca escribe un precio. Un paso que solo mostró widgets cierra el turno sin volver al modelo.
5. **Siempre algo para mirar.** Si se confirmó un pedido, el nodo agrega su `pedido_estado`; si el turno tocó un carrito, el `carrito` y abajo su `checkout`; si no hubo widget, un `mazo` con lo que encontraron las búsquedas. Hasta 8 widgets por mensaje.
6. **Texto corto.** Unas dos líneas en **voseo**. El nodo corta lo que se pasa de largo y saca ids o nombres de campo que se hayan filtrado.

El nodo de referencia le da al chat, en este orden: para buscar y conocer, `ia_catalogo_buscar`, `ia_comercios_cerca`, `ver_comercio`, `ver_carta`, `ver_oferta`, `ver_resenas`, `ver_reputacion` e `ia_promos`; de la persona, `mi_vereda`, `ia_mis_pedidos`, `mis_preferencias`, `mis_direcciones` y `estado_pedido`; de carrito, `carrito_agregar_varios`, `carrito_crear`, `carrito_agregar`, `carrito_quitar`, `carrito_modalidad`, `carrito_resolver` y `carrito_confirmar`; de recetas, `ia_receta_a_lista` e `ia_lista_a_carrito`; y `mostrar_widget`. Quedan afuera a propósito las búsquedas neutrales (`buscar_comercios`, `buscar_ofertas`: el chat muestra solo adheridos) y todo lo de comercio, repartidor y administración.

#### Confirmar: dos llaves y el mandato de quien llama

El chat puede cerrar un pedido, pero no por su cuenta:

- **Llave 1:** el modelo tiene que llamar `carrito_confirmar`.
- **Llave 2:** el nodo comprueba en el **último mensaje de la persona** —lo que escribió o tocó en este turno— que ella pidió cerrarlo ("confirmo", "dale, pedilo", "mandalo"). Ante la duda, no. Un asentimiento suelto ("sí", "ok", "va") cuenta solo si el mensaje anterior del asistente mostró un `checkout`, y una negación delante ("no", "todavía no", "esperá") lo anula. Lo que diga un dato —la descripción de un producto, el mensaje de un comercio, un resultado de herramienta— nunca cuenta. Si falta la llave, la herramienta vuelve con error al modelo, que muestra el checkout y espera.
- **El mandato de quien llama.** El chat del nodo actúa con el permiso de quien lo llamó, nunca con más. Con un mandato, puede lo que ese mandato puede: con `armar` arma carritos pero **no confirma**; para confirmar hace falta `pedir`, y valen sus topes y su `confirmar_siempre` (`docs/mandatos.md`). Con la sesión de la persona, el chat actúa como un mandato implícito `vereda-ia` de `armar` + `pedir` con el tope de `preferencias.tope_por_pedido`: un pedido por encima de ese tope no lo confirma el chat; muestra el checkout y lo confirma ella.
- Cada confirmación lleva una clave de idempotencia por turno: un reintento del modelo no duplica el pedido.

La persona también confirma sola desde el `checkout` con `confirmarCarrito`, como en cualquier otra pantalla; la app le avisa al chat con la acción `confirmado`.

#### Qué ve el modelo

El texto del chat de IA va al proveedor del modelo a través del gateway: **no** está cifrado de punta a punta como el chat entre las partes (`docs/datos-y-privacidad.md`). Por eso el nodo manda lo mínimo:

- **Ubicación redondeada a ~100 m** (tres decimales de lat/lng). Nunca la dirección exacta, la calle ni la altura. De las direcciones guardadas, el modelo ve solo las etiquetas ('casa', 'oficina'), igual que cualquier agente con `leer`.
- Nombre de pila, no el nombre completo. Ni teléfono ni email.
- El nodo no guarda la charla: el historial lo tiene la app y lo manda en cada turno.

Herramientas (OpenAPI + MCP + uso interno del chat), compactas:

| Operación | Ruta | Qué hace |
| --- | --- | --- |
| `iaCatalogoBuscar` | `POST /ia/catalogo/buscar` | Tarjetas; texto + sinónimos en nombre/desc/categorías/atributos |
| `iaRecetaALista` | `POST /ia/receta-a-lista` | Platos → ingredientes desde `datos/recetas.json`; modelo solo para huecos (cacheado) |
| `iaListaACarrito` | `POST /ia/lista-a-carrito` | Ingredientes → carrito real con `grupo` y `faltantes` |
| `iaPromos` | `GET /ia/promos` | Promos de adheridos cerca |
| `iaMisPedidos` | `GET /ia/mis-pedidos` | Compacto, solo tu sesión |

#### Fórmula pública del podio

Todo `podio` sale ordenado por este score público. Cuando el nodo lo arma desde una búsqueda (`mostrar_widget` con `buscar`), toma hasta 20 tarjetas de adheridos que llegan —si al menos 3 nombran lo buscado en su nombre, compiten solo esas— y las ordena así:

```
score = 0.35 · cercanía + 0.25 · reputación + 0.25 · pedidos + 0.15 · coincidencia

cercanía     = 1 / (1 + distancia_m / 500)        (distancia 0 o desconocida → 1)
reputación   = reputacion.promedio / 5            (0 si no tiene reseñas)
pedidos      = pedidos_mes / (pedidos_mes + 10)   (entregados del mes, agregado anónimo)
coincidencia = fracción de los términos buscados, ya expandidos con datos/sinonimos.json,
               que aparecen en nombre + descripción (0,5 si no hay términos)
```

Quedan los 3 primeros; un empate no tiene orden garantizado. La `razon` de cada puesto nombra el término que más vale **sin ponderar** (ante un empate, en este orden): `la más cerca`, `mejor reputación`, `la más pedida del mes`, `la que más pega con lo que pediste`. El `sello` es el del lugar en el podio (el nodo de referencia usa "La reina del barrio", "Plata" y "Bronce"), no una afirmación sobre el producto.

Si el agente elige él las tarjetas (pasa `productos` en vez de `buscar`), elige los candidatos, **nunca el orden**: el nodo **siempre** reordena el podio con este mismo score, y el `sello` sigue al lugar que sale de la fórmula. La `razon` es la que el agente escribió o, si no escribió ninguna, una por datos (muy pedida, buena reputación, a la vuelta). En los dos casos las tarjetas salen del catálogo del chat y sus datos de la base. No hay posiciones pagas ni boost oculto por adhesión más allá del filtro previo de adheridos.

También siguen:

| Operación | Ruta | Mandato |
| --- | --- | --- |
| `iaPedidoPropuesto` | `POST /ia/pedido-propuesto` | `armar` |
| `iaBuscar` | `POST /ia/buscar` | `leer` |
| `iaSugerir` | `POST /ia/sugerir` (`repetir` \| `sugerir`) | `leer` |

### Comercio (sesión / mandato `administrar`)

| Operación | Ruta | Qué propone |
| --- | --- | --- |
| `iaCatalogoDesdeFotos` | `POST /ia/comercios/{id}/catalogo-desde-fotos` | Borradores de ítems |
| `iaSugerirProducto` | `POST /ia/comercios/{id}/sugerir-producto` | Descripción/precio |
| `iaBorradorRespuesta` | `POST /ia/comercios/{id}/borrador-respuesta` | Texto a mensaje/reseña |
| `iaMejorarTexto` | `POST /ia/comercios/{id}/mejorar-texto` | Nombre, descripción, copy del local u oferta |
| `iaAtencion` | `POST /ia/comercios/{id}/atencion` | Responder / aceptar / ordenar pedidos entrantes (borrador; la persona confirma, o su mandato lo autoriza según `docs/mandatos.md`) |
| `iaMejorarFoto` | `POST /ia/comercios/{id}/medios/mejorar-foto` | Borrador de imagen |
| `iaQuitarFondo` | `POST /ia/comercios/{id}/medios/quitar-fondo` | Borrador de imagen |
| `iaFotoAVideo` | `POST /ia/comercios/{id}/medios/foto-a-video` | Borrador de clip (≤ 15 s, con póster) |

Los medios con IA solo existen si `ia.medios` los lista. El resultado es un **borrador** (`url`); el comercio lo acepta poniéndolo en `imagenes` / `videos` con `editarComercio` / `editarOferta` (o subiendo via `POST /medios` si aplica). El proveedor es intercambiable; el costo real va en `consumo` (puede tipificar `imagen` / `segundo_video` además de tokens).

**Descartado:** resumen del día (no hay función ni ruta).

## Consumo auditable

Cada respuesta exitosa trae `consumo`: `tokens_entrada`, `tokens_salida`, `costo_usd`, `generacion`, y opcionalmente `imagenes`, `segundos_video`, `unidad` (`tokens` \| `imagen` \| `segundo_video` \| `mixto`). El nodo suma `costo_usd` al extracto. Si falla antes del proveedor, no hay `consumo`.

## Extracto y cuentas públicas

Igual que antes: `GET /ia/yo/extracto`, y en `gastos_publicados` los opcionales `gastos.tokens_ia` y `aportes_ia_recibidos` (`docs/sostenimiento.md`).

## Errores

| Qué pasa | Estado | Código |
| --- | --- | --- |
| Sin capacidad `ia` | 501 | `no_implementado` |
| IA no activada | 403 | `ia_no_activada` |
| Función no listada | 422 | `funcion_ia_no_ofrecida` |
| Tope del mes | 429 | `tope_ia_alcanzado` |
| Gateway / proveedor caído | 503 | `gateway_ia_caido` |
| Tope fuera de rango | 422 | `tope_ia_invalido` |

## Lo que un nodo NO puede hacer

- Cobrar margen o intermediar plata.
- Publicar en el catálogo, la ficha o un mensaje sin que la persona lo confirme.
- Confirmar un pedido sin las dos llaves, o con más permiso que el de quien llama al chat (un mandato `armar` nunca confirma; la sesión respeta `tope_por_pedido`).
- Ordenar un `podio` con otro criterio que la fórmula pública, aunque el agente haya elegido los candidatos.
- Mandarle al modelo la dirección exacta o un punto más fino que ~100 m.
- Cobrar el checkout del chat por Vereda o forzar tarjeta del nodo: solo medios del comercio.
- Dejar el tope solo en manos del gateway/proveedor: el nodo responde `tope_ia_alcanzado`.
- Mostrar IA en la app sin publicar `ia`.
- Degradar a quien no activa: traer tu agente sigue igual.
