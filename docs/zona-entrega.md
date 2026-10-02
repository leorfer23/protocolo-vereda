# La zona de entrega

`ubicacion.zona_entrega` dice hasta dónde entrega un comercio. Es lo que usan `buscarComercios`,
`verSucursales` (`llega`) y el carrito para saber si una dirección cae adentro. Un círculo perfecto
no le sirve a todos: un comercio llega a Pilar y a Del Viso pero no al barrio cerrado del medio, o
llega a dos pueblos que no se tocan. Y nadie tiene que escribir coordenadas a mano para armarla.

## Las dos formas

- **El anillo de 1.0.** Una lista de puntos `{lat, lng}`, cerrada (el primero igual al último, 4
  como mínimo). Sigue valiendo y quiere decir lo mismo que antes: una sola área sin huecos.
- **El objeto.** `forma` (cómo la pidió la persona), `areas` (la geometría que resolvió el nodo) y
  `resuelta` (cuándo). Es `esquemas/comercio.json#/$defs/zona_entrega`.

```json
{
  "forma": { "tipo": "radio", "radio_km": 15 },
  "areas": [ { "borde": [ { "lat": -34.32, "lng": -58.91 }, "…" ] } ],
  "resuelta": "2026-10-02T10:00:00-03:00"
}
```

Cada área es un `borde` y, si hace falta, `huecos`: anillos adentro del borde que no son parte de la
zona. Varias áreas son zonas separadas. Ejemplos: `ejemplos/zona-santa-elena-15km.json` (radio) y
`ejemplos/zona-pilar-del-viso.json` (dos áreas, una con hueco).

## Cuándo un punto está adentro

Un punto está en la zona si está en alguna área: dentro de su borde, o sobre él, y fuera de todos sus
huecos. **Siempre se mira la geometría guardada, nunca la forma.** El nodo y cualquier cliente que
dibuje la zona o diga "te llega" usan los mismos puntos, así que no pueden no estar de acuerdo.

## Cómo se arma

El comercio, la app o un agente mandan una `forma`. El nodo la resuelve a áreas y guarda las dos.

| `forma.tipo` | Lo que dice la persona | Lo que hace el nodo |
| --- | --- | --- |
| `radio` | "15 km desde el local" | Un polígono de 64 vértices sobre el círculo de `radio_km` alrededor de `centro` (ausente: el punto de `ubicacion.direccion`). Es lo que propone la app por defecto. |
| `localidades` | "Pilar, Del Viso y Villa Rosa" | La unión de sus límites de OpenStreetMap. Lo que se toca queda en una sola área; lo que no, en áreas separadas. |
| `dibujo` | "corré este borde hasta la ruta" | Nada: las `areas` las manda quien dibujó. Es también lo que queda cuando la persona ajusta una forma de las otras dos (`partio_de` dice cuál era). |

- **`menos`**, en `radio` y en `localidades`: localidades o barrios que se restan. Lo que queda
  adentro de un área sale como hueco ("menos el barrio cerrado Los Robles").
- **Nombres u ids.** Una localidad se escribe con `nombre` o con `osm` (`relation/…` o `way/…`).
  El nodo busca el nombre en los límites que tiene cargados y guarda el id, para que la forma diga
  siempre lo mismo. Un nombre que es más de un lugar no se adivina: 422 `localidad_ambigua` con los
  candidatos en `detalle` (en `resolverZonaEntrega`, en `sin_resolver`).
- **Radio en el plano.** Los vértices salen de la fórmula de destino sobre una esfera de 6371 km,
  el primero hacia el norte y en el sentido de las agujas del reloj, con cinco decimales. Lo que
  se compara es ese polígono, no el círculo.
- **Tamaño.** Hasta 50 áreas y 50 huecos por área. El nodo puede simplificar los límites de OSM
  (unos 10 m de tolerancia) y acepta por lo menos 2000 vértices en total; con más puede responder
  422 `zona_invalida`, igual que con anillos que se cruzan o huecos fuera de su borde.

## Qué guarda y devuelve el nodo

- Guarda la `forma` tal como quedó (con los ids de OSM resueltos), las `areas` y `resuelta`.
- Con `radio` o `localidades` escribe él las áreas: las que vengan se ignoran. Con `dibujo` guarda
  las que vienen, después de validarlas.
- Devuelve siempre las áreas, en la ficha y en la respuesta de `editarComercio` y `crearComercio`.
- **Vuelve a armarla** solo cuando la forma depende de algo que cambió en la ficha: un `radio` sin
  `centro` cuando cambia la dirección. **No** la cambia porque el operador bajó límites nuevos de OSM:
  la persona confirmó una forma y esa es la que vale hasta que la vuelva a guardar.
- Un comercio que escribió el anillo de 1.0 lo sigue viendo como anillo: el nodo no lo convierte.

## Mostrar antes de guardar: `resolverZonaEntrega`

`POST /zona-entrega/resolver` (herramienta MCP `zona_entrega_resolver`) recibe una forma y devuelve
la zona como quedaría (`esquemas/comercio.json#/$defs/zona_resuelta`): áreas, `superficie_km2`,
`vertices` y los nombres `sin_resolver`. No guarda nada. Sirve a la app, a la webapp y a los
agentes por igual para dibujar la zona en un mapa antes de confirmar.

## El agente arma la zona

Una persona no piensa en vértices: dice "15 km", "Pilar y Del Viso" o "hasta la ruta 8, sin cruzar
la Panamericana". El flujo:

1. **Proponer desde las palabras.** "15 km" es un `radio`; una lista de lugares es `localidades`,
   con `menos` para lo que no. Para un borde por calles, el agente arma un `dibujo` siguiendo los
   trazados con nombre de `GET /zona/calles` (docs/mapa.md). Sin datos de la persona, propone 15 km.
2. **Resolver.** `zona_entrega_resolver`. Si un nombre vuelve en `sin_resolver`, le pregunta cuál
   ("¿San Miguel partido o el barrio de Merlo?") y vuelve a resolver con el `osm`.
3. **Mostrar.** Le muestra a la persona las áreas en un mapa (el suyo, o el de la app) con la
   superficie, y qué quedó afuera si restó algo.
4. **Confirmar.** Solo con un sí de la persona guarda con `comercio_editar` (o en el alta, con
   `comercio_crear`), mandando la misma `forma` y, si es un dibujo, las mismas `areas`. Si la
   persona ajusta, vuelve al paso 2.

El agente nunca guarda una zona que la persona no vio: cambia a quién le llega el comercio.

## Compatibilidad

- **Quien escribe**: el anillo de 1.0 sigue valiendo en `crearComercio` y `editarComercio`.
- **Quien lee** tiene que aceptar las dos formas: `zona_entrega` es un arreglo (el anillo) o un
  objeto (con `areas`). Un cliente 1.0 que solo entiende el arreglo sigue andando con los comercios
  que no cambiaron su zona.

## Lo que todavía no es

- **Precio por zona.** `precio_envio.por_tramo` sigue siendo por km desde el comercio. Un precio
  propio por área (`nombre` ya la identifica) es un cambio aparte, en `modalidad.json`.
- **Cómo se ve.** Las pantallas para dibujar y ajustar la zona en la app y en la webapp son una
  decisión de diseño, no del protocolo.
- **Otras zonas.** La zona de una modalidad consolidada, la de trabajo de un repartidor y la del
  nodo siguen siendo un anillo.
