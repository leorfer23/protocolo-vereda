# Plan de la implementación de referencia

Borrador 2, 2026-09-21. Lenguaje decidido; el resto a discutir. La evidencia detrás de cada punto está en `.claudedocs/plan-2026-09/` (cinco informes, con fuentes y con lo que no se pudo verificar marcado aparte).

## Decisión de lenguaje

**Decidido el 2026-09-21: Go.** Fue una decisión cerrada por poco; abajo queda qué se resigna.

El rendimiento no decide entre Rust y Go:

- En las tres escalas modeladas (barrio, ciudad, estrés) el costo dominante es Postgres: 3 a 8 consultas por pedido, 5 a 20 ms, 70 a 90 % del presupuesto. La federación agrega 10 a 100 ms de red.
- La brecha estimada entre Rust y Go en esta carga es menor a 2x. Caché de lecturas públicas, pooling, índice geo y escritura por lotes mueven de 10x a 100x.
- Salir de Python no se justifica por velocidad. Se justifica por memoria en un VPS de 1 GB (unos 150 a 300 MB de base contra decenas) y por distribuir un binario único.

Lo que sí distingue, verificado el 2026-09-21 en crates.io y proxy.golang.org:

| Necesidad | Go | Rust |
| --- | --- | --- |
| Firma HTTP RFC 9421 (`federacion.md` la exige) | `yaronf/httpsign` v0.6.1 | `httpsig` 0.0.26 |
| JSON canónico RFC 8785 | `gowebpki/jcs` v1.0.2 | `serde_json_canonicalizer` 0.3.2 |
| Ed25519 | stdlib | `ed25519-dalek` 3.0.0 |
| SDK oficial de MCP | `go-sdk` v1.8.0 | `rmcp` 3.4.0 |
| Cola de trabajos sobre Postgres | `river` v0.47.0 (encola dentro de la transacción) | `apalis` 1.0.0-rc.10 |
| Servidor desde OpenAPI 3.1 | `oapi-codegen` v2.8.0, "initial support" | sin herramienta dominante |
| Geo | SQL a mano sobre PostGIS | SQL a mano sobre PostGIS |
| Variantes del dominio | campos opcionales, sin chequeo en compilación | `enum` con `match` exhaustivo |
| Compilación cruzada | nativa (`GOOS`/`GOARCH`) | vía musl o `cross` |

Por qué Go:

- Una implementación de referencia también se lee. "Cualquiera puede correr un nodo" incluye poder auditarlo y forkearlo; la curva de entrada de Go es más baja.
- Las partes difíciles del nodo (reclamo exclusivo de viaje, tope de mandato bajo concurrencia, cierre atómico de grupo, cola de salida persistente) se resuelven en transacciones de Postgres, igual en cualquier lenguaje.
- GoToSocial documenta 250 a 350 MB y 1 vCPU como objetivo de diseño para un nodo federado chico.

Qué se resigna frente a Rust, y cómo se compensa (linter `exhaustive`, tablas de transición con tests, vectores de firma en `ejemplos/`):

- Priorizar garantías en compilación sobre facilidad de contribución: doce estados de pedido, seis tipos de oferta y cinco modos de precio son donde Go depende de disciplina y tests.
- Querer un núcleo único (canonicalización, firma, validación) reutilizable desde clientes web y móviles vía WASM. Go lo hace peor.

En ambos lenguajes los handlers se escriben a mano y se valida en ejecución contra `esquemas/`.

## Fase 0: cerrar la spec antes de escribir el nodo

Cambiar esto con nodos corriendo es caro. Orden sugerido:

1. `operationId` en las 61 operaciones de `openapi.yaml` (hoy ninguna lo tiene).
2. Uniones formales. En 20 esquemas hay un solo `oneOf` (`lista.json`). `oferta.json` acepta hoy cualquier combinación de `tipo` con bloques opcionales; hace falta `if/then` o `oneOf` para que `pesable`, `servicio`, `recurrente` y cada `modo` de precio exijan lo suyo.
3. Caché de lecturas públicas: `ETag` y `Cache-Control` en todas las rutas sin token. Hoy solo `GET /comercios/{id}/ofertas` lo declara.
4. Carrito: esquema propio en `esquemas/`, TTL y reserva de stock mientras se arma (hoy hay riesgo de sobreventa).
5. Rotación de claves Ed25519 y validez de las firmas históricas.
6. `POST /federacion/entrantes`: política de reintentos e idempotencia, y negociación de versión entre nodos (`version_no_soportada` existe como error, sin flujo).
7. `pedir_diario`: zona horaria y corte del día.
8. Vectores de prueba de firma en `ejemplos/`: objeto, bytes canónicos, clave, firma y un request RFC 9421 completo. RFC 9421 como único mecanismo, versionado, sin variantes.
9. Menores: ventana de 7 días de reseña en `resena.json` (hoy solo en el README); `orden=reputacion` en `/comercios` pero no en `/buscar` ni en MCP; "misma dirección" sin definir en despacho fase 2; replicación y conflictos del catálogo maestro; intercambio de claves X25519 del chat; mudanza cuando el nodo viejo no coopera; de quién es la responsabilidad en una disputa entre nodos.

## Fase 1: suite de conformidad

- Caja negra, por HTTP, contra la URL de cualquier nodo. Generada de `ejemplos/`, `openapi.yaml` y `esquemas/`.
- Existe antes que el nodo y es el criterio de salida de cada fase siguiente.
- Evita que la primera implementación se vuelva la spec de hecho, que es lo que le pasó a ActivityPub con Mastodon.

## Arquitectura del nodo

Un binario, `vereda-nodo`, contra PostgreSQL con PostGIS. SQLite queda fuera de la versión 1: geo, `SKIP LOCKED` y bloqueos por fila son la base del diseño.

- `nucleo`: tipos, JSON canónico, firma y verificación, validadores compilados una vez al arrancar desde `esquemas/` embebidos. La spec es la fuente; el binario no lleva copias editadas.
- `servicio`: reglas de negocio. La API HTTP y las 22 herramientas MCP llaman a esta misma capa.
- `estados`: cada máquina de estado como tabla de transiciones. Una transición es una transacción que actualiza la entidad, agrega al historial y escribe el evento firmado.
- `salida`: cola persistente para webhooks y federación, con reintento y backoff por destino. Nunca una llamada HTTP a otro nodo dentro del request del usuario.
- `federacion`: `.well-known`, entrantes, RFC 9421, caché de claves públicas de otros nodos.
- `busqueda`: candidatos por índice GiST, ranking en dos pasadas en memoria (la fórmula normaliza `p_min` por consulta).
- `despacho`: oferta de viaje con `UPDATE` condicional como reclamo exclusivo, cascada a los 30 s, lote cada 60 s.
- `tiemporeal`: SSE leyendo el log de eventos por cursor; ubicación de repartidores en memoria con volcado por lotes cada 1 a 2 s.
- Tope de mandato: contador por mandato actualizado con `UPDATE` condicional en la misma transacción que crea el pedido.

Objetivo de huella publicado desde el inicio: nodo de barrio en un VPS de 1 GB, Postgres incluido.

## Infraestructura

Dos preguntas distintas.

**El artefacto de referencia no se acopla a ningún proveedor.** Lo van a correr terceros en su propio servidor. Se entrega como binario Go estático, imagen de contenedor y un `docker-compose.yml` con Postgres y PostGIS. Nada de Workers, Durable Objects, D1, colas ni servicios propios de una nube dentro del nodo. Imágenes y adjuntos van detrás de una interfaz de almacenamiento compatible con S3.

Por qué Cloudflare no sirve como plataforma del nodo (documentación oficial, 2026-09-21):

- Workers corre JavaScript, TypeScript, Python y Rust; Go solo compilado a WebAssembly. Un servidor Go con `pgx`, `net/http` y trabajos en segundo plano no es eso. "Go en Cloudflare" significa Containers.
- Containers: "All disk is ephemeral", así que Postgres no puede vivir ahí. La ubicación es automática ("the nearest free container instance"), se duerme tras 10 minutos sin tráfico por defecto y se accede a través de un Worker en JavaScript.
- Cloudflare no aloja Postgres. Hyperdrive es un pool con caché hacia una base externa.
- El nodo es un proceso con estado y siempre encendido: lote de despacho cada 60 s, cola de salida con reintentos, SSE, generación de ocurrencias. Y hace 3 a 8 consultas por pedido, así que tiene que estar pegado a su base.

**Para la instancia propia: AWS en São Paulo para cómputo y base, con Cloudflare adelante.**

| | AWS `sa-east-1` | Cloudflare Containers |
| --- | --- | --- |
| Cómputo siempre encendido | Fargate ARM 0,25 vCPU y 0,5 GB: USD 12,40/mes | `basic` 0,25 vCPU y 1 GiB: hasta USD 24,73/mes con el plan de USD 5 |
| Postgres con PostGIS | RDS `db.t4g.micro` Single-AZ con 20 GB gp3: USD 29,20/mes | no existe; hay que contratarlo afuera |
| Entrada HTTPS | ALB: USD 24,82/mes más LCU | incluida |
| Salida a Internet | USD 0,15/GB | USD 0,04/GB, 500 GB incluidos |
| Base junto al cómputo | sí, misma VPC | no: ubicación automática, cada consulta cruza redes |
| Total mínimo | unos USD 66/mes más salida | unos USD 25/mes más una base externa |

- Cloudflare Containers es más barato en cómputo y salida, pero igual obliga a pagar una base en otro lado y a pagar latencia en cada consulta. Con Postgres dominando el presupuesto de latencia, es el peor lugar para ahorrar.
- El punto débil de AWS es la salida a USD 0,15/GB. Se resuelve con Cloudflare adelante como DNS, CDN y WAF: las lecturas públicas sin token son el tráfico que puede dispararse, y cacheadas no salen de AWS. Imágenes en R2.
- El ALB es el 37 % del costo mínimo. Alternativa a evaluar al desplegar: una sola instancia EC2 corriendo el mismo `docker-compose.yml` que usarán los terceros, con Cloudflare Tunnel como entrada. Cuesta menos y prueba el camino de quien se aloja solo; resigna los respaldos administrados de RDS.
- Dato que hoy deja a Containers fuera para usuarios en Argentina: los Containers cuelgan de un Durable Object, y la documentación dice "Durable Objects hinted to South America spawn in Eastern North America instead". Cada request no cacheado cruzaría el continente antes de llegar al nodo. Revisar cuando Cloudflare cree Durable Objects en Sudamérica.
- Reparto que aprovecha Cloudflare donde sí compite, que es casi toda la superficie que se toca al desarrollar: DNS, CDN, WAF, R2 para imágenes, Pages para el cliente web y la documentación, y Tunnel como entrada al nodo. En AWS São Paulo queda solo lo que tiene estado: el binario y Postgres. Con Tunnel como entrada, el ALB sobra.
- Esta decisión no bloquea nada hasta la fase 2. Al llegar ahí, medir P50 y P99 de `confirmarCarrito` desde Buenos Aires antes de cerrarla.

Precios de la API pública de listas de precios de AWS y de la página de precios de Containers. El cómputo de Containers está calculado sobre lo aprovisionado, como cota superior.

## Orden de construcción

Cada fase cierra con su parte de la suite en verde.

2. Núcleo y lecturas públicas: comercios, ofertas, búsqueda, ranking, caché.
3. Carrito, pedido y pago con el PSP detrás de una interfaz; eventos y SSE.
4. Cola de salida, webhooks y federación entre dos nodos locales.
5. Mandatos y servidor MCP.
6. Despacho, viajes y ubicación.
7. Suscripciones, rondas, grupos, cotizaciones, listas, catálogo maestro, mensajes.

Al final de la fase 3 y de la 6: prueba de carga con el modelo de `.claudedocs/plan-2026-09/4-rendimiento.md` (barrio: unas 10 lecturas/s; ciudad: unas 500 lecturas/s y 130 ubicaciones/s), midiendo memoria y P99. Los números de ese modelo son estimaciones; la prueba los reemplaza.

## Decisiones abiertas

- Repositorio del nodo: aparte (`vereda-nodo`), dejando este solo para la spec CC0, o acá mismo. Y su licencia.
- Gobernanza de la referencia: más de una persona con permiso de merge antes de llamarla "la" referencia.
- PSP para las pruebas de la fase 3.
