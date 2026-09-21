# Rust para el nodo de referencia de Protocolo Vereda

## 1. Tabla de cobertura

| Necesidad | Librería candidata | Versión y fecha del último release | Madurez | URL |
|---|---|---|---|---|
| HTTP server + runtime async | tokio | 1.53.1, 2026-07-20 | estable | https://crates.io/crates/tokio |
| HTTP server + runtime async | axum | 0.8.9, 2026-04-14 | estable | https://crates.io/crates/axum |
| PostgreSQL | sqlx (async, queries verificadas en compile-time) | 0.9.0, 2026-05-21 | estable | https://crates.io/crates/sqlx |
| PostGIS / geo (planar) | geo (georust) | 0.33.1, 2026-04-20 | estable | https://crates.io/crates/geo |
| PostGIS ↔ sqlx (EWKB) | geozero (feature with-postgis-sqlx) | 0.15.1, 2025-12-11 | usable con cuidado | https://crates.io/crates/geozero |
| SQLite embebido | rusqlite | 0.40.2, 2026-08-08 | estable | https://crates.io/crates/rusqlite |
| SQLite embebido (alt.) | sqlx (driver sqlite integrado) | 0.9.0, 2026-05-21 | estable | https://crates.io/crates/sqlx |
| Validación JSON Schema 2020-12 + $ref cross-file | jsonschema (Stranger6667) | 0.56.0, 2026-09-10 | estable | https://docs.rs/jsonschema |
| Modelos tipados desde JSON Schema 2020-12 | typify (oxidecomputer) | 0.8.0, 2026-09-09 | usable con cuidado | https://github.com/oxidecomputer/typify |
| OpenAPI 3.1 spec-first (server/validación desde el .yaml) | openapi-to-rust | activo, docs revisadas 2026-07-15 | inmadura | https://openapi-to-rust.dev/ |
| OpenAPI 3.1 spec-first (alternativa histórica) | openapi-generator, generador rust-server | doc vigente 2026 | inmadura para este caso | https://openapi-generator.tech/docs/generators/rust-server/ |
| OpenAPI (dirección inversa: código→spec) | utoipa | 5.5.0, 2026-05-04 | estable, pero no es spec-first | https://crates.io/crates/utoipa |
| Firma/verificación Ed25519 | ed25519-dalek | 3.0.0, 2026-07-06 | estable | https://crates.io/crates/ed25519-dalek |
| HTTP Message Signatures RFC 9421 | httpsig | 0.0.26, 2026-07-22 | inmadura (versionado 0.0.x) | https://github.com/junkurihara/httpsig-rs |
| draft-cavage (no requerido por Vereda; federacion.md pide RFC 9421) | http-signatures (asonix) | sin releases recientes visibles | inmadura/discontinuada | https://github.com/asonix/http-signatures |
| Canonicalización JSON RFC 8785 (JCS) | serde_json_canonicalizer | 0.3.2, 2026-02-03 | usable con cuidado | https://crates.io/crates/serde_json_canonicalizer |
| Servidor MCP | rmcp (oficial, modelcontextprotocol/rust-sdk) | 3.4.0, 2026-09-15 | estable / activamente mantenido | https://github.com/modelcontextprotocol/rust-sdk |
| Webhooks / jobs / retries con backoff | apalis (backends Postgres, Redis, SQLite; retry vía tower) | 1.0.0-rc.10, 2026-09-15 | usable con cuidado (aún pre-1.0) | https://crates.io/crates/apalis |
| Observabilidad (tracing) | tracing | 0.1.44, 2025-12-18 | estable, de facto standard | https://crates.io/crates/tracing |
| Observabilidad (métricas/OTel) | opentelemetry | 0.33.0, 2026-09-18 | usable con cuidado (releases 0.x frecuentes) | https://crates.io/crates/opentelemetry |

## 2. Distribución y operación

Un binario Rust compilado en release es un solo ejecutable estático o casi estático por defecto; con target musl (`x86_64-unknown-linux-musl`, `aarch64-unknown-linux-musl`) se obtiene un binario completamente estático sin dependencia de glibc. `cross` (cross-rs/cross, https://github.com/cross-rs/cross) cross-compila a linux/amd64 y linux/arm64 corriendo el build en contenedores Docker preconfigurados, sin necesitar toolchains nativos por arquitectura. Imágenes Docker desde `scratch` o distroless con un binario Rust estático suelen quedar en el rango de un dígito a low-double-digit MB según ejemplos publicados (no verificado con una medición propia de un binario del tamaño de este proyecto — ver sección 6). No encontré una medición de memoria idle específica para un servicio axum+sqlx comparable en tamaño a este nodo desde una fuente primaria (TechEmpower u oficial); las cifras que circulan (decenas de MB) provienen de blogs, no de la fuente de benchmarks en sí — quedan en sección 6. Tiempo de build en frío e incremental: no hay implementación de referencia todavía, así que no hay número real para un proyecto de este tamaño (56 operaciones OpenAPI, 20 esquemas, servidor MCP); la encuesta oficial de rendimiento del compilador de Rust (blog.rust-lang.org, 2025) confirma que el rebuild incremental lento es la queja más frecuente entre usuarios de Rust en general, sin dar una cifra aplicable a este caso puntual.

## 3. Costo humano

La encuesta State of Rust 2024/2025 (blog.rust-lang.org) reporta que, entre quienes dejaron de usar Rust, compile times largos fue una de las razones citadas por cerca del 45%, y que esperar un rebuild incremental fue la queja abierta más común. Para colaboradores externos a un repo abierto, esto se traduce en un ciclo dev más lento que en lenguajes interpretados o con JIT rápido, aunque `cargo check` e incremental compilation lo mitigan parcialmente. El async de Rust agrega una curva propia: posts de practicantes (bitbashing.io "Async Rust Is A Bad Language", Qovery "Common Mistakes with Rust Async") documentan que depurar código async es más difícil porque se pierde la pila de ejecución legible, y que conceptos como `Pin`, `'static` y bounds `Send`/`Sync` se filtran a código de aplicación en escenarios con trait objects o spawns concurrentes — relevante acá porque el nodo tendría SSE (`GET /eventos`), reintentos de webhooks y validación de carrito paso a paso corriendo concurrentemente. No encontré una encuesta específica sobre onboarding de contribuidores externos a proyectos Rust open-source (más allá de la encuesta general de compile times), así que esa parte es una inferencia razonable, no un dato medido.

## 4. Riesgos específicos para Vereda

- **OpenAPI 3.1 spec-first débil**: no hay una herramienta dominante y madura para generar stubs de servidor o validación de requests directamente desde `openapi.yaml` (3.1, con `$ref` a `esquemas/*.json`). `openapi-generator`/rust-server documenta soporte débil de `oneOf`/`allOf`/`anyOf`/polimorfismo; `openapi-to-rust` es un proyecto joven y de mantenimiento individual. Probablemente haya que escribir handlers a mano y usar el crate `jsonschema` para validar el body contra los esquemas, en vez de un pipeline spec-first automático.
- **RFC 9421 en versión 0.0.x**: `httpsig` es la implementación más activa de HTTP Message Signatures, pero su propio versionado (0.0.26) señala una API todavía inestable — riesgo directo porque la firma HTTP entre nodos (federación) es central al protocolo.
- **JCS de nicho**: la canonicalización JSON (necesaria para que una firma Ed25519 sobre un pedido o mandato sea verificable byte a byte entre nodos) depende de crates pequeños (`serde_json_canonicalizer`); alternativas como `serde_jcs` se reportan como posiblemente abandonadas y no 100% conformes al RFC.
- **PostGIS fragmentado**: no hay un crate único "PostGIS para sqlx"; hay que combinar `geo` (álgebra geométrica) con `geozero` (conversión EWKB↔sqlx) y, para radios/polígonos de zonas de entrega, delegar en funciones SQL de PostGIS vía queries crudas — más piezas para integrar que un ORM con soporte geo nativo.
- **Curva async para colaboradores externos**: dado que el proyecto es CC0 y busca contribuciones externas, el modelo mental de `tokio`/`Send`/`'static` es una barrera de entrada mayor que en lenguajes con concurrencia más simple, según las fuentes citadas en la sección 3.

## 5. Ventajas específicas para Vereda

- Los seis `tipo` de `oferta.json` (`producto`, `pesable`, `preparado`, `compuesto`, `servicio`, `recurrente`) y los cinco `modo` de `precio` (`fijo`, `por_unidad`, `por_persona`, `por_periodo`, `a_cotizar`) son, en la práctica, variantes con datos asociados distintos; un `enum` de Rust con `match` exhaustivo obliga al compilador a que cualquier código nuevo trate los seis/cinco casos explícitamente — encaja con la nota del propio esquema de que "un comercio puede inventar subtipos" pero "apps y agentes solo necesitan reconocer estos seis".
- `comunes.json#/$defs/monto` exige centavos enteros ("nunca decimales"); el tipado estático de Rust sin coerción numérica implícita reduce una clase de bugs de redondeo en el manejo de dinero, algo central dado que el protocolo mueve pagos directos sin custodia.
- Ed25519 es el mecanismo de firma de reseñas, mandatos y transiciones de pedido (`docs/federacion.md`); `ed25519-dalek`, parte del grupo dalek-cryptography, es una implementación madura y ampliamente usada como dependencia única para esa primitiva.
- Un binario estático único encaja con "cualquiera puede correr un nodo": una cooperativa de comercios en un VPS chico copia un binario y lo corre, sin runtime, sin paso de instalación de dependencias en producción.
- El ecosistema `tower`/`tracing` da middlewares componibles (reintentos, timeouts, idempotencia) reutilizables entre el HTTP público, el cliente de federación y el servidor MCP — encaja con requisitos transversales del protocolo como `Idempotency-Key`, reintentos de webhook durante 24h y `ETag` en el catálogo de ofertas.

## 6. No verificado

- Memoria idle (rangos de decenas de MB para axum, cifras de Go Fiber) y "7.1M req/s" de Actix en TechEmpower Round 23: provienen de blogs/agregadores (tech-insider.org, rustvsgo.com), no de una lectura directa de la página de resultados de TechEmpower.
- Tamaño de imagen Docker (5–12 MB) para un binario Rust: tomado de ejemplos de blogs personales con "hello world", no medido sobre un binario del tamaño real de este nodo.
- Tiempo de build en frío e incremental para un proyecto con el tamaño de este spec (56 operaciones, 20 esquemas, MCP): no existe implementación de referencia, no hay cifra real disponible.
- Si `jsonschema` (Stranger6667) resuelve sin fricción el patrón exacto de `$ref` relativo entre archivos hermanos que usa este repo (p. ej. `comunes.json#/$defs/identidad` desde `pedido.json`) — la capacidad general de resolver referencias externas está documentada, pero no la probé contra estos esquemas concretos.
- Madurez/adopción real de `openapi-to-rust` en producción (no hay cifras de descargas ni casos de uso públicos verificados más allá de su propio sitio y repo).
- Si `typify` maneja bien el patrón de `oferta.json#/$defs/precio` (un objeto con `modo` como enum de tag pero campos opcionales sueltos, no un `oneOf` discriminado formal) — la documentación de typify confirma que `oneOf` mapea a `enum`, pero este patrón concreto de Vereda no es un `oneOf` clásico y no verifiqué el resultado de typify sobre él.
