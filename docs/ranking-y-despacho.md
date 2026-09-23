# Ranking y despacho: los dos algoritmos públicos

Ninguno tiene posiciones pagas, destacados ni criterios ocultos. Cambiarlos requiere cambiar este archivo en el repositorio público.

## Ranking por defecto

```
score = 0.5 · 1/(1 + d/2km) + 0.35 · p_min/p + 0.15 · entregados/(aceptados + rechazados)
```

`d` distancia en línea recta, `p` precio del ítem o ticket promedio, `p_min` el menor entre candidatos. El usuario o agente puede ordenar por cualquier criterio solo (`orden=distancia|precio|reputacion`); esta fórmula es solo el default.

La misma fórmula ordena el feed en video (`GET /buscar?con_video=true`, `docs/medios.md`): tener video no suma puntos, solo filtra. Con paginado, `p_min` se calcula sobre todo el conjunto de la consulta y no sobre cada página, así una página no cambia el orden de la anterior.

El tercer término —`entregados/(aceptados + rechazados)`— es cumplimiento, no opinión: mide si el comercio entrega lo que acepta. Las reseñas no entran en el ranking por defecto; entran cuando se pide `orden=reputacion`.

## Orden por reputación

`orden=reputacion` en `/comercios` y en `/buscar` ordena por la **reputación contextual** de
`docs/resenas.md`:

```
reputacion = 0,7 · promedio_ponderado + 0,3 · (1 + 4 · recompra)
```

No es un promedio de estrellas. Cada reseña pesa `w = c · v · r · k · f` —cercanía del reseñador al
comercio, afinidad con quien mira, cuántas veces volvió a comprar, antigüedad y diversidad de su
identidad, y las señales anti campaña—, y la recompra de los compradores entra directo en el número
visible. La fórmula completa, los valores de cada factor y qué ataque neutraliza cada uno están en
`docs/resenas.md`.

Consecuencias para el orden:

- **Con sesión, el orden es distinto para cada persona**, y la diferencia está publicada: es el
  factor `v`. Sin sesión, `v` se cancela y el orden es el mismo para todos.
- **Un comercio nuevo no arranca en 5.** El promedio ponderado incluye 3 puntos de la media de la
  red, así que una sola reseña perfecta no lo sube arriba de los que tienen historia.
- **Ninguna posición se compra.** Ni el orden, ni la reputación, ni el peso de una reseña. Tampoco se gana aportando al nodo: ninguno de los dos algoritmos lee `aporte_nodo` ni los pagos al nodo (`docs/sostenimiento.md`). Cambiar
  cualquiera de los dos algoritmos es cambiar estos archivos en el repositorio público.

## Despacho

Esto es el modo `pool`: el que usa un comercio cuando no tiene repartidores propios ni toma el que
eligió el comprador, o cuando esos no aceptaron. Cada comercio elige en su ficha (`envios.asignacion`)
qué modos usa y en qué orden —`propios`, `usuario`, `pool`— y qué pasa si nadie acepta; el diseño
entero, con quién responde ante el comprador y quién le paga al repartidor, está en
`docs/repartidores.md`. Sin bloque `envios`, el comercio usa solo este despacho.

Objetivo: minimizar tiempo muerto del repartidor y cumplir el ETA prometido. No es objetivo maximizar entregas por hora.

| Fase | Regla |
| --- | --- |
| 1 | Ofrecer al repartidor disponible más cercano al comercio, entre los elegibles; 30 s para aceptar; si no, al siguiente |
| 2 | Agrupar hasta 2 pedidos de comercios a menos de 500 m entre sí, con destinos a menos de 1 km entre sí y sin que el desvío agregue más de 10 minutos al ETA ya prometido del primer pedido, con consentimiento del usuario |
| 3 | Lotes cada 60 s con restricciones de frío, peso y vehículo; rondas y consolidadas como un viaje de varias paradas |

**Elegible** para un viaje del pool es el repartidor disponible cuya zona de trabajo declarada
(`repartidor.zona`: polígono o centro y radio) contiene **todas** las paradas del viaje, con caja
térmica si el viaje la requiere, capacidad para su peso y que acepta el medio con que se paga el envío
(`repartidor.cobro.metodos`). Nadie recibe ofertas del pool fuera de su zona. La zona y las
restricciones las declara el repartidor en `PUT /repartidor`; no las revisa nadie.

El desvío se mide sobre la misma ruta OSRM con la que se calculó el ETA, comparando la ruta agrupada contra la del primer pedido solo. Si agrupar rompe el ETA prometido, no se agrupa.

Garantías: el repartidor ve monto, distancia, peso y cómo se le paga antes de aceptar; rechazar no penaliza; soltar un viaje ya aceptado sí se ve en su reputación; un solo viaje activo por repartidor en fase 1; congelados con prioridad y máximo 20 min en camino; el ETA es el real (preparación + ruta OSRM).

La tarifa de envío la fija la cooperativa de repartidores y es pública por tramo de distancia. La red la publica en `tarifa_envio` de `/.well-known/vereda.json` (schema `Nodo` en `openapi.yaml`) y la aplica. El envío se le paga directo al repartidor, en efectivo o a su alias, por quien lo contrató (`docs/repartidores.md`): la red no lo cobra ni lo retiene.

La reputación del repartidor no entra en este algoritmo.
