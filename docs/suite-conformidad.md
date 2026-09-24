# Suite de conformidad (diseño)

Fase 1 de `docs/plan-implementacion.md`. Existe antes que el nodo de referencia y es su
criterio de salida: si `vereda-nodo` no la pasa, no está listo, sin importar qué tan bien
se vea andando. La razón de fondo, no solo de forma: si el nodo se escribe primero, la
suite termina midiendo lo que el nodo hace en vez de lo que la spec dice, que es lo que le
pasó a ActivityPub con Mastodon (`.claudedocs/plan-2026-09/5-arte-previo.md`, punto 1).

Este documento es el diseño. No hay código todavía: es la primera entrega que pidió Leo,
para tener el visto bueno antes de escribir un test.

## Lo que ya existe y no se repite

`validar.py` ya prueba que la spec es consistente **consigo misma**, sin red: los ejemplos
contra los esquemas, los 67 casos límite de `ejemplos/casos/*.json`, `openapi.yaml` contra
OAS 3.1, que las 69 operaciones tengan `operationId`, que las 12 lecturas públicas declaren
`ETag`/`Cache-Control`/`304`, y los 11 vectores de `ejemplos/vectores-firma.json` (JCS,
firma Ed25519, request RFC 9421).

La suite de conformidad prueba algo distinto: que un **nodo corriendo**, en su propia URL,
se comporta como esos esquemas y ese `openapi.yaml` dicen. Es la versión en vivo de la
misma pregunta. Por eso reutiliza el cargador de esquemas de `validar.py` en vez de
duplicarlo (ver "En qué se escribe").

## Tres niveles, porque no todo se puede probar sin permiso

Una suite de caja negra "contra la URL de cualquier nodo" solo puede, sin credenciales,
leer lo que ese nodo ya publica. Todo lo que muta estado (crear un pedido, otorgar un
mandato, entregar un evento de federación) necesita que alguien decida correrlo. Por eso
la suite tiene tres niveles independientes, cada uno con su propio veredicto:

| Nivel | Necesita | Muta el nodo | Corre contra |
| --- | --- | --- | --- |
| **A — anónimo** | nada, solo la URL | No | cualquier nodo, incluso uno de producción, en cualquier momento |
| **B — autenticado** | sesión y/o mandato de un actor de prueba, provistos por quien corre la suite | Sí | un nodo (o entorno) que su propio operador designó para esto |
| **C — federación** | una identidad Ed25519 de prueba que el nodo bajo prueba trate como par | Sí (entrega eventos) | idem, y el nodo tiene que aceptar al emisor de prueba |

Un nodo puede someterse solo al nivel A. El reporte lo dice así, nunca como "0 %" en B y
C: un nivel no corrido es "no corrido", no es "fallado". Nadie debería tener que dar de
alta una cuenta de prueba solo para que un desconocido en Internet le corra la suite.

El acceso está en `openapi.yaml` (`/acceso`, `docs/acceso.md`), pero solo el de custodia
propia es obligatorio, y solo para el nodo que lo declara (`acceso.custodia_propia` en
`/.well-known/vereda.json`). Contra ese nodo, el nivel B prueba el acceso con claves que
genera en el momento —cada una da de alta un usuario de prueba, que es lo que el nodo
promete— y, si no se le pasó `--sesion`, se abre la suya por ahí y corre el resto. Contra un
nodo que no lo declara, el nivel B sigue necesitando `--sesion`: el acceso alternativo por
mensaje no se puede automatizar sin una casilla, y la suite no la tiene.

## Cómo se generan los casos (no se escriben a mano)

Esto es el punto central del diseño, porque es lo que el plan pide explícitamente y lo que
evita que la suite se desactualice sola frente a la spec:

- **Desde `openapi.yaml`**: se parsea una vez y se arma la matriz de las 69 operaciones
  (`operationId`, método, ruta, `security`, esquema de cada respuesta declarada). Cada
  entrada de esa matriz es un caso del nivel A o B según su `security`. Agregar una
  operación al spec le agrega un caso a la suite sin tocar la suite.
- **Desde `esquemas/`**: son el oráculo de validación de toda respuesta. Se reutiliza el
  mismo `Registry` (`jsonschema` + `referencing`) que arma `validar.py`, no una copia.
- **Desde `ejemplos/*.json`**: son los cuerpos de request para las operaciones de
  escritura. `ejemplos/ronda-los-alamos.json` es el cuerpo de `POST /rondas`,
  `ejemplos/mandato.json` el de `POST /mandatos`, y así con cada ejemplo que ya tiene un
  esquema asignado en `validar.py`. Antes de enviarlos se regeneran los campos que tienen
  que ser únicos por corrida (`id`, marcas de tiempo).
- **Desde `ejemplos/casos/*.json`**: son 67 casos ya clasificados `valido`/`invalido` por
  esquema. Un caso `invalido` se manda tal cual como cuerpo de la operación que crea o
  edita ese recurso, y se espera `422` con `esquemas/error.json`; un caso `valido` se
  espera aceptado. Agregar un caso límite a `ejemplos/casos/oferta.json` (por ejemplo) le
  agrega, gratis, una prueba de comportamiento HTTP a la suite — nadie escribe un test
  nuevo a mano para eso.
- **Desde `ejemplos/vectores-firma.json`**: dos usos. (1) la identidad y clave de prueba
  para bootstrapear el nivel B y C sin generar nada nuevo. (2) el oráculo de firma: sirve
  para verificar, contra bytes conocidos, que la propia implementación de JCS y Ed25519 de
  la suite es correcta antes de usarla para juzgar a un nodo ajeno.

Ninguna de estas fuentes se copia a mano dentro de la suite: se leen del repo en tiempo de
generación de casos. Un PR que cambie `esquemas/` o `ejemplos/` cambia lo que la suite
prueba la próxima vez que corre, sin tocar el código de la suite.

## Qué prueba cada nivel

**Nivel A — anónimo, de solo lectura.**

1. *Estructura.* Las 14 lecturas públicas responden al método declarado, devuelven `ETag`
   y `Cache-Control` en `200`, y `304` sin cuerpo al repetir con `If-None-Match`.
2. *Esquema en vivo.* Toda respuesta `200` de una ruta pública (`/comercios`,
   `/comercios/{id}`, `.../ofertas`, `.../promociones`, `.../reputacion`, `/ofertas/{id}`, `/catalogo/{ean}`, `/buscar`,
   `/rondas`, `/rondas/{id}`, `/.well-known/vereda.json`, `/zona/calles`, `/actores/{id}/claves`,
   `/actores/{id}/mudanza`, `/actores/{id}/resenas`) valida contra el esquema que
   `openapi.yaml` referencia. `/buscar?con_video=true` trae solo ofertas con `videos`, y `/buscar` pagina:
   `limite=1` trae una, el `cursor_siguiente` da la siguiente sin repetirla y un cursor inventado da `422`.
   Sin fixtures propios: valida lo que el nodo realmente tenga
   publicado, sea un comercio o cien. `/zona/calles` es opcional: un `404` con
   `esquemas/error.json` queda omitido, no fallado (`docs/mapa.md`).
3. *Errores.* Una ruta con parámetro que no existe (`ean` inventado, `id` inventado)
   devuelve el `estado_http` declarado con cuerpo `esquemas/error.json`, y `codigo` dentro
   del vocabulario de `error.json#/properties/codigo/examples`.
4. *Fórmula de reputación.* `GET /comercios/{id}/reputacion` no se valida solo contra el
   esquema: la suite rehace la cuenta con las partes que el propio nodo publica
   (`0,7 · promedio + 0,3 · (1 + 4 · recompra)`, `docs/resenas.md`) y falla si el número no
   cierra, o si el desglose no dice qué fórmula aplicó. Un nodo que devuelve 5,0 con un
   promedio de 3,2 no cumple el protocolo aunque el esquema valide.
5. *Firmas reales, sin fixtures.* Cada reseña pública de `/actores/{id}/resenas` se
   verifica de punta a punta: JCS del objeto sin `firma`, contra la clave publicada en
   `/actores/{firmante}/claves` — que puede vivir en **otro nodo**, exactamente la prueba
   de interoperabilidad entre nodos que importa, sin que la suite tenga que crear nada.
   Es la aplicación literal de "cualquiera lo verifica" de `docs/claves-y-firmas.md`. La suite saca
   antes los campos que el firmante no escribió (`respuesta`, `senales`, `visible`): un nodo que los
   metiera en el JCS haría fallar las firmas de sus propias reseñas. Lo mismo, con el mismo
   código, para lo que prueba identidad (`docs/identidad-y-verificacion.md`): cada vinculación
   de `/actores/{id}/verificacion` tiene que estar declarada y firmada por ese mismo actor, y
   cada atestación y denuncia pública, por su autor. Las pruebas que viven afuera (DNS, una
   página, un perfil) y la firma del nodo sobre el documento no se rehacen en esta fase.
6. *Negativos sin sesión.* Los 74 casos de `ejemplos/casos/*.json` puestos como cuerpo de
   la operación de escritura correspondiente, sin credenciales: se espera `401`, no `422`
   ni `500` — que el nodo pida autenticación antes que validar el cuerpo.

**Nivel B — autenticado (credenciales de prueba del operador).**

- Ciclo completo carrito → confirmar → pago → entregado, con los ejemplos como cuerpos:
  `agregarItemCarrito` responde `valido`/`incompleto`/`no_disponible` según
  `docs/carrito-y-reserva.md`; `confirmarCarrito` reserva y devuelve `402` si excede el
  mandato, `409` si se agotó algo entre el armado y la confirmación.
- Ventanas de tiempo (`carrito_vencido` a las 24 h, `plazo_aceptacion_min` en efectivo) se
  prueban con el reloj del nodo si expone uno de prueba corto, o quedan documentadas como
  prueba de larga duración opcional — no bloquean el resto del nivel B.
- Direcciones guardadas: `PUT /yo/direcciones` reemplaza la lista y la devuelve, `GET /yo` la
  muestra, etiquetas repetidas o una dirección sin punto dan `422`, y un token de mandato no
  la escribe nunca. Al final se restauran las que la sesión de prueba tenía.
- Mis comercios: `GET /yo/comercios` con la sesión de prueba responde `200` con `MiComercio[]`, y
  cada comercio de la lista existe y coincide con su ficha pública. La lista puede venir vacía:
  la sesión de prueba puede ser la identidad del comercio y no su dueña.
- Elegir cómo pagar: con el comercio de prueba, `metodo_pago` fuera de
  `efectivo`/`transferencia` da `422`; uno que el comercio no acepta da `422`
  `efectivo_no_disponible` o `medio_no_disponible` con `detalle.medios_cobro` igual a los
  `medios_cobro` publicados; uno que acepta crea el pedido con el cobro de los productos por
  ese medio.
- Seguimiento en camino: la identidad de prueba se declara repartidora, pide con envío,
  toma el viaje, retira y reporta un punto. `GET /pedidos/{id}` en `en_camino` trae ese
  punto en `ubicacion_repartidor`, y ya entregado no lo trae. Si el nodo no deja armar
  algún paso previo (alta de repartidor, despacho en 20 s), el caso se omite, no falla.
- La oferta dice quién paga: en ese mismo viaje, antes de aceptar, `GET /viajes/ofrecidos` cumple
  `esquemas/viaje.json` y trae el pedido en `pago_repartidor.por_pedido` con `cobros`, cuyos
  `envio` suman su `monto` (`docs/repartidores.md`, punto d).
- Retiro y entrega firmados: `retirarPedido` y `entregarPedido` con una `firma` que no verifica
  dan `422 firma_invalida` sin mover el pedido. Después, con la clave de la suite si la sesión
  salió de `/acceso` (custodia propia), o sin `firma` si el nodo custodia la clave, responden
  `200`, y `firmas.retiro` / `firmas.entrega` son del repartidor y verifican sobre el traspaso
  `{accion, pedido_id, repartidor, instante}` contra su historial (`docs/repartidores.md`,
  punto j). Si el nodo pide la firma y la suite no tiene la clave, se omite.
- Rendición del efectivo: entregado ese pedido en efectivo, `GET /pedidos/{id}` trae `rendicion`
  `pendiente` por lo que la repartidora cobró para el comercio. `declararRendicion` con una firma
  que no verifica da `422 firma_invalida`; bien firmada queda `declarada`, y `confirmarRendicion`
  con el mismo monto la deja `confirmada`. Las dos constancias son de su actor (la repartidora y
  el comercio) y verifican sobre `{accion, pedido_id, actor, monto, instante}`; otra más da
  `409 rendicion_confirmada` (`docs/repartidores.md`, punto l). Si una clave es de custodia propia
  y la suite no la tiene, se omite.
- Aceptar con tiempo: en el ciclo, `aceptarPedido` con `tiempo_preparacion_min` fuera de rango
  da `422` y no acepta; con `25` responde el pedido con `tiempo_preparacion_min: 25` y `eta` a
  25 minutos de la aceptación (±2 min: es retiro, sin ruta).
- Preparando: en el ciclo, el primer `resolverItemPedido` sobre el pedido `aceptado` lo deja
  `preparando` en `GET /pedidos/{id}`. Si antes de resolver no estaba `aceptado`, se omite.
- Eventos de quien administra: contra un nodo con custodia propia, una compradora nueva (de
  `/acceso`) compra en el comercio de prueba y el stream `GET /eventos` de la sesión de prueba,
  que lo administra, trae su `pedido.creado` en 15 s. Sin custodia propia se omite.
- Nombres del pedido: `PUT /yo/nombre` guarda el nombre sin los espacios de los bordes y
  `GET /yo` lo muestra; vacío, de puros espacios, de más de 80 caracteres, que no es texto o
  sin `nombre` da `422`; un token de mandato no lo escribe; `null` lo borra. Al final se
  restaura el de la sesión de prueba. Con custodia propia, una compradora nueva que entra sin
  nombre no tiene `nombre` en `GET /yo` (el nodo no pone el handle), elige uno y compra en el
  comercio de prueba: con el pedido activo, ella y quien administra el comercio ven su nombre
  en `partes.usuario`, y `partes.comercio` trae el del comercio; una tercera identidad recibe
  `404`. Cancelado, ella lo sigue viendo y el comercio (sin lista de clientes aceptada) ya no.
  Sin custodia propia, esa parte se omite.
- Abierto ahora: la ficha trae `abierto_ahora`; `apertura_manual` cerrada o abierta (con
  `hasta` a 30 min) se ve en la respuesta del `PATCH`, en `GET /comercios/{id}` y en
  `buscarComercios?abierto`; con el comercio cerrado, confirmar un carrito da `409
  comercio_cerrado`; con campos de más da `422`; `null` la quita y vuelve el
  `abierto_ahora` de antes. Corre al final y deja el comercio como estaba.
- Clips (`docs/medios.md`): con el comercio y la oferta de prueba, `PATCH` con un clip en
  `videos` responde `200` y `GET /comercios/{id}` y `GET /ofertas/{id}` lo devuelven tal
  cual; uno de 45 s o sin póster da `422` y no pisa el que estaba. Al final se restauran
  los clips que tenían.
- Fotos subidas al nodo (`docs/medios.md`), solo si el nodo publica `endpoints.medios`; si
  no, se omite: es opcional. `medios` cumple `CapacidadMedios`; con la sesión de prueba, una
  JPEG con EXIF y GPS se sube al comercio de prueba (`201`, `MedioSubido`) y su `url` sirve
  una JPEG sin esos metadatos; la misma foto otra vez da la misma `url`; una PNG se sube si
  `tipos` la lista. Texto con `Content-Type: image/jpeg` da `415 tipo_no_admitido`, un
  archivo de más de `limite_bytes` da `413 medio_muy_grande`, sin token `401`, y con custodia
  propia otra identidad da `403`. El tope por comercio no se prueba: llenarlo es caro.
- Equipo del comercio (`docs/equipo.md`), con custodia propia; si el nodo responde `501` en
  `verEquipo`, se omite. La dueña lee el equipo (`esquemas/equipo.json`) e invita con
  `pedidos` (`201`, con `codigo` y `enlace`); `exportar` como permiso da `422`. Una identidad
  nueva acepta con su sesión (`201`, con su identidad, el rol y los permisos) y el mismo código
  con otra da `410 invitacion_invalida`. El comercio aparece en su `GET /yo/comercios` con rol
  y permisos, y lee la bandeja; editar la ficha, las métricas, exportar e invitar le dan `403
  sin_permiso` (con `detalle.falta`). Sacar a la dueña da `403 sin_permiso`. La dueña la saca
  (`204`) y desde la llamada siguiente la bandeja le da `403 no_es_el_dueno` y el comercio ya
  no está en su lista. El techo del agente de un miembro no se prueba acá: pide un mandato de
  una identidad de la suite.
- Un viaje inventado en `GET /viajes/{id}` responde `404` con `esquemas/error.json`: lo mismo
  que un viaje ajeno, para no revelar cuáles existen.
- Reseña dentro de la ventana de 7 días y rechazada fuera de ella
  (`fuera_de_ventana_resena`), una por par.
- Mandato: tope por período (`pedir:<centavos>`, atómico bajo dos pedidos simultáneos),
  revocación inmediata, y que `POST /yo/claves/rotar` **nunca** se pueda invocar con un
  mandato de agente (`docs/claves-y-firmas.md`: "Rotar nunca se puede hacer por mandato").

**Nivel C — federación (la suite actúa como nodo par).**

- Idempotencia: el mismo `id` de evento con el mismo contenido responde `202` dos veces
  sin duplicar nada visible; con otro contenido, `409`.
- Orden: un salto de `secuencia` responde `409 secuencia_fuera_de_orden` con
  `detalle.ultima_secuencia`.
- Versión: una `Vereda-Version` que el nodo no soporta responde `400
  version_no_soportada` con `detalle.versiones`.
- Firma: el request entero verifica RFC 9421 contra la clave del emisor de prueba,
  reusando la mecánica exacta de `ejemplos/vectores-firma.json`.

## En qué se escribe

Python 3, el mismo stack que `validar.py` (`jsonschema` + `referencing`, `pyyaml`,
`rfc8785`, `cryptography`) más un cliente HTTP (`requests` o `httpx`). Nueva carpeta
`conformidad/` en la raíz, hermana de `esquemas/` y `ejemplos/` — no un repo aparte: la
suite es parte de "la spec ejecutable", igual que los ejemplos y los esquemas, y su ciclo
de vida es el de la spec, no el del nodo Go. El cargador de esquemas se factoriza a un
módulo chico que `validar.py` y `conformidad/` importan los dos, para no mantener dos
copias del mismo `Registry`.

`validar.py` sigue siendo el chequeo offline (la spec es consistente consigo misma);
`conformidad/` es el chequeo online (un nodo cumple la spec). Corren por separado y no se
mezclan: `validar.py` no necesita red y no debería empezar a necesitarla.

## Cómo se invoca contra una URL arbitraria

```
python3 -m conformidad https://vereda.ar
```

Por defecto corre solo el nivel A (no necesita nada más que la URL). Flags:

- `--nivel a,b,c` — repetible; agregar `b` o `c` sin las credenciales que piden falla
  rápido con un mensaje claro, no corre a medias.
- `--sesion <token>` / `--mandato <token>` — credenciales del actor de prueba, nivel B.
- `--clave-nodo-prueba <archivo>` — semilla Ed25519 del nodo par de prueba, nivel C; sin
  este flag deriva la de `ejemplos/vectores-firma.json`.
- `--solo <operationId o tag>` — correr un subconjunto (por ejemplo, solo `carrito`
  mientras se depura esa parte del nodo).
- `--formato texto|json` y `--salida <archivo>`.

Sale con `0` si todo lo corrido pasó, `1` si algo falló — igual que `validar.py`, para que
un CI (o el "criterio de salida de cada fase" que pide el plan) lo use como gate.

## Cómo reporta

En consola, el mismo lenguaje ✓/✗ de `validar.py`, agrupado por nivel y por
`operationId`, con el motivo en español citando el campo o el esquema que falló — no un
stack trace.

Con `--formato json`, una lista de casos: `{nivel, operationId, caso, resultado,
evidencia}`, donde `evidencia` es el request y la respuesta recortados a lo necesario para
reproducir. Nunca guarda tokens de sesión ni datos personales reales del nodo bajo prueba
en ese reporte, ni en nivel A ni en B.

El resumen final es por nivel: cuántos casos corrieron y cuántos pasaron en cada uno, y
"no corrido" para los niveles que no se pidieron — nunca un solo número global que mezcle
un nodo que solo se sometió al nivel A con uno que pasó los tres.

## Por qué no todo es automático

El nivel A es de solo lectura por construcción: no crea nada en el nodo bajo prueba, así
que se puede correr contra un nodo de producción real sin permiso de nadie, en cualquier
momento — es el nivel que responde "¿esta URL habla Vereda?". B y C mutan estado (crean
pedidos, mandatos, eventos de federación) y por eso exigen que el operador del nodo decida
correrlos, con credenciales de un entorno que él eligió para esto — nunca contra una
cuenta real. Es el mismo patrón que el "sandbox de conformidad antes de producción" de
Beckn/ONDC (`.claudedocs/plan-2026-09/5-arte-previo.md`, punto 2), sin su registro
central: acá no hay a quién pedirle el sandbox salvo al propio nodo.

## Qué queda fuera de este diseño

- **MCP** (`mcp/herramientas.json`) no entra: es otra interfaz sobre la misma capa de
  servicio, no HTTP público, y el plan no la incluye en la fase 1.
- **Prueba de carga** (fin de fase 3 y 6 en `docs/plan-implementacion.md`) es otra
  herramienta con otro objetivo (P99, memoria bajo tráfico simulado), no esta suite.
- **Dónde vive el repositorio de `conformidad/` a largo plazo** si crece mucho: por ahora
  en `protocolo-vereda`, junto a lo que genera sus casos. Si el volumen lo justifica,
  separarlo es una decisión de Leo, no de este PR.
- Ningún esquema, ruta ni regla nueva: este documento no agrega superficie al protocolo,
  solo decide cómo probarlo.
