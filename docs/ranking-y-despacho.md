# Ranking y despacho: los dos algoritmos públicos

Ninguno tiene posiciones pagas, destacados ni criterios ocultos. Cambiarlos requiere cambiar este archivo en el repositorio público.

## Ranking por defecto

```
score = 0.5 · 1/(1 + d/2km) + 0.35 · p_min/p + 0.15 · entregados/(aceptados + rechazados)
```

`d` distancia en línea recta, `p` precio del ítem o ticket promedio, `p_min` el menor entre candidatos. El usuario o agente puede ordenar por cualquier criterio solo (`orden=distancia|precio|reputacion`); esta fórmula es solo el default.

## Despacho

Objetivo: minimizar tiempo muerto del repartidor y cumplir el ETA prometido. No es objetivo maximizar entregas por hora.

| Fase | Regla |
| --- | --- |
| 1 | Ofrecer al repartidor disponible más cercano al comercio; 30 s para aceptar; si no, al siguiente |
| 2 | Agrupar hasta 2 pedidos de comercios a menos de 500 m con destinos en la misma dirección, con consentimiento del usuario |
| 3 | Lotes cada 60 s con restricciones de frío, peso y vehículo; rondas y consolidadas como un viaje de varias paradas |

Garantías: el repartidor ve monto, distancia y peso antes de aceptar; rechazar no penaliza; un solo viaje activo por repartidor en fase 1; congelados con prioridad y máximo 20 min en camino; el ETA es el real (preparación + ruta OSRM).

La tarifa de envío la fija la cooperativa de repartidores y es pública por tramo de distancia. La red la publica y la aplica.
