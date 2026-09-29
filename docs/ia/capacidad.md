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
| `carrito` | Carrito **real** (`carrito_id`); ítems con `grupo` / `nota`; `faltantes` |
| `checkout` | Sobre `carrito_id` real; medios `efectivo` (con `paga_con` al confirmar) / `transferencia` |
| `recomendacion` | Texto + ítems opcionales |
| `comercio` | Ficha corta del local |
| `bienvenida` | Home del chat vacío (sin llamar al modelo): título, promos, volver a pedir, sugerencias |
| `respuestas` | Chips sobre el campo; tocar = mandar ese texto/valor |
| `mazo` | Cartas apiladas (Paso / ¡Esta! / Más como esta) |
| `podio` | Hasta 3 puestos con `razon` pública |
| `promo` | Carta grande con `sello` |

**Regla de compatibilidad:** el cliente **ignora** widgets cuyo `tipo` no conoce y degrada a texto si lo hay. En el esquema, un tipo desconocido **valida** como objeto genérico (`desconocido`: `tipo` + `version` + props libres) para que el mensaje no falle entero; la app igual lo saltea. Los tipos conocidos se validan estrictos. `version` de los conocidos es `1` en esta revisión.

Las acciones (agregar al carrito, confirmar pedido) las ejecuta la **persona** (o su agente) con `crearCarrito` / `agregarItemCarrito` / `confirmarCarrito` — el widget solo propone. El carrito del chat **reusa** el carrito del nodo (`carrito_id`).

Respuesta completa por defecto. Streaming SSE (`Accept: text/event-stream`) es opcional: el nodo puede mandar el mismo `mensaje` armado por partes; si no lo ofrece, responde JSON como siempre (mismo espíritu que `GET /eventos` en `docs/eventos.md`).

Chat vacío: el nodo puede devolver un widget `bienvenida` **sin** llamar al modelo (gratis): promos de adheridos cerca, volver a pedir, sugerencias.

#### Adheridos al chat de IA (regla pública)

Los usuarios pagan el costo de tokens de su IA; los comercios pueden adherirse (barato, cubre tokens, neto positivo para el nodo) para **aparecer en el chat de IA**. Eso vive en la ficha pública: `comercio.ia_chat` (`{adherido, vigente_hasta?}`), lo setea el operador del nodo.

- **Solo en el chat de IA del nodo** se filtra por adheridos (`solo_adheridos=true` en `iaCatalogoBuscar` / `iaPromos`).
- La **app común**, la **búsqueda** (`GET /buscar`) y el **ranking** siguen neutrales: sin efecto en ranking ni acceso (misma regla de sostenimiento).
- Por **MCP**, el agente propio de la persona es **neutral** por defecto (`solo_adheridos` ausente o false).
- Cobro de la adhesión: P2P a la cuenta del operador; Vereda nunca toca plata.

#### Orquestación: el modelo entiende y redacta, el nodo ejecuta

El modelo **no** llama herramientas a ciegas. En cada turno:

1. El modelo entiende el mensaje y devuelve un JSON compacto `{intencion, terminos, gusto, comercio, platos, personas, …}` (`buscar` \| `refinar` \| `elegir` \| `armar_carro` \| `checkout` \| `charla`) y redacta la respuesta corta en **voseo**.
2. El **nodo** ejecuta las herramientas deterministas, arma los widgets y guarda en el historial los ids de ofertas/carrito mostrados (así "de fugazzeta" y "esa" funcionan).

Herramientas (OpenAPI + MCP + uso interno del chat), compactas:

| Operación | Ruta | Qué hace |
| --- | --- | --- |
| `iaCatalogoBuscar` | `POST /ia/catalogo/buscar` | Tarjetas; texto + sinónimos en nombre/desc/categorías/atributos |
| `iaRecetaALista` | `POST /ia/receta-a-lista` | Platos → ingredientes desde `datos/recetas.json`; modelo solo para huecos (cacheado) |
| `iaListaACarrito` | `POST /ia/lista-a-carrito` | Ingredientes → carrito real con `grupo` y `faltantes` |
| `iaPromos` | `GET /ia/promos` | Promos de adheridos cerca |
| `iaMisPedidos` | `GET /ia/mis-pedidos` | Compacto, solo tu sesión |

#### Fórmula pública del podio

Cuando el nodo arma un widget `podio`, ordena hasta 3 tarjetas candidatas con un score público (misma idea que el ranking del barrio, calibrado al chat):

```
score = 0.35 · 1/(1 + distancia_m/2000)
      + 0.30 · (reputacion.promedio / 5)
      + 0.20 · min(1, pedidos_mes / 40)
      + 0.15 · coincidencia
```

`coincidencia` ∈ [0, 1] es cuánto matchea el texto/gusto pedido (1 = exacto tras sinónimos). Cada puesto lleva una `razon` en castellano que refleja el término que más aportó (`más cerca`, `mejor reputación`, `más pedida`, `más parecida a lo que pediste`). No hay posiciones pagas ni boost oculto por adhesión más allá del filtro previo de adheridos.

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

### La Libreta (memoria de la persona)

Lo que la IA sabe de cada persona vive en su **Libreta** (`docs/ia/libreta.md`, `esquemas/libreta.json`): órdenes, hechos, alias y cómo quiere que le hablen, cifrada con una clave de la persona, visible y editable en "Tu IA", y en `GET /yo/exportar`, `POST /yo/borrar` y la mudanza. El nodo la anuncia con `libreta` en `ia.funciones.comprador`. El índice, esta semana y la voz llegan al modelo en cada turno; el resto se busca con `mi_libreta_buscar`. Adentro del chat de IA del nodo, y solo ahí, el podio suma un término personal (`+ 0.20 · personal`), siempre visible en `razon_personal`.

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
