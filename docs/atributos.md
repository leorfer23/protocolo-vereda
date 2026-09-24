# Atributos: vocabulario sugerido por rubro

`atributos` (`esquemas/comunes.json#/$defs/atributos`) es un objeto abierto: clave libre en
snake_case, valor booleano, número o texto corto. Va en la oferta, sus variantes, el comercio y el
catálogo maestro. Nadie lo restringe y este archivo no cambia eso.

Lo que sí hace falta es que dos almacenes llamen igual a lo mismo. Si uno escribe `sin_tacc` y otro
`libre_de_gluten`, una búsqueda por `sin_tacc=true` encuentra a uno solo. Por eso el protocolo
**sugiere** un vocabulario común. Sugiere, nunca obliga: una clave que no está acá es tan válida como
cualquiera, el nodo la guarda y la devuelve igual, y si muchos comercios empiezan a usar la misma, se
suma a esta lista.

Las claves de acá no tienen tilde ni eñe: el patrón de clave es `^[a-z][a-z0-9_]*$`.

## Cómo se usan

- **Comercio y agente del comercio**: al cargar una oferta, usar la clave de esta lista si existe.
  Si no existe, inventarla en snake_case, en castellano, sin unidades en el valor.
- **Búsqueda**: `GET /buscar?atributos=sin_tacc=true,vegano=true` y el campo `atributos` de la
  herramienta MCP `buscar_ofertas` filtran por igualdad exacta. Un agente que busca "vino tinto
  malbec de Mendoza" puede filtrar por `varietal=malbec,region=Mendoza` y leer el resto de los
  atributos de cada resultado para comparar.
- **Valores**: booleanos para lo que es sí o no (`sin_tacc`), números sin unidad para cantidades
  (la unidad la dice la clave o esta tabla), texto corto y en minúsculas para lo demás, salvo nombres
  propios (`bodega`, `marca`, `region`).
- `restricciones` del usuario (`esquemas/usuario.json`) usa las mismas claves: `sin_tacc` en sus
  restricciones es `sin_tacc: true` en la oferta.

## Comunes a cualquier rubro

| Clave | Valor | Ej. |
|---|---|---|
| `marca` | texto | `"La Serenísima"` |
| `origen` | texto: provincia, país o zona | `"Mendoza"` |
| `refrigerado` | booleano | `true` |
| `congelado` | booleano | `true` |
| `artesanal` | booleano | `true` |
| `picante` | `"suave"`, `"medio"`, `"fuerte"` | `"medio"` |

## Almacén y supermercado

| Clave | Valor | Ej. |
|---|---|---|
| `contenido_neto` | número, en la unidad de `contenido_unidad` | `500` |
| `contenido_unidad` | `"g"`, `"kg"`, `"ml"`, `"l"`, `"unidad"` | `"g"` |
| `sin_tacc` | booleano: apto celíacos | `true` |
| `vegano` | booleano | `true` |
| `vegetariano` | booleano | `true` |
| `sin_lactosa` | booleano | `true` |
| `sin_azucar_agregada` | booleano | `true` |
| `kosher` | booleano | `true` |
| `organico` | booleano | `true` |
| `exceso_azucares`, `exceso_sodio`, `exceso_grasas_totales`, `exceso_grasas_saturadas`, `exceso_calorias` | booleano: el sello frontal que lleva el envase | `true` |

## Vinoteca

| Clave | Valor | Ej. |
|---|---|---|
| `bodega` | texto | `"Catena Zapata"` |
| `varietal` | texto en minúsculas; `"blend"` si es corte | `"malbec"` |
| `cosecha` | número: el año | `2021` |
| `region` | texto | `"Valle de Uco"` |
| `graduacion` | número: % de alcohol en volumen | `13.5` |
| `tipo_vino` | `"tinto"`, `"blanco"`, `"rosado"`, `"espumante"`, `"dulce"` | `"tinto"` |
| `crianza` | texto: barrica, meses | `"12 meses en roble"` |

## Verdulería

| Clave | Valor | Ej. |
|---|---|---|
| `origen` | texto | `"Cinturón hortícola platense"` |
| `organico` | booleano | `true` |
| `agroecologico` | booleano | `true` |
| `de_estacion` | booleano | `true` |
| `calibre` | texto | `"grande"` |

## Panadería

| Clave | Valor | Ej. |
|---|---|---|
| `sin_tacc` | booleano | `true` |
| `integral` | booleano | `true` |
| `masa_madre` | booleano | `true` |
| `del_dia` | booleano: horneado hoy | `true` |
| `relleno` | texto | `"dulce de leche"` |

## Carnicería

| Clave | Valor | Ej. |
|---|---|---|
| `corte` | texto | `"vacío"` |
| `animal` | `"vaca"`, `"cerdo"`, `"pollo"`, `"cordero"`, … | `"vaca"` |
| `con_hueso` | booleano | `false` |
| `alimentacion` | `"pastura"`, `"feedlot"` | `"pastura"` |
| `envasado_al_vacio` | booleano | `true` |

## Información nutricional

Claves planas, **por 100 g**, o por 100 ml si la oferta se vende en volumen (`nutricional_por`).
Planas y no anidadas porque `atributos` solo admite valores simples y porque así se filtran igual que
cualquier otra clave.

| Clave | Unidad |
|---|---|
| `nutricional_por` | `"100g"` (por defecto) o `"100ml"` |
| `calorias_100g` | kcal |
| `carbohidratos_100g` | g |
| `azucares_100g` | g |
| `proteinas_100g` | g |
| `grasas_100g` | g |
| `grasas_saturadas_100g` | g |
| `grasas_trans_100g` | g |
| `fibra_100g` | g |
| `sodio_100g` | mg |

Ej.: `{"calorias_100g": 61, "proteinas_100g": 3.1, "grasas_100g": 3, "sodio_100g": 50, "nutricional_por": "100ml"}`.
