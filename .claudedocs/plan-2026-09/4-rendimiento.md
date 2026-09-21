# Rendimiento en un nodo Vereda: dónde se gana y dónde se pierde

## 1. Modelo de carga (estimación, bottom-up)

Supuestos explícitos: 3% de usuarios concurrentes en pico, 1 búsqueda cada 120 s por usuario activo, 3 lecturas de oferta por búsqueda, 5% de usuarios activos a mitad de checkout, 20% del volumen diario de pedidos concentrado en la hora pico, couriers activos pingueando cada 15 s.

| Endpoint | Barrio (200 comercios, 5k usuarios) | Ciudad (10k comercios, 500k usuarios) | Estrés (pico viral en lecturas) |
|---|---|---|---|
| Búsqueda pública `/buscar` `/comercios` | ~2 req/s | ~125 req/s | 2.000–5.000 req/s |
| Lectura de ofertas | ~6 req/s | ~375 req/s | 6.000–15.000 req/s |
| Validación de carrito | ~1 req/s | ~25 req/s | ~50–100 req/s (limitado por usuarios reales) |
| Escritura de pedidos | ~0.05 req/s | ~3 req/s | ~10 req/s (el mundo físico limita esto) |
| Ubicación de repartidor | ~1.3 req/s | ~130 req/s | ~130–300 req/s |
| Inbox de federación | <0.01 req/s | ~0.3 req/s | ~1–5 req/s |
| Webhooks salientes | ~0.1 req/s | ~14 req/s | ~50 req/s |

Insight clave: **lectura y escritura escalan distinto.** Escritura (pedidos, entregas) está acotada por capacidad real de cocinas/couriers, nunca explota. Lectura pública es cacheable y sin token (regla 5 del README) — es la única categoría que puede dispararse 50-100x por un link viral, scraping o un bot, y es exactamente la que un cache resuelve sin tocar el lenguaje.

## 2. Presupuesto de latencia — rutas calientes

**Escritura de pedido** (`POST /carritos/{id}/confirmar` → crea pedido, valida stock, cobra): TLS+parse HTTP ~0.1ms · verificación de firma/mandato Ed25519 ~0.05-0.15ms · JSON parse + validación de esquema (compilada) ~0.05-0.2ms · **3-8 round-trips a Postgres (check stock, lock, insert pedido/items, evento) × 1-3ms = 5-20ms** · ranking/lógica de negocio <0.5ms · serialización <0.2ms. **Postgres domina: 70-90% del presupuesto**, sin importar el lenguaje del proceso que espera esa I/O.

**Búsqueda/lectura pública**: dominada por la query geo-indexada (0.85-7.8ms, sección 4) + serialización; con cache-hit en CDN, el costo de origen es ~0.

**Validación de carrito** (`/resolver`): similar al pedido pero sin el commit final — 2-4 round-trips DB, mismo patrón dominante.

**Ubicación de repartidor**: payload chico, 1 UPSERT — si cada ping es su propia transacción, el costo es casi 100% fsync de Postgres, evitable con batching (sección 4).

**Inbox de federación** (`POST /federacion/entrantes`): además de la firma Ed25519, si la clave pública del nodo emisor no está cacheada hay que resolver `.well-known/vereda.json` del otro nodo — un RTT cruzado a otro dominio que puede sumar 10-100ms, muy por encima de cualquier costo de CPU local.

## 3. Cuánto cambia el lenguaje

- **Servidor Python (Granian vs Uvicorn)**: benchmark de emmett-framework (jul-2024) — Granian ASGI GET 43.263 RPS vs Uvicorn+httptools GET 37.121 RPS; en POST, Uvicorn fue más rápido (33.833 vs 22.038 RPS) — ni siquiera dentro de Python hay un ganador uniforme.
- **TechEmpower Round 23** (techempower.com, mar-2025, última ronda antes de archivarse): en tests JSON/plaintext puros Rust/Go superan a FastAPI por 10-40x, pero ese patrón es conocido por sobrestimar la diferencia real: en los tests *DB-bound* (multiple-queries, data-updates, fortunes) el round-trip a Postgres domina igual para todos los lenguajes y la brecha documentada entre el top Rust/Go y Python con driver async (asyncpg) se reduce a un orden de **~2-5x**, no 10-40x **(estimación basada en el patrón histórico de TechEmpower; no pude extraer la tabla numérica exacta de Round 23 — ver sección 7)**.
- **Memoria idle**: FastAPI+Uvicorn ~150MB vs Actix (Rust) ~20MB, ~7x (mawoka.eu). Un piloto en Raspberry Pi 5 (arXiv 2609.11932) midió Rust/Axum en 4.97MB idle y un ratio throughput/RAM 2.8x mejor que Go — muestra chico, no revisado por pares.
- **Traducción a tamaño de VPS (estimación)**: nodo de barrio (pico ~10 req/s lectura, <1 req/s escritura): 1 vCPU compartida alcanza en cualquier lenguaje; lo que limita en un VPS de 1GB es RAM — 150-300MB de base de Python es 15-30% de la caja, compitiendo con `shared_buffers` de Postgres. Nodo de ciudad (pico ~500 req/s lectura, ~130 req/s ubicación): con pool async y ranking sobre cientos de candidatos, 1-2 vCPUs alcanzan igual en Python que en Go/Rust — la diferencia es headroom de colas bajo picos, no el techo de throughput. Caso de estrés sin cache: acá sí, Python (aun async) probablemente necesita del orden de 2-4x más núcleos que Go/Rust para el mismo throughput de lectura — pero la sección 4 muestra que el cache evita llegar a este escenario en el 90%+ de los casos.

## 4. Lo que importa más que el lenguaje

- **CDN/cache de lecturas públicas**: el protocolo exige que todo lo público se lea sin token (regla 5) — es cacheable por diseño. Un hit ratio de 90-96% (rango típico de industria, Fastly/Bunny/Gcore) reduce la carga de origen 10-20x, más que cualquier salto de lenguaje.
- **Índice geo**: GiST con KNN en Postgres, ~0.85ms promedio sobre miles de millones de filas (Alibaba Cloud), hasta 7.8ms en casos peores (Crunchy Data) — exacto y suficiente hasta miles de ofertas por radio. H3 (RustProofLabs, jun-2022) da 73-77% más velocidad en vecino-más-cercano y 99% en agregaciones regionales, pero es aproximado por celda — vale la pena solo a escala de estrés/nacional, no en barrio/ciudad.
- **Pooling de conexiones**: sin pool, cada request paga apertura de conexión Postgres (TCP+TLS+auth), 5-50ms extra — mayor que el presupuesto entero de CPU de la app.
- **Batching de ubicación de repartidor**: a escala ciudad, 130 UPDATEs/s individuales son 130 fsyncs/s de WAL; agrupar en ventanas de 1-2s corta esto en un orden de magnitud.
- **Ed25519**: ~70.000 verif/s en hardware de consumo (cifra citada ampliamente), ~14µs ideal, ~50-150µs con overhead real (i7-10510U, ~125µs medido) — en ningún tamaño de nodo de la sección 1 esto pesa más de 1% de un core.
- **Validación de JSON Schema compilada**: fastjsonschema compilado es reportado como órdenes de magnitud más rápido que validar sin compilar (peterbe.com); la decisión que importa es "compilar una vez al arrancar", no el lenguaje.

## 5. Dónde Python de verdad no alcanza

Nodo de barrio: sin problema — pico de pocos req/s, cualquier proceso Python async lo sirve cómodo. La fricción real ahí es **RAM en un VPS de 1GB** (colectivo chico), no CPU. Nodo de ciudad: tampoco CPU-bound con los números de arriba; el riesgo real es **latencia de cola (P99)** si una validación sin compilar o un cómputo de ranking sobre miles de candidatos bloquea el event loop — es un riesgo de disciplina async, no exclusivo de Python. Caso de estrés: acá Python sin cache sí sería un problema de CPU/cores — pero la mitigación de cache lo evita antes de llegar a la app. Fricción de despliegue (sin binario único, requiere runtime + lockfile) es real pero es un costo operativo, no de rendimiento.

## 6. Veredicto acotado

**(a) ¿Justificado abandonar Python por rendimiento? No.** En las tres escalas modeladas, la latencia está dominada por Postgres, la red de federación y (en lectura) el cache — no por el lenguaje de la app; la brecha documentada Python-vs-Go/Rust en cargas DB-bound (~2-5x) es mucho menor que la de benchmarks JSON puros (10-40x), y las decisiones de la sección 4 mueven más la aguja que el cambio de lenguaje.

**(b) Brecha Rust-vs-Go para esta carga vs. sección 4**: pequeña, probablemente <2x entre sí en trabajo DB-bound — ambos compilados, sin intérprete ni GIL. Las decisiones arquitectónicas (cache CDN: -90-95% de carga de origen; pooling: 5-50ms/request; índice geo correcto) mueven 1-2 órdenes de magnitud. Rust-vs-Go es ruido comparado con esas decisiones.

## 7. No verificado

- Tabla numérica exacta de TechEmpower Round 23 para FastAPI/Go/Rust en tests DB-bound (no se pudo extraer; solo el patrón histórico de que DB-bound acorta la brecha).
- Overhead exacto de RFC 9421 (firma HTTP de federación) sumado a Ed25519 — estimación 50-150µs, no medido para este stack específico.
- Tiempos exactos de round-trip a Postgres para las queries reales de este esquema — extrapolados de benchmarks genéricos de Postgres/GiST, no del workload de Vereda.
- Aplicabilidad del hit ratio de CDN (90-96%) al tráfico real de Vereda, que es long-tail por comercio de barrio (menos concentrado que el tráfico típico de CDN).
- El paper de Raspberry Pi 5 (arXiv 2609.11932) es un piloto a pequeña escala, no revisado por pares.
