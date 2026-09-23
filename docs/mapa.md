# El mapa: las calles de la zona

La app muestra un mapa en el seguimiento del pedido, en la ficha del comercio y en el viaje del
repartidor. Es un mapa de barrio: líneas finas sobre fondo liso, las avenidas más marcadas, sin
fotos satelitales, sin tiles y sin puntos de interés. Las calles las sirve **el propio nodo**, en
`GET /zona/calles`. La app nunca le pide calles a un tercero.

## Por qué las sirve el nodo

- **Nadie de afuera se entera de dónde está nadie.** Un servicio de mapas de terceros ve cada
  pedido de tiles: qué zona mira quién y cuándo. Acá el pedido va al nodo que ya conoce el pedido,
  y ni siquiera a él le dice algo: la ruta **no tiene parámetros**, así que el archivo es el mismo
  para todos y pedirlo no revela ninguna ubicación.
- **Liviano.** Un barrio grande son unos cientos de tramos: entre 100 y 300 KB sin comprimir y
  entre 30 y 80 KB con gzip. Cambia cuando el operador lo vuelve a bajar, cada varios meses.
  Se sirve con `ETag` y `Cache-Control: public`, y la app lo guarda: en el uso normal, un `304`.
- **Sin librerías.** Es JSON. La app lo lee con su decodificador de siempre y dibuja polilíneas.

## El formato

Un GeoJSON (RFC 7946) acotado, `esquemas/calles.json`. Ejemplo en `ejemplos/calles-zona.json`.

- `features`: solo `LineString`, cada una con `properties.tipo` y, si tiene, `properties.nombre`.
  Nada más: ni ids de OpenStreetMap, ni velocidades, ni sentidos de circulación.
- `bbox`: `[oeste, sur, este, norte]`. Es donde la app encuadra el mapa.
- `version`: cambia con cada descarga. `fecha_datos`: el día de los datos de origen.
- `atribucion`: obligatoria, ver abajo.
- Las posiciones van **`[lng, lat]`**, como manda RFC 7946: al revés del `{lat, lng}` del resto del
  protocolo. Cinco decimales (~1 m) alcanzan; más solo agranda el archivo.

Se eligió GeoJSON y no un formato propio más compacto porque el ahorro (un 30-40 % antes de
comprimir, bastante menos después de gzip) no paga lo que se pierde: el operador abre su archivo
en cualquier herramienta de mapas (QGIS, geojson.io) para ver qué está sirviendo, y cualquier
cliente lo lee sin un decodificador a medida.

### Tipos de vía

| `tipo` | `highway` de OpenStreetMap | Cómo se dibuja |
| --- | --- | --- |
| `autopista` | `motorway`, `motorway_link` | la más marcada |
| `avenida` | `trunk`, `primary`, `secondary` y sus `_link` | marcada |
| `calle` | `tertiary`, `tertiary_link`, `residential`, `unclassified` | fina |
| `pasaje` | `living_street` | más fina |
| `peatonal` | `pedestrian` | más fina, punteada si la app quiere |

Se dejan afuera `service`, `footway`, `cycleway`, `path`, `track` y todo lo que no es una calle
que alguien reconozca por su nombre. Los tramos de una misma calle pueden venir separados.

## De dónde salen y cómo se actualizan

De **OpenStreetMap**, bajadas **una vez** por el operador del nodo, nunca en tiempo de ejecución:

1. El operador elige el rectángulo de su zona (lo que cubren sus comercios y repartidores, con
   margen).
2. Baja las vías de ese rectángulo desde un extracto de OSM: un `.osm.pbf` regional (Geofabrik), o
   una sola consulta a Overpass, que devuelve el mismo JSON que después se convierte.
3. Las convierte a este formato y las carga en el nodo. El nodo de referencia trae un comando que
   hace los pasos 2 y 3.
4. Para actualizar, repite. La `version` cambia, el `ETag` también, y las apps bajan el archivo
   nuevo la próxima vez que abren el mapa.

Un nodo sin calles cargadas responde `404 no_encontrado`: servirlas es **opcional**. La app dibuja
entonces su cuadrícula genérica, que no dice nada de ningún lugar real.

## Atribución (ODbL)

Los datos de OpenStreetMap son libres bajo la Open Database License con una condición: decir de
dónde salen. Por eso `atribucion` es obligatoria en el esquema, siempre con `texto` que nombra a
OpenStreetMap, `licencia: "ODbL-1.0"` y `url: "https://www.openstreetmap.org/copyright"`.

- **La app** muestra el `texto` sobre el mapa, discreto y siempre visible (una esquina, tipografía
  chica), y lo enlaza a `url`. Nunca lo tapa ni lo esconde detrás de un menú.
- **El nodo** sirve el archivo tal como lo derivó de OSM: si lo modifica (recorta, simplifica),
  sigue siendo una base derivada bajo ODbL, y la atribución va igual.
- La especificación (CC0) no incluye datos de OpenStreetMap: el ejemplo tiene coordenadas dibujadas
  a mano. Los datos viven en cada nodo, con su licencia.

## Lo que no es

- No es un geocodificador: la app no busca direcciones acá. Las direcciones las escribe la persona
  (`PUT /yo/direcciones`) y el punto lo marca ella.
- No es ruteo: el recorrido del repartidor no sale de estas líneas.
- No tiene comercios ni puntos de interés: lo que se dibuja encima (el comercio, la casa, el
  repartidor) sale de los datos del pedido, no del mapa.
