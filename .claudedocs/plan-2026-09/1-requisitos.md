# Qué tiene que hacer un nodo — requisitos técnicos

## 1. Entidades y almacenamiento

| Entidad | Schema | Escribe | Perfil / notas |
|---|---|---|---|
| Comercio | `comercio.json` | nodo comercio | lectura alta, público |
| Oferta | `oferta.json` | comercio | lectura muy alta; `comercios/{id}/ofertas` con ETag (openapi.yaml:66) |
| Modalidad | `modalidad.json` | comercio | embebida en `comercio.modalidades[]`, sin ruta propia |
| Pedido | `pedido.json` | comercio (fuente verdad) + copia firmada en nodo usuario | escritura muy alta, 12 estados; `historial[]` **append-only** (pedido.json:41-54) |
| Pago | `pago.json` | comercio/PSP | nunca datos de cuenta (pago.json:5) |
| Repartidor | `repartidor.json` | nodo repartidor/cooperativa | ubicación escritura muy alta, solo visible en pedido activo |
| Usuario | `usuario.json` | nodo usuario | nombre/dirección restringidos |
| Reseña | `resena.json` | nodo autor, guarda destinatario | **append-only, sin edición/borrado** (resena.json:5); anonimizada al borrar cuenta |
| Suscripción | `suscripcion.json` | usuario+comercio (doble firma) | escritura baja, lectura por scheduler |
| Lista | `lista.json` | usuario | ítems genéricos resueltos en `/carritos/{id}/resolver` |
| Catálogo maestro | `catalogo-maestro.json` | cualquier nodo (`aportado_por`) | **replicado entre nodos** (federacion.md:25), clave EAN |
| Ronda | `ronda.json` | comercio o usuario | escritura baja |
| Grupo | `grupo.json` | usuario | cierre atómico, genera 1 pedido con N pagos |
| Viaje | `viaje.json` | comercio (despacho) | escritura alta, vida corta |
| Mandato | `mandato.json` | usuario, firma | leído en **cada** llamada de agente (mandato.json:5) |
| Mensaje | `mensaje.json` | comercio + copia cifrada usuario | cifrado X25519/XChaCha20 e2e |
| Cotización | `cotizacion.json` | usuario/comercio | presupuesto firmado por comercio |
| Evento | `evento.json` | el nodo mismo | **append-only, secuencia monótona por entidad, firmado** (eventos.md:3) |

## 2. Máquinas de estado

| Ciclo | Estados | Transición crítica | Cita |
|---|---|---|---|
| Pedido | creado→pagado→aceptado→preparando→listo→asignado→en_camino→entregado (+cancelado) | pago confirmado antes de aceptar; `listo` exige todos los ítems resueltos (atómico sobre `items[]`) | pedido.json:101-104; openapi.yaml:177 |
| Ítem | pendiente→confirmado/sustituido/faltante/pesado; sustituto vence en **5 min** | requiere timer por ítem | pedido.json:127; herramientas.json (responder_sustitucion) |
| Pago | pendiente→confirmado/vencido/en_mano/fallido | dirigido por webhook de PSP, idempotente | pago.json:15 |
| Viaje | ofrecido→aceptado/rechazado→en_curso→completado | **30 s** para aceptar, cascada al siguiente; 1 viaje activo por repartidor en fase 1 → asignación exclusiva, carrera entre couriers | ranking-y-despacho.md:19,23 |
| Suscripción/ocurrencia | activa/pausada/cancelada; futura→abierta→confirmada/salteada→generada | generación disparada por tiempo (`anticipacion_horas`), debe ser idempotente | suscripcion.json:35-47 |
| Ronda | abierta→cerrada→en_camino→entregada/cancelada | cierre por `cierre_pedidos` o `cupo`, se convierte en viaje multi-parada | ronda.json:16-18 |
| Grupo | abierto→cerrado→pedido_generado/cancelado; participante: invitado→armando→confirmado→pagado | `cerrar` agrega ítems de N participantes en **1 pedido con N cobros**, atómico | grupo.json:16,28; openapi.yaml:224 |
| Cotización | solicitada→presupuestada→aceptada/rechazada/vencida | aceptar crea pedido con precio congelado | cotizacion.json:35 |
| Mandato | activo/revocado/vencido | verificado en cada llamada; tope (`pedir:<c>`, `pedir_diario:<c>`) exige conteo atómico bajo concurrencia | mandato.json:23,32 |

## 3. Criptografía e identidad

- Par **Ed25519** por actor; privada custodiada cifrada por el nodo salvo `custodia_clave: propia` (federacion.md:9; usuario.json:17).
- Firma: JCS (RFC 8785) sobre el objeto sin `firma` (comunes.json:246) — canonicalización en cada firma/verificación, costo de CPU en hot path.
- Se firma: creación/aceptación/entrega de pedido (pedido.json:90-97), reseñas (resena.json:8), mandatos (mandato.json:8), presupuesto de cotización (cotizacion.json:32), suscripción por ambas partes (suscripcion.json:52-53), cada evento (evento.json:21), webhooks (header `Vereda-Firma`, eventos.md:15), entregas entre nodos (RFC 9421, federacion.md:30).
- Verificación al recibir: firma de federación contra clave publicada por el nodo de origen (federacion.md:31); webhook verificado antes de procesar (eventos.md:15).
- **Silencios**: sin rotación de clave Ed25519; sin ventana/zona horaria para `pedir_diario`; sin mecanismo de intercambio de claves X25519 del chat a partir de la identidad Ed25519.

## 4. Federación

- Descubrimiento: `GET /.well-known/vereda.json` (versiones, clave del nodo, zona, endpoints) — federacion.md:13; openapi.yaml:34-40.
- Flujo entre nodos (federacion.md:27-35): lectura pública cacheable por ETag → firma y `POST /v1/federacion/entrantes` con HTTP Signature RFC 9421 → nodo comercio valida, crea pedido, genera cobro PSP → eventos firmados de vuelta al nodo usuario → entrega firmada por repartidor → reseña firmada viaja al nodo reseñado.
- `POST /federacion/entrantes` responde `202` (openapi.yaml:298-304); **sin** política de reintento propia (a diferencia del webhook genérico, 24 h exponencial, eventos.md:10).
- Idempotencia: `Idempotency-Key` en toda creación; eventos deduplicados por `id` (eventos.md:33-35).
- Confianza: nodo con `.well-known` válido y firma correcta es aceptado; lista de bloqueo pública por fraude, sin otra moderación (federacion.md:47).
- Resiliencia: comercio es fuente de verdad — si cae el nodo usuario, el pedido sigue; si cae el del comercio, no hay pedido (federacion.md:35).
- Mudanza: `GET /yo/exportar` firmado + redirección firmada vieja→nueva por 12 meses (federacion.md:49-51).
- Replicación del catálogo maestro (protocolo, conflictos de EAN con múltiples `aportado_por`): no especificada.

## 5. Geo y ranking

- `/comercios` y `/buscar` requieren `lat/lng` (openapi.yaml:48-49,86-87); filtrado contra `zona_entrega` (polígono) → point-in-polygon por candidato **(inferido)**.
- Ranking default: `score = 0.5·1/(1+d/2km) + 0.35·p_min/p + 0.15·entregados/(aceptados+rechazados)` (ranking-y-despacho.md:8) — `p_min` se calcula sobre el conjunto de candidatos de la consulta: **por request, dos pasadas** (recolectar → normalizar). Sin evidencia de precómputo.
- `orden=reputacion` válido en `/comercios` (openapi.yaml:53) pero no en `/buscar` ni en `buscar_ofertas` del MCP (openapi.yaml:89; herramientas.json:13) — inconsistencia de superficie.
- Despacho (ranking-y-despacho.md:17-23): fase 1 evento-driven (oferta al repartidor más cercano, 30 s, cascada); fase 2 agrupa ≤2 pedidos <500 m "misma dirección" (criterio no cuantificado); fase 3 lotes cada **60 s** con restricciones de frío/peso/vehículo → job periódico. ETA = preparación + ruta OSRM (integración externa no detallada, **inferido**).

## 6. Eventos y tiempo real

- `evento.json`: `tipo` con patrón `entidad.accion` (12 prefijos), `secuencia` monótona por entidad, `firma_nodo` (evento.json:7-21).
- Canales: SSE `GET /eventos?desde=<id>` por actor ("de mis entidades", openapi.yaml:286) → log de eventos filtrable por actor, reanudable por cursor; Webhook firmado, reintento exponencial 24 h; Federación firmada RFC 9421.
- `PUT /repartidor/ubicacion` cada 5 s con viaje activo (openapi.yaml:242) — escritura de altísima frecuencia, visibilidad restringida a las partes.
- Fan-out exacto de eventos públicos de catálogo (`oferta.stock_cambiado`, `comercio.abierto/cerrado`) — ¿SSE público sin sesión? — no definido.

## 7. Rutas calientes (top 8)

1. `GET /comercios/{id}/ofertas` — catálogo por vista de comercio; público; **único con ETag explícito**, cacheable.
2. `GET /comercios` — búsqueda geo en cada apertura; público; ranking por query, poco cacheable.
3. `GET /buscar` — búsqueda de ofertas texto/EAN; público; mismo problema de cacheo.
4. `PUT /repartidor/ubicacion` — cada 5 s por repartidor activo; autenticado; no cacheable.
5. `GET /eventos` (SSE) — conexiones persistentes por actor; autenticado; recurso de conexión, no cacheable.
6. `POST /carritos/{id}/items` — cada ítem agregado al armar; autenticado; recalcula validez, no cacheable.
7. `POST /carritos/{id}/confirmar` — crea pedido, valida tope de mandato; autenticado; camino crítico, no cacheable.
8. `GET /pedidos/{id}` — polling de estado durante entrega activa; autenticado; dato privado, no cacheable.

## 8. Huecos de la spec

- **Carrito sin esquema propio** en `esquemas/` (solo inline en `openapi.yaml#/components/schemas/Carrito`) — sin TTL, persistencia ni reserva de stock especificados.
- **Reserva de stock concurrente**: nada en `oferta.stock` reserva unidades mientras están en un carrito (solo `reserva_mostrador` estático) → riesgo de overselling no abordado.
- `orden=reputacion` inconsistente entre `/comercios` y `/buscar`/MCP.
- Sin rotación de clave Ed25519 ni tratamiento de firmas históricas al rotar.
- `pedir_diario:<centavos>`: sin zona horaria/corte de "día" ni conteo atómico bajo concurrencia especificados.
- Fase 2 de despacho: "misma dirección" sin definición cuantitativa.
- Replicación del catálogo maestro: sin protocolo de sync ni resolución de conflictos por EAN.
- `POST /federacion/entrantes` sin política de reintento propia (a diferencia de webhooks).
- Derivación/intercambio de claves X25519 del chat: no especificado.
- `version_no_soportada` existe como error (error.json:9) pero no hay flujo de negociación de versión entre nodos con `versiones` distintas en `.well-known`.
- Ventana de reseña "dentro de 7 días" (README regla 4) no está en `resena.json`, solo en el README — sin campo formal que respalde la validación.
