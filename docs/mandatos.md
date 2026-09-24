# Mandatos: qué hizo tu agente

Un agente no entra por `/acceso`: actúa con un mandato que la persona le otorga desde su sesión (`esquemas/mandato.json`, `POST /mandatos`). El mandato dice qué puede hacer y con qué topes, y se revoca en un toque. Esta página cubre la otra mitad: que la persona pueda ver, después, qué hizo el agente con ese permiso.

## La actividad

`GET /mandatos/{id}/actividad` (`verActividadDeMandato`) devuelve lo que el agente escribió con ese mandato, de lo más nuevo a lo más viejo. Cada entrada (`mandato.json#/$defs/actividad`) trae:

| Campo | Qué es |
| --- | --- |
| `operacion` | El `operationId` que invocó: `crearPromocion`, `actualizarStock`, `aceptarPedido`. |
| `entidad` | Sobre qué escribió: `{tipo, id}`, el recurso que creó o cambió, para abrirlo. |
| `resumen` | Qué hizo en una línea, como lo diría un vecino: "Agregó una promoción 2x1". Hasta 140 caracteres. Lo escribe el nodo, no el agente. |
| `instante` | Cuándo. |

## Qué se anota

- **Toda escritura que el nodo aceptó con ese mandato**, y solo esas: una entrada por llamada exitosa que cambió algo, en la misma transacción que el cambio. Si la escritura se deshace, la entrada también.
- **No se anotan las lecturas** ni los rechazos (`fuera_de_mandato`, `requiere_confirmacion`, errores). Lo que la persona aprueba después con `POST /confirmaciones/{codigo}` lo hace ella con su sesión, así que tampoco es actividad del agente.
- **Lo que la persona hace con su sesión no entra.** Es la actividad del agente, no el historial de la cuenta.

## Quién la lee

- **Solo la persona que otorgó el mandato, con su sesión.** Un token de mandato recibe `403`: un agente no lee su propio rastro (por eso no hay herramienta MCP). El mandato de otra persona responde `404`, igual que uno que no existe, para no revelar cuáles existen.
- **Sigue legible con el mandato revocado o vencido.** Es justo cuando más interesa.

## Cuánto se guarda

El nodo guarda al menos los últimos **90 días** de actividad de cada mandato. Lo anterior lo puede borrar; no está obligado. Es el mismo plazo que el default de retención de un pedido (`docs/datos-y-privacidad.md`).

## Paginado

Por cursor opaco, como `listarPedidosDelComercio`: `limite` (50 por defecto, 200 como máximo) y, si hay más, `cursor_siguiente` para la página que sigue. Un cursor vencido o ajeno responde `422`.
