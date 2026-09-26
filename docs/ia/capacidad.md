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

Toda función **devuelve un borrador** (o un mensaje con widgets). Confirmarlo es un paso aparte con los endpoints que ya existen, o con el mandato de la persona cuando corresponda. La IA del nodo nunca compra sola ni publica sola.

### Comprador — chat con UI generativa

`POST /ia/chat` (`iaChat`, mandato `armar` o sesión): un turno de conversación. El cuerpo manda `mensaje`, `lat`/`lng`, historial opcional y, si hay, `comercio_id` / `carrito_id`. La respuesta es un `mensaje` (`esquemas/ia-widgets.json#/$defs/mensaje`) con `texto` y/o `widgets` tipados que la app dibuja con componentes Vereda:

| `tipo` | Qué dibuja |
| --- | --- |
| `elegir_categoria` | Chips/lista de categorías |
| `productos` | Tarjetas (foto, precio, Agregar) |
| `producto` | Una tarjeta |
| `carrito` | Ítems y total propuestos |
| `checkout` | Medios del comercio: solo `efectivo` / `transferencia` (nunca cobro por Vereda) |
| `recomendacion` | Texto + ítems opcionales |
| `comercio` | Ficha corta del local |

**Regla de compatibilidad:** el cliente **ignora** widgets cuyo `tipo` no conoce y degrada a texto si lo hay. `version` del widget es `1` en esta revisión.

Las acciones (agregar al carrito, confirmar pedido) las ejecuta la **persona** (o su agente) con `crearCarrito` / `agregarItemCarrito` / `confirmarCarrito` — el widget solo propone.

Respuesta completa por defecto. Streaming SSE (`Accept: text/event-stream`) es opcional: el nodo puede mandar el mismo `mensaje` armado por partes; si no lo ofrece, responde JSON como siempre (mismo espíritu que `GET /eventos` en `docs/eventos.md`).

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

- Cobrar margen, intermediar plata, o escribir en catálogo/chat/carrito sin confirmación.
- Cobrar el checkout del chat por Vereda o forzar tarjeta del nodo: solo medios del comercio.
- Dejar el tope solo en manos del gateway/proveedor: el nodo responde `tope_ia_alcanzado`.
- Mostrar IA en la app sin publicar `ia`.
- Degradar a quien no activa: traer tu agente sigue igual.
