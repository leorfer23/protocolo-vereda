# Capacidad `ia` (opcional)

Un nodo **puede** ofrecer IA nativa a comercios y compradores: catálogo desde fotos, pedidos en lenguaje natural, borradores de respuesta, resumen del día. Es una capacidad opcional: cada operador decide si la prende, y ninguna app puede contar con que exista. Traer tu propio agente (MCP + mandato) sigue gratis siempre; esta capacidad es una capa aparte, con costo de tokens a precio real, sin margen.

El nodo **no hospeda modelos**. Llama a un gateway de inferencia que el operador eligió (OpenRouter, Vercel AI Gateway u otro). La spec no cierra el enum de proveedores: solo exige medición auditable, que el costo se publique, y que el **nodo** garantice el tope por cuenta (no delega ese límite al gateway). En el anuncio, `gateway` es un texto libre informativo (`openrouter`, `vercel_ai_gateway`, …) para transparencia.

## Cómo se sabe

El nodo que la ofrece publica `ia` en `/.well-known/vereda.json` (`esquemas/ia.json#/$defs/capacidad`, `CapacidadIa` en el OpenAPI):

| Campo | Qué es |
| --- | --- |
| `funciones` | Qué ofrece: comercio (`catalogo_desde_fotos`, `sugerir_producto`, `borrador_respuesta`, `resumen_dia`) y/o comprador (`pedido_propuesto`, `buscar`, `sugerir`). Ausente una función = esa ruta responde `422 funcion_ia_no_ofrecida`. |
| `gateway` | Texto libre informativo: qué gateway usa este nodo (`openrouter`, `vercel_ai_gateway`, u otro). No es un enum cerrado. No cambia el contrato de las rutas. |
| `precio` | Siempre `modalidad: costo` y `margen: 0`. Moneda de medición `USD`; `equivalente_ars` opcional (solo referencia de UI). |
| `pago` | A `sostenimiento.cuenta`, referencia `ia:<identidad>:<periodo>` (`AAAA-MM`). Mismo patrón P2P que un aporte: la persona declara la transferencia; el operador marca recibido. |
| `tope_mensual_usd` | Default y máximo que una identidad puede elegir al activar. **El nodo lo garantiza** (rechaza con `429 tope_ia_alcanzado` al llegar), sea cual sea el `gateway`. |
| `periodo_reseteo` | `mensual` (día 1, zona del nodo). |
| `exige_pago_previo` | Si `true`, sin el extracto del mes anterior marcado recibido la IA queda pausada al empezar el mes. Default `false`. |

Sin `ia` en el anuncio, o si el operador la apaga, toda ruta bajo `/ia` responde `501 no_implementado` y las apps no muestran nada nuevo. Apagar no borra extractos ni el historial de activación.

## Activación (autoservicio)

Nadie aprueba a nadie. La persona (o el dueño de un comercio que actúa con su sesión) activa su IA:

- `GET /ia/yo` (`verMiIa`): estado `inactiva` \| `activa` \| `pausada`, `activa_hasta`, `tope_usd`, `consumido` del período abierto, `periodo`.
- `PUT /ia/yo` (`configurarMiIa`): `{estado, tope_usd?}`. `activa` o `pausada` con un tope entre el default y el máximo del nodo. Solo con sesión (un mandato no activa la IA de nadie: es plata y consentimiento).
- `POST /ia/yo/transferencia` (`declararTransferenciaIa`): declara que transfirió el extracto de un `periodo` a `sostenimiento.cuenta` con la referencia publicada. El operador confirma afuera, con sus herramientas; el nodo no mueve plata.

Si no está `activa`, cualquier función responde `403 ia_no_activada`. Si el consumido del mes llega al tope, `429 tope_ia_alcanzado` con `detalle.tope_usd` y `detalle.consumido_usd` (y `Retry-After` hasta el próximo reseteo): ese límite lo aplica el nodo, no el gateway. Si el gateway no responde, `503 gateway_ia_caido`.

## Funciones: proponen, no escriben

Toda función **devuelve un borrador**. Confirmarlo es un paso aparte, con los endpoints que ya existen (`crearOferta`, `editarOferta`, `responderResena`, `enviarMensaje`, `crearCarrito` / `agregarItemCarrito`, etc.) o con el agente de la persona y su mandato. La IA del nodo nunca escribe sola en el catálogo, el chat ni el carrito.

### Comercio (sesión dueña/equipo, o mandato `administrar`)

| Operación | Ruta | Qué propone |
| --- | --- | --- |
| `iaCatalogoDesdeFotos` | `POST /ia/comercios/{id}/catalogo-desde-fotos` | Borradores de ítems (nombre, descripción, precio sugerido, atributos) a partir de URLs de fotos. |
| `iaSugerirProducto` | `POST /ia/comercios/{id}/sugerir-producto` | Descripción y/o precio sugerido para un producto (texto y/o foto). |
| `iaBorradorRespuesta` | `POST /ia/comercios/{id}/borrador-respuesta` | Texto de respuesta a un mensaje o una reseña. |
| `iaResumenDia` | `POST /ia/comercios/{id}/resumen-dia` | Resumen del día y qué reponer, con números del nodo. |

Permiso de equipo: `catalogo` o `pedidos` según la función (`x-permiso-equipo` en el OpenAPI). Un miembro sin permiso recibe `403 sin_permiso`.

### Comprador (sesión, o mandato `armar` / `leer`)

| Operación | Ruta | Qué propone | Mandato |
| --- | --- | --- | --- |
| `iaPedidoPropuesto` | `POST /ia/pedido-propuesto` | Un carrito propuesto (comercio + ítems + cantidades) desde lenguaje natural ("armame una picada para 6"). La persona lo confirma con `crearCarrito` / ítems / `confirmarCarrito`. | `armar` |
| `iaBuscar` | `POST /ia/buscar` | Resultados de búsqueda interpretada (misma forma que `GET /buscar`, más una `interpretacion`). | `leer` |
| `iaSugerir` | `POST /ia/sugerir` | Repetir un pedido anterior o sugerir a partir del historial. | `leer` |

## Consumo auditable

Cada respuesta exitosa de una función trae `consumo`:

```json
{
  "tokens_entrada": 1200,
  "tokens_salida": 340,
  "costo_usd": 0.0124,
  "generacion": "gen_…"
}
```

`generacion` es opaco, único por llamada, y aparece en el extracto. El nodo suma `costo_usd` al `consumido` del período de la identidad. Si la llamada falla antes de llegar al gateway, no hay `consumo` y no se cobra.

## Extracto y cuentas públicas

- `GET /ia/yo/extracto?periodo=AAAA-MM` (`verExtractoIa`): líneas por `generacion` (función, instante, tokens, costo) y totales del período. Lo ve solo la identidad con su sesión.
- En `gastos_publicados` de `GET /sostenimiento` / `sostenimiento` del anuncio, cada período puede traer:
  - `gastos.tokens_ia`: lo gastado en la IA ofrecida (suma de costos del gateway).
  - `aportes_ia_recibidos`: lo que el operador marcó recibido con referencia `ia:…` en ese mes.

Así las cuentas cierran a la vista: tokens de IA vs lo recuperado. `gastos.tokens` sigue siendo lo de los agentes que administran el nodo, no mezclado.

## Errores

| Qué pasa | Estado | Código |
| --- | --- | --- |
| El nodo no ofrece `ia`, o se apagó | 501 | `no_implementado` |
| La identidad no tiene IA activa | 403 | `ia_no_activada` |
| Pedí una función que el nodo no lista | 422 | `funcion_ia_no_ofrecida` |
| Llegué al tope del mes | 429 | `tope_ia_alcanzado` |
| El gateway no responde | 503 | `gateway_ia_caido` |
| Tope pedido fuera del rango del nodo | 422 | `tope_ia_invalido` |

## Lo que un nodo NO puede hacer con esto

- Cobrar margen sobre el costo del gateway, ni un abono fijo disfrazado de "plan".
- Intermediar la plata: el pago es P2P a `sostenimiento.cuenta`.
- Escribir en catálogo, chat, reseñas o carrito sin que la persona (o su agente con mandato) confirme por los endpoints de siempre.
- Mostrar IA en la app si no publicó `ia` en el anuncio.
- Degradar a quien no activa: traer tu propio agente sigue igual.
- Hospedar el modelo dentro del nodo como requisito del protocolo.
- Dejar el tope mensual solo en manos del gateway: el nodo es quien lo garantiza y quien responde `tope_ia_alcanzado`.

## Relación con mandatos y agentes propios

La capacidad `ia` es del **nodo**. Un agente propio (Claude Desktop, etc.) habla por MCP con el mandato de la persona y no pasa por estas rutas ni consume este tope. Las herramientas MCP de `/ia` existen para que el mismo agente pueda, si la persona quiere, usar la IA del nodo con el costo a la vista.
