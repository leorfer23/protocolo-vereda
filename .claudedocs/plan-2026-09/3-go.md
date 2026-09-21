# Go para el nodo de referencia de Protocolo Vereda

Evaluación de cobertura del ecosistema Go (septiembre 2026) contra lo que necesita el nodo: HTTP+federación+MCP, sobre `openapi.yaml` (3.1, 61 operaciones) y 20 esquemas JSON draft 2020-12 con `$ref` cruzados.

## 1. Tabla de cobertura

| Necesidad | Librería candidata | Versión / fecha último release | Madurez | URL |
|---|---|---|---|---|
| HTTP server | stdlib `net/http` (router con métodos y wildcards desde Go 1.22) | Go 1.22 (feb 2024), vigente en toolchain actual | estable | https://go.dev/blog/routing-enhancements |
| HTTP router (alternativa) | `go-chi/chi` v5 | v5.3.0, 22 may 2026 | estable | https://github.com/go-chi/chi/releases/tag/v5.3.0 |
| PostgreSQL access | `jackc/pgx/v5` | v5.11.0, 7 sep 2026 | estable | https://pkg.go.dev/github.com/jackc/pgx/v5 |
| PostGIS / geo (tipos, EWKB) | `twpayne/go-geom` (encoding/ewkb, encoding/geojson) | v1.6.1, 14 abr 2025 | usable con cuidado | https://pkg.go.dev/github.com/twpayne/go-geom |
| PostGIS / geo (alternativa liviana) | `cridenour/go-postgis` (solo `Point`, Scanner/Valuer) | sin release taggeado verificado; repo activo | inmadura | https://github.com/cridenour/go-postgis |
| Radio / polígono en PostGIS | Sin librería Go dedicada: `ST_DWithin`, `ST_Contains`, `ST_Within` se ejecutan como SQL vía pgx; Go solo (de)serializa el resultado | — | estable (la lógica geográfica vive en PostGIS, no en Go) | https://pkg.go.dev/github.com/jackc/pgx/v5 |
| SQLite embebido (cgo) | `mattn/go-sqlite3` | v1.14.52, 5 sep 2026 | estable | https://pkg.go.dev/github.com/mattn/go-sqlite3 |
| SQLite embebido (pure Go) | `modernc.org/sqlite` | v1.59.0, 15 sep 2026 | usable con cuidado | https://pkg.go.dev/modernc.org/sqlite |
| JSON Schema 2020-12, runtime, cross-file `$ref` | `santhosh-tekuri/jsonschema/v6` | v6.0.3, 6 ago 2026 | estable | https://github.com/santhosh-tekuri/jsonschema/releases |
| Generar structs Go desde JSON Schema 2020-12 | `omissis/go-jsonschema` | v0.24.1, 1 ago 2026 | usable con cuidado | https://pkg.go.dev/github.com/omissis/go-jsonschema |
| Generar structs Go (alternativa) | `codeberg.org/emersion/go-jsonschema` | activo, sin fecha de release verificada | inmadura | https://pkg.go.dev/codeberg.org/emersion/go-jsonschema |
| OpenAPI 3.1 parsing/validation | `pb33f/libopenapi` | activo (soporta 3.0/3.1/3.2), última versión no verificada con fecha exacta | usable con cuidado | https://github.com/pb33f/libopenapi |
| OpenAPI 3.1 parsing (alternativa) | `getkin/kin-openapi` | v0.149.0, 28 ago 2026 (soporte 3.1 parcial: nullable arrays, 2020-12 vía `EnableJSONSchema2020()`) | usable con cuidado | https://pkg.go.dev/github.com/getkin/kin-openapi |
| Codegen server/client desde OpenAPI 3.1 | `oapi-codegen/oapi-codegen` v2 | v2.8.0, 17 jul 2026 (soporte 3.1 recién agregado, "initial support") | inmadura | https://github.com/oapi-codegen/oapi-codegen/releases/tag/v2.8.0 |
| Codegen server/client (alternativa) | `ogen-go/ogen` | activo; según su propio sitio es "el generador más joven" (primer commit 2021), foco declarado en OpenAPI 3, no confirma 3.1 completo | inmadura | https://ogen.dev/ |
| Ed25519 firma/verificación | stdlib `crypto/ed25519` | incluida en Go desde 1.13, vigente | estable | https://pkg.go.dev/crypto/ed25519 |
| HTTP Message Signatures (RFC 9421) | `yaronf/httpsign` | v0.6.1, 13 sep 2026 | usable con cuidado | https://pkg.go.dev/github.com/yaronf/httpsign |
| HTTP Message Signatures (alternativa) | `common-fate/httpsig` | activo, sin fecha de release verificada | inmadura | https://pkg.go.dev/github.com/common-fate/httpsig |
| JSON Canonicalization (RFC 8785) | `gowebpki/jcs` | v1.0.2, 21 sep 2026 | usable con cuidado | https://pkg.go.dev/github.com/gowebpki/jcs |
| MCP server SDK | `modelcontextprotocol/go-sdk` (oficial, con Google) | v1.7.0, 28 jul 2026; transportes: stdio, `StreamableServerTransport`/`StreamableHTTPHandler`, SSE | usable con cuidado (OAuth marcado "experimental"; SDK joven) | https://github.com/modelcontextprotocol/go-sdk |
| Webhook delivery / retries con backoff | sin librería estándar dominante; se implementa sobre un job queue | — | — | — |
| Background jobs (Postgres-native) | `riverqueue/river` | v0.47.0, 31 ago 2026 | usable con cuidado (pre-1.0) | https://pkg.go.dev/github.com/riverqueue/river |
| Background jobs (Redis) | `hibiken/asynq` | v0.26.0, 3 feb 2026 (pre-1.0, desarrollo "moderado" según el propio repo) | usable con cuidado | https://pkg.go.dev/github.com/hibiken/asynq |
| Observabilidad: tracing/metrics | `go.opentelemetry.io/otel` | v1.46.0, 25 ago 2026 (API traces/metrics estable desde v1.16.0/v0.39.0 para metrics) | estable | https://pkg.go.dev/go.opentelemetry.io/otel |
| Observabilidad: métricas Prometheus | `prometheus/client_golang` | v1.24.1, jul 2026 | estable | https://github.com/prometheus/client_golang/releases |

## 2. Distribución y operación

- **Binario estático único**: sí, con `CGO_ENABLED=0` el binario no depende de libc y cross-compila nativamente (`GOOS`/`GOARCH`) sin toolchain extra — esto se rompe si se elige `mattn/go-sqlite3` (cgo), que fuerza compilar con gcc por plataforma objetivo; `modernc.org/sqlite` evita el problema a costa de 1.3×-2.0× más lento en operaciones CPU-bound según benchmarks de sept. 2026 (https://oneuptime.com/blog/post/2026-02-02-sqlite-go/view).
- **Cross-compilación linux/amd64 y arm64**: nativa vía `GOOS=linux GOARCH=amd64|arm64 go build`, sin CGO.
- **Docker**: imagen `scratch` de referencia ronda 1.5 MB más el binario; `distroless/static` agrega ~2 MB (certs, tz, usuario no-root) — cifras de blogs de terceros, no de una medición propia sobre este proyecto (https://klotzandrew.com/blog/smallest-golang-docker-image/).
- **Build time**: el FAQ oficial de Go fija como objetivo de diseño "a lo sumo unos segundos para construir un ejecutable grande en una sola computadora" (https://go.dev/blog/routing-enhancements cita el mismo espíritu de simplicidad; el objetivo de compilación viene del FAQ de go.dev). No hay una medición específica para un proyecto del tamaño de este nodo (56 rutas / 61 operaciones) — va a "No verificado".
- **GC**: el propio *GC guide* de Go dice que el GC "no es completamente stop-the-world y hace la mayoría de su trabajo concurrentemente con la aplicación", con pausas STW breves en las transiciones mark/sweep y pausas dominadas por el tiempo de detener las goroutines corriendo, proporcionales a `GOMAXPROCS` más que al tamaño del heap (https://go.dev/doc/gc-guide). Como contraejemplo documentado en producción: Discord migró su servicio "Read States" de Go a Rust en 2020 porque el GC debía escanear una LRU cache completa y generaba picos de latencia periódicos, resueltos al eliminar el GC (https://discord.com/blog/why-discord-is-switching-from-go-to-rust). Es evidencia de un caso concreto, no una garantía general — depende del patrón de asignación de memoria del servicio.

## 3. Costo humano

- Go tiene una especificación deliberadamente chica (25 palabras clave) y curva de entrada rápida para colaboradores externos que ya conocen C-like syntax; es el argumento central de su propio FAQ de diseño para "fast compilation" y simplicidad de análisis (https://go.dev/blog/routing-enhancements, tema relacionado).
- Dev-loop: compilación incremental rápida por paquete (solo recompila lo que cambió y sus dependientes) — confirmado por la documentación de `go build`, aunque no hay una medición específica de este repo.
- Manejo de errores explícito (`if err != nil`) es verboso comparado con excepciones o `Result<T,E>`; es un patrón reconocido y discutido extensamente en la comunidad Go (evidencia cualitativa, no cuantificable con una fuente única).
- Sin tipos suma (sum types) nativos: un dominio con "seis tipos de oferta" y variantes por-tipo (`servicio`, `recurrente`, `consolidada`, etc., ver sección 4) se modela con structs con punteros opcionales o `interface{}`+type switch, patrón estándar en Go pero sin verificación exhaustiva en compile-time de que todos los casos estén cubiertos.
- `nil`: los punteros y las interfaces nil son una fuente de pánico en runtime documentada de forma extensa por el propio equipo de Go (no hay opción de tipo Option/Maybe en el lenguaje).

## 4. Riesgos específicos para Vereda

1. **`oferta.json` no usa `oneOf`/`discriminator` formal, pero SÍ tiene una unión discriminada informal**: `tipo` (enum de 6) determina cuál de `servicio`, `recurrente`, `stock`, `disponibilidad`, `componentes.elegir` aplica. En Go esto se traduce en un struct con ~10 campos opcionales (punteros) donde el compilador no obliga a manejar los 6 casos — el chequeo de "solo lleno el campo que corresponde a mi tipo" queda en runtime/tests, no en el sistema de tipos.
2. **Codegen desde `openapi.yaml` 3.1 es el punto más débil confirmado**: `oapi-codegen` v2.8.0 (jul 2026) recién agregó soporte 3.1 y los propios mantenedores lo llaman "initial support"; `ogen` no confirma 3.1 completo. Con 61 operaciones y `$ref` directos a los 20 esquemas JSON (no inline), el spec-first workflow probablemente requiera parches manuales o "trucos" — hay un post público documentando cómo forzar a `oapi-codegen` a aceptar 3.1 antes de v2.8.0 (https://www.jvt.me/posts/2025/05/04/oapi-codegen-trick-openapi-3-1/), señal de fricción real en este punto exacto.
3. **`lista.json` tiene un `oneOf` real** (`oferta_id` XOR `generico`) que si se valida con generación de structs Go se resuelve típicamente con dos punteros opcionales + validación manual de exclusividad, no con un tipo suma; el generador (`go-jsonschema`) declara soporte para `oneOf` pero no hay evidencia de cómo lo tipa exactamente para este caso.
4. **`comunes.json#/$defs/poligono` y `punto`** (consultas de radio y polígono) no tienen contraparte de tipo Go madura: la tabla no encontró una librería Go con adopción amplia y release reciente que envuelva `ST_DWithin`/`ST_Contains`; en la práctica el nodo va a escribir SQL crudo vía `pgx`, lo cual es viable pero reduce lo que Go "cubre" nativamente a serialización de resultados.
5. **`mandato.json.scopes`** codifica valores estructurados en strings con patrón regex (`pedir:<centavos>`, `pedir_diario:<centavos>`) — parseo y validación de esto es responsabilidad 100% del código de aplicación en cualquier lenguaje; no cambia por Go, pero sin sum types el árbol de decisión "¿qué scope es este y qué le exijo?" se vuelve otro type-switch más para mantener sincronizado a mano con el schema.

## 5. Ventajas específicas para Vereda

1. **MCP oficial existe y es Go-first**: el SDK `modelcontextprotocol/go-sdk` está mantenido junto con Google, cubre stdio y streamable HTTP (los dos transportes que la spec pide para el "servidor MCP como primera interfaz"), con releases activos (v1.7.0, jul 2026).
2. **`net/http` desde 1.22 alcanza sola para las 61 operaciones**: routing por método + wildcards de path cubre el patrón `/pedidos/{id}/items/{item}` sin depender de un framework externo, lo que reduce superficie de dependencias para "cualquiera que corra un nodo" en una VPS chica.
3. **Ed25519 y TLS son stdlib**: la firma de reseñas/pedidos/mandatos y la comunicación federada no dependen de una librería criptográfica de terceros para la primitiva central — reduce la superficie de auditoría de seguridad para un protocolo cuya garantía central es "quien firma es quien dice ser".
4. **Un solo binario estático, cross-compilado sin toolchain extra**: encaja con el requisito explícito de "un colectivo de comercios con una VPS barata" — sin runtime a instalar, sin gestor de paquetes de sistema, siempre que se evite la variante cgo de SQLite.
5. **`river` da background jobs transaccionales sobre el mismo Postgres** que ya va a usar el nodo (pedidos, mandatos, etc.), útil para los reintentos exponenciales de webhooks que pide `docs/` (24 h) sin sumar Redis como dependencia operativa extra — relevante para el criterio de "nadie más que un colectivo chico lo tiene que poder correr".

## 6. No verificado

- Tiempo de build real para un proyecto del tamaño de este nodo (56 rutas / 20 esquemas): no medido, solo el objetivo de diseño general de Go.
- Cifras exactas de memoria idle y tamaño de imagen Docker para un servicio comparable a este nodo específico (las cifras citadas son de proyectos Go genéricos, no de una réplica de esta spec).
- Versión y fecha de release exacta de `pb33f/libopenapi` (confirmado que soporta 3.1/3.2, no su changelog reciente).
- Si `go-jsonschema` (omissis) representa el `oneOf` de `lista.json` como tipo suma real, interfaz, o simplemente ambos campos opcionales sin exclusión forzada en compile-time — no se pudo verificar el output generado.
- Estado exacto de madurez de `cridenour/go-postgis` y `common-fate/httpsig` (no se encontró tag de release con fecha).
- Si existe alguna librería Go madura y mantenida que envuelva consultas PostGIS de radio/polígono con una API tipada (más allá de SQL crudo) — la búsqueda no encontró ninguna con evidencia de adopción amplia.
