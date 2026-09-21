# Arte previo: protocolos federados y de comercio abierto

## 1. Tabla

| Proyecto | Lenguaje | Huella nodo chico (fuente) | Qué dolió | URL |
|---|---|---|---|---|
| Beckn/ONDC | Go en beckn-onix (registro, gateway, adapters); no es "un nodo", es middleware empresarial | sin cifra publicada para nodo chico | onboarding de semanas por integración manual; registro central en la práctica | [beckn-onix](https://github.com/beckn/beckn-onix/blob/main/docs/user_guide.md) |
| Mastodon | Ruby/Rails + Sidekiq | ~1–1.5 GB RAM mínimo (2023-03-01, 2023-07-08) | Sidekiq: backlog bajo picos, regresión de RAM reconocida por maintainers (issue #40407, 2024) | [sharpletters.net](https://sharpletters.net/2023/03/01/mastodon-resource-optimization/), [GH #40407](https://github.com/mastodon/mastodon/issues/40407) |
| GoToSocial | Go | 250–350 MB RAM, 1 vCPU, diseño explícito | ninguno propio relevante; existe como reacción al peso de Mastodon | [docs.gotosocial.org](https://docs.gotosocial.org/en/latest/getting_started/) |
| Lemmy | Rust | sin cifra confiable encontrada | sin cola persistente de federación hasta v0.19 (2023-12-15): perdía acciones al reiniciar | [join-lemmy.org v0.19.0](https://join-lemmy.org/news/2023-12-15_-_Lemmy_Release_v0.19.0_-_Instance_blocking,_Scaled_sort,_and_Federation_Queue) |
| Akkoma/Pleroma | Elixir/BEAM | 512 MB–1 GB single user; ~1.3 GB pico activo | fork por decisiones unilaterales del maintainer de Pleroma (2022) | [write.as/golden-demise](https://write.as/golden-demise/hosting-a-pleroma-instance-metrics-and-costs), [docs.akkoma.dev](https://docs.akkoma.dev/) |
| Matrix Synapse | Python/Twisted + Rust selectivo desde 1.68 (2022) | sin cifra de "nodo chico" en fuente primaria | rutas calientes (push rules, auth) caras en Python puro; issue oficial pide Rust "opcional" | [GH #12164](https://github.com/matrix-org/synapse/issues/12164) |
| Matrix Dendrite | Go | más liviano que Synapse, sin cifra | logró paridad server-server 100% (ene 2023) pero el proyecto pasó a "solo fixes de seguridad" | [dendrite docs](https://matrix-org.github.io/dendrite/) |
| Matrix Conduit/conduwuit | Rust + RocksDB embebido | "RAM/CPU no perceptible" (anecdótico, no benchmark de maintainer) | nació como fork por estancamiento del mantenedor original | [edu4rdshl.dev](https://edu4rdshl.dev/posts/about-to-leave-matrix-oh-wait-there-s-conduwuit/) |
| AT Protocol/Bluesky | Go (indigo: PDS/relay), TypeScript (AppView) | no diseñado para nodo chico; relay es pesado | `did:plc` es un registro centralizado de escritura única pese al framing "portable" | [agent.io](https://agent.io/posts/risks-of-did-plc/), [Wikipedia AT Protocol](https://en.wikipedia.org/wiki/AT_Protocol) |

## 2. Beckn/ONDC en detalle

Arquitectura: **BAP** (app compradora) arma la solicitud → opcionalmente un **Gateway** la resuelve contra el **Registro** de red y hace multicast a los **BPP** (plataformas proveedoras) relevantes por categoría/zona; BAP y BPP se comunican después directo. El Registro es la fuente de confianza: lista `subscriber_id`, clave pública y cobertura de cada participante compliant ([beckn/registry](https://github.com/beckn/registry)). Firma: cada request/callback es un "contrato" firmado por el emisor y verificado por el receptor contra la clave publicada en el registro ([ONDC signing-verification.md](https://github.com/ONDC-Official/developer-docs/blob/main/registry/signing-verification.md)).

Referencia: **beckn-onix** (adapter BAP/BPP + gateway + registro), microservicios containerizados con Docker/docker-compose; existe un sandbox de certificación ("Beckn-in-a-box") para probar compliance antes de producción.

Gobernanza: pese al framing "red abierta", ONDC tiene un **facilitador de red único**, ONDC Limited, que aloja el registro central y redacta la política de red — no es descentralización de registro, es descentralización de ejecución con un ancla centralizada ([resources.ondc.org](https://resources.ondc.org/ondc-network-policy)). En 2022 el Comité Parlamentario de la India señaló falta de claridad sobre privacidad, seguridad y responsabilidades entre comprador/vendedor/plataforma ([medianama.com, 2022-06](https://www.medianama.com/2022/06/223-ondc-issues-parliamentary-committee-report/)). La complejidad de onboarding —semanas de integración manual por comercio— sigue siendo un obstáculo citado en 2025 ([tekdi.net](https://www.tekdi.net/all-blogs/ai-powered-beckn-integration-democratizing-complex-protocol-adoption)).

**Qué puede copiar Vereda**: el modelo de "contrato firmado" por mensaje (ya cubierto por RFC 9421 en Vereda); el sandbox de conformidad antes de producción; la separación clara adapter-de-protocolo vs. backend de negocio del comercio; una taxonomía explícita de códigos de error (Vereda ya tiene esquema `error`, mantenerlo tan explícito como el de ONDC).

**Qué evitar**: el registro/gateway central de facto pese al discurso de apertura — Vereda ya lo evita con `.well-known` + dominio, hay que defender esa decisión activamente cuando aparezca la presión de "un directorio que ayude a buscar nodos"; y la ambigüedad regulatoria inicial sobre responsabilidades, que Vereda ya mitiga en parte en `datos-y-privacidad.md` pero no explícitamente para disputas entre nodos.

## 3. Lo que dice la evidencia sobre el lenguaje

**Ruby (Mastodon)**: los propios maintainers reconocieron en 2024 una regresión de RAM ligada a threads de Sidekiq (issue #40407) — evidencia de maintainer, no de comentarista. El modelo (Rails + Sidekiq + Redis + Postgres) exige separar colas y limitar threads a mano para no explotar RAM en instancias chicas.

**Go (GoToSocial, Dendrite)**: GoToSocial fue diseñado explícitamente con un objetivo de footprint (250–350 MB) documentado por sus propios maintainers — no es una consecuencia accidental del lenguaje sino una decisión de diseño que Go facilitó. Dendrite alcanzó paridad funcional con Synapse (2023) pero el propio proyecto (ahora bajo Element) lo puso en modo mantenimiento — la razón documentada es priorización de recursos del equipo, no una limitación de Go.

**Rust (Lemmy, Conduit/conduwuit)**: Lemmy eligió Rust desde el inicio y aun así tuvo que rediseñar la entrega de federación en v0.19 (dic 2023) porque el problema no era velocidad de ejecución sino ausencia de cola persistente con backoff por destino — lección: Rust no sustituye diseño de colas. Los reportes de footprint mínimo de Conduit/conduwuit son anecdóticos (blogs personales), no benchmarks de maintainer.

**Python + Rust híbrido (Synapse)**: el propio issue de diseño (GH #12164, abierto 2022-03-04) pide la *opción* de escribir código sensible a performance en Rust, no una reescritura completa; desde Synapse 1.68 (2022) compilar desde fuente requiere un compilador Rust. Es la evidencia más directa: el equipo de Matrix, con años de Python en producción, optó por extraer rutas calientes puntuales a Rust en vez de reescribir todo — ni "todo Python" ni "todo Rust".

## 4. Errores del primer año

1. **La implementación de referencia se vuelve la spec de facto**: extensiones de Mastodon (`manuallyApprovesFollowers`, actor instance workaround) que otros tuvieron que imitar para interoperar, más allá del texto W3C ([fossacademic.tech, 2023-10-15](https://fossacademic.tech/2023/10/15/APnonStandard.html)). Fix: conformance suite independiente de la primera implementación.
2. **Colas de federación sin persistencia ni backoff**: Lemmy antes de v0.19 perdía acciones salientes al reiniciar; arreglado con cola persistente y un sender por instancia destino (2023-12-15).
3. **Fragmentación de versiones del mecanismo de firma**: el fediverse desplegado quedó atado a `draft-cavage-http-signatures-12` (expirado) mientras el IETF publicaba RFC 9421 en feb. 2024, forzando "double-knocking" (probar un esquema, si falla probar el otro) ([hackers.pub, análisis 2026](https://hackers.pub/@fedify/2026/why-activitypub-is-hard)).
4. **Identidad portable atada a un registro centralizado**: `did:plc` de AT Protocol/Bluesky es una escritura única alojada centralmente; el DID (y con él, todos los seguidores) no se puede mover si ese servicio falla o censura ([agent.io](https://agent.io/posts/risks-of-did-plc/)).
5. **Fork por gobernanza no resuelta de la referencia**: Pleroma → Akkoma (2022) por decisiones unilaterales del mantenedor original.
6. **Ancla centralizada pese al discurso de red abierta**: el "facilitador" único de ONDC aloja el registro central; el comité parlamentario indio marcó la ambigüedad de responsabilidades desde el arranque (2022-06).
7. **No hay suite de conformidad hasta que el ecosistema ya forkeó en la práctica**: el fediverse (Mastodon/Pleroma/Lemmy/Misskey) probó interoperabilidad ad hoc durante años antes de cualquier esfuerzo de estandarización compartido de firmas HTTP.

## 5. Recomendaciones para el plan de Vereda

1. Generar una suite de conformidad ejecutable (HTTP real, no solo JSON) a partir de `ejemplos/` + `openapi.yaml` + `esquemas/` antes de que exista una segunda implementación — extender `validar.py`, no reemplazarlo.
2. Diseñar la cola de salida de federación (pedidos, eventos, reseñas entre nodos) como cola persistente con reintento y backoff por nodo-destino desde el día uno, no como llamada HTTP síncrona en el camino caliente.
3. Fijar RFC 9421 como único mecanismo de firma sin variantes heredadas y versionarlo explícitamente, para no repetir el "double-knocking" del fediverse.
4. No introducir un gateway o directorio central "de hecho" aunque sea opcional al inicio — mantener `.well-known` + dominio como única vía de descubrimiento, incluso bajo presión de conveniencia.
5. Especificar y probar el caso límite de la "mudanza" de identidad (redirección firmada de 12 meses) cuando el nodo viejo no coopera o desapareció — es exactamente el caso donde falla `did:plc`.
6. Publicar un objetivo explícito de footprint para "nodo chico" (ej. <350 MB RAM, 1 vCPU, referencia GoToSocial) como criterio de diseño desde el inicio, no como optimización posterior.
7. Definir gobernanza de la implementación de referencia (más de un maintainer con permiso de merge, sucesión) antes de publicarla como "la" referencia.
8. Explicitar en `federacion.md` de quién es la responsabilidad en una disputa entre nodos, más allá de la lista de bloqueo pública — Vereda ya evita el problema estructural de ONDC, pero no da esa respuesta por escrito.

## 6. No verificado

- Cifra de "25x" de aceleración por push-rules en Rust en Synapse: aparece en síntesis de búsqueda, no pude confirmar el post original de matrix.org.
- Artículo de Business Standard (2025-05-05) sobre dificultades de ONDC: 403 al intentar leerlo, solo tengo el fragmento del buscador ("salida de jugadores clave, UX poco convincente").
- Ejemplo "500.000 seguidores / 40.000 dominios / agotamiento TIME_WAIT" para Mastodon: viene de síntesis de búsqueda, no de una fuente primaria con firma y fecha verificadas.
- "RAM/CPU no perceptible" de Conduit/conduwuit: blog personal, no benchmark de mantenedor.
- Que los servicios core de beckn-onix estén escritos en Go: afirmado por herramienta de búsqueda, no confirmado leyendo directamente el repo.
- Footprint concreto de un nodo chico de Lemmy: no encontré una cifra confiable en fuente primaria.
