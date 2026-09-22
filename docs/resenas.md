# Reseñas y reputación contextual

Las reseñas son lo más valioso y lo más atacado de cualquier plataforma. Las de los incumbentes
están rotas por tres razones conocidas: se compran, se falsifican y se usan como arma entre
competidores. Vereda no las arregla con un equipo de moderación —no tiene equipo— sino con tres
decisiones verificables: **cuesta plata real dejar una reseña**, **el peso de cada reseña sale de una
fórmula publicada** y **nadie puede borrar ni comprar nada**.

## Lo que ya está en el protocolo

- Una reseña solo existe si hay un **pedido entregado** (`esquemas/resena.json`). No hay reseña sin
  compra: montar una campaña obliga a pagar y recibir los pedidos, uno por uno.
- Una por par autor-destinatario por pedido, dentro de los 7 días de la entrega.
- **Firmada** por quien la escribe con su clave Ed25519 (`docs/claves-y-firmas.md`): se verifica en
  cualquier nodo, se federa sin perder validez, y ni el operador del nodo puede fabricarla.
- **No se edita, no se borra, no se oculta.** Tampoco por el comercio, tampoco por el nodo. El
  reseñado responde públicamente, sin límite de tiempo.
- **No se paga.** No hay posiciones pagas, destacados ni criterio oculto en ningún lado del
  protocolo (`docs/ranking-y-despacho.md`).

Lo que falta, y es lo que define este documento, es **cuánto pesa cada reseña**. Un promedio simple
trata igual al vecino que compró treinta veces y a la identidad creada anteayer del otro lado de la
ciudad. Ahí es donde entra una campaña.

## Reputación contextual

La reputación que ve una persona **se calcula para ella**. No es un número escondido: es esta
fórmula, con estos números, corriendo sobre reseñas firmadas que cualquiera puede verificar.

### Peso de una reseña

```
w = c · v · r · k · f
```

| Factor | Qué mide | Valor |
| --- | --- | --- |
| `c` cercanía | Distancia entre la **zona habitual del autor** y el comercio | `1,0` ≤ 1,5 km (barrio) · `0,6` ≤ 10 km (ciudad) · `0,25` más lejos · `0,6` si el autor no tiene zona habitual |
| `v` para vos | Afinidad entre el autor y **quien mira** | `0,7 + 0,3 · (0,5 · prox + 0,5 · min(1, (2g + m)/6))` · sin sesión: `0,7` para todas |
| `r` recompra | Pedidos entregados del autor **a ese comercio** | `min(1 ; 0,4 + 0,15 · (n − 1))` → 1 pedido `0,40`, 5 o más `1,00` |
| `k` crédito de identidad | Antigüedad y diversidad del autor | `0,1 + 0,9 · (0,5 · min(1, dias/90) + 0,5 · min(1, comercios/3))` |
| `f` señales | Ráfaga, dueño, vinculadas | `1` normal · `0,2` en revisión por ráfaga · `0` dueño o identidad vinculada |

Donde `prox` es la misma escala de `c` aplicada entre la zona habitual del autor y la de quien mira,
`g` son las rondas y grupos compartidos entre ambos, `m` los comercios distintos a los que ambos le
compraron, `dias` los días desde el primer pedido entregado del autor y `comercios` la cantidad de
comercios distintos a los que le compró.

**Zona habitual**: la celda de ~1 km del punto mediano de las entregas de esa identidad en los
últimos 12 meses, y solo si tiene 3 o más pedidos entregados. Es un agregado: nunca es la dirección,
no es un dato nuevo y no se publica junto a la reseña. Con menos de 3 pedidos no hay zona y `c` vale
`0,6`.

Sin sesión, `v = 0,7` para todas las reseñas y se cancela al normalizar: **el número público es
exactamente el mismo cálculo**, sin la parte personal. No hay dos algoritmos.

### Promedio ponderado

```
promedio = (Σ wᵢ · pᵢ + 3 · µ) / (Σ wᵢ + 3)
```

`pᵢ` es el puntaje de 1 a 5 y `µ` el promedio de la red de los últimos 12 meses (`media_red` en la
respuesta; `4,0` mientras el nodo tenga menos de 100 reseñas). Los `3` puntos de la media son el
antídoto contra el comercio nuevo con una sola reseña perfecta: hacen falta varias reseñas de peso
pleno para despegarse de la media, y ninguna cantidad de reseñas livianas alcanza.

### Recompra

```
recompra = Σ_{compradores con n ≥ 2} k · f / (Σ_{compradores} k · f + 2)
```

Sobre **compradores**, no sobre reseñadores: volver a comprar cuenta aunque nunca hayas escrito nada.
Es la señal más cara de falsificar del sistema —exige un segundo pedido pagado y entregado— y por eso
entra directo en el número visible.

### Reputación

```
reputacion = 0,7 · promedio + 0,3 · (1 + 4 · recompra)
```

Los dos términos están en la escala 1–5, así que el resultado también. `orden=reputacion` en
`/comercios` y `/buscar` ordena por este número.

**La recompra pesa más que el puntaje**, y es deliberado. Dos comercios con 4,0 de promedio sobre 30
compradores: el que hizo volver a 24 queda en `4,0`; el que no hizo volver a nadie queda en `3,1`.
Las estrellas se consiguen; que la gente vuelva, no.

## Qué ataque neutraliza cada término

| Término | Ataque | Por qué funciona |
| --- | --- | --- |
| `c` cercanía | Reseñas compradas a granja de cuentas en otra provincia | Una identidad cuyas entregas caen lejos del comercio pesa `0,25`: cuatro veces menos que un vecino |
| `v` para vos | "Opinión promedio" que no se parece a la tuya | No neutraliza un ataque: hace que la reputación que ves esté hecha de gente que se parece a vos. Sin sesión se cancela y no hay dos números distintos |
| `r` recompra | Reseña de una sola compra, que es todo lo que una campaña puede pagar | Un pedido pesa `0,40`; cinco pesan `1,00`. El atacante tendría que comprar cinco veces por identidad |
| `k` crédito | Identidades creadas para la ocasión | Recién creada y con un solo comercio: `k = 0,25`. Con 90 días y 3 comercios: `k = 1,00`. Crear identidades es gratis; **darles historia cuesta pedidos reales** |
| `f` ráfaga | 20 reseñas de 1 estrella en un fin de semana | Multiplica por `0,2` mientras el patrón se sostenga, con criterio publicado y a la vista |
| `f` dueño/vinculadas | Autorreseñas y reseñas cruzadas entre comercios del mismo dueño | Valen `0`. Se publican igual, marcadas |
| `µ` media | Comercio nuevo con una reseña de 5 | Arranca pegado a la media de la red y se despega con volumen real |
| Recompra en el visible | Todo lo anterior a la vez | La campaña puede ensuciar estrellas; no puede fabricar segundos pedidos |

### El caso concreto

Comercio con 5 vecinos recurrentes (barrio, 4 compras cada uno, identidades de más de 90 días) que
lo puntuaron 5. Llega una campaña: 20 identidades nuevas, de otra ciudad, una compra cada una,
puntaje 1.

| Cálculo | Resultado |
| --- | --- |
| Promedio simple, como lo haría cualquier plataforma | **1,80** |
| Vereda, sin campaña | **4,31** |
| Vereda, con la campaña, sin marcarla de ráfaga | **3,80** |
| Vereda, con la campaña marcada de ráfaga | **4,17** |

Peso de un vecino recurrente: `0,595`. Peso de una identidad de la campaña marcada: `0,0036`. Hacen
falta 165 identidades de campaña para igualar a un solo vecino, y cada una cuesta un pedido pagado y
entregado. Ese es todo el diseño.

Las 20 reseñas **siguen publicadas y visibles**, con su marca y el criterio que la disparó. Vereda no
esconde nada: cambia cuánto pesa, a la vista de todos.

## Señales anti campaña

Deterministas, publicadas y recalculadas cada hora. Ninguna la decide una persona, ni el operador del
nodo, ni el comercio. Ninguna borra ni oculta nada.

### Ráfaga

Una reseña queda marcada `en_revision_por_rafaga` si se cumplen las tres condiciones a la vez:

1. Pertenece a un grupo de **5 o más reseñas al mismo destinatario dentro de 72 horas** con el
   puntaje del mismo lado (todas ≤ 2, o todas ≥ 4).
2. Al menos el **70 % de los autores del grupo tiene `k < 0,3`** (identidades sin historia).
3. El grupo es **3 veces o más el ritmo habitual del destinatario**: reseñas en esas 72 h contra el
   máximo entre `1` y el promedio de reseñas por 72 h de los últimos 90 días.

Efecto: `f = 0,2`. La marca aparece en la reseña, en el desglose de reputación y con los tres números
que la dispararon, para que cualquiera rehaga la cuenta.

La regla es **simétrica**: una campaña de elogios falsos se marca igual que una de ataques. Quien
compra reseñas positivas cae en el mismo criterio que quien paga una campaña negativa.

**Se levanta sola.** La marca no es un evento que alguien decide: es una función del estado actual,
recalculada cada hora. Cuando los autores ganan crédito —pasan los 90 días, le compran a otros
comercios— el grupo deja de cumplir la condición 2 y la marca cae sin que nadie intervenga. Una
oleada de clientes reales nuevos queda marcada unos días y se desmarca sola; una granja de cuentas
que nunca vuelve a comprar queda marcada para siempre.

### Dueño e identidades vinculadas

`f = 0` cuando:

- el autor es la identidad dueña del comercio reseñado;
- el autor es dueño de un comercio **vinculado** al reseñado;
- autor y destinatario son comercios vinculados entre sí.

Dos comercios están **vinculados** si comparten dueño, CUIT verificado, cuenta de cobro o clave
pública. Son hechos que el nodo ya tiene: no se recolecta ningún dato nuevo.

Estas reseñas **se publican igual**, marcadas `no_computa: dueno_o_vinculada`. Que un dueño se
autorreseñe es información útil para quien mira.

### Marcar no rompe la firma

`senales` y `visible` los escribe el nodo, no el autor, así que quedan fuera del JCS que cubre la
firma —igual que `respuesta`, que la escribe el reseñado (`docs/claves-y-firmas.md`). Una reseña
marcada por ráfaga sigue verificando byte por byte contra la clave de quien la escribió, en este nodo
y en cualquier otro. `ejemplos/vectores-firma.json` trae el par de vectores que lo prueba: la misma
reseña, antes y después de que la respondieran y la marcaran, con el mismo JCS.

### Lo que no existe

- **No se borra ni se oculta.** Ni el comercio, ni el nodo, ni el operador. La única acción del
  reseñado es responder, públicamente y firmado.
- **No se paga.** No hay reseñas patrocinadas, destacados, "opiniones verificadas por el comercio" ni
  ningún camino por el que la plata mueva el número.
- **No hay moderación discrecional.** Todo lo que baja el peso de una reseña está en este archivo,
  con números. Cambiarlo es cambiar este archivo en el repositorio público.

## Reseñas del comercio al comprador

`esquemas/resena.json` ya es simétrico (`autor`, `destinatario`, `rol_autor`): un comercio o un
repartidor reseña al comprador. Cómo pesan:

- Forman la **reputación del comprador**, con la misma fórmula. `c` y `v` valen `1` —un comercio es
  un punto fijo, no tiene "zona habitual"—, `r` es cuántas veces ese comprador le compró (el comercio
  que ya te vendió cinco veces pesa más que el que te vendió una), `k` es el crédito del comercio
  autor y `f` funciona igual.
- **No afectan la reputación del comercio autor**, ni su posición en el ranking, ni el despacho. Un
  comercio no gana nada reseñando.
- **No filtran a nadie.** Nadie queda excluido de comprar por su reputación. El número existe para
  que un comercio o un repartidor decidan si aceptan un pedido, que es una decisión suya.
- **Revelación simultánea contra la represalia.** Las dos reseñas de un pedido se publican cuando
  ambas existen, o al cerrarse la ventana de 7 días: lo que pase primero. Ninguna de las dos partes
  puede leer la del otro antes de escribir la suya, y así la reseña del comercio no puede ser la
  respuesta a la del comprador. Mientras tanto la reseña ya está firmada y guardada: nadie puede
  retirarla al ver la otra.

## Superficie de API

Una sola operación nueva: `GET /comercios/{id}/reputacion`.

El desglose no va dentro de `verComercio` porque esa respuesta es **pública y cacheada con ETag**, y
la parte "para vos" cambia con cada sesión: meterlas juntas obligaría a `Cache-Control: private` en
la ficha del comercio y tiraría el caché de la operación más pedida del nodo. Separadas, la ficha
sigue cacheándose para todos y la reputación se pide solo cuando se la va a mostrar.

- **Sin sesión**: el desglose global, cacheable, con `media_red`, `recompra`, la cantidad de reseñas
  que entraron y las que no, y por qué.
- **Con sesión**: lo mismo más el bloque `para_vos`, con `Cache-Control: private`.

`esquemas/comercio.json` sigue trayendo `reputacion` en la ficha (el número y la cantidad) para que
un listado no tenga que pedir N veces el desglose. El desglose completo está en la operación nueva.
