# Identidad y verificación sin autoridad

La pregunta de Leo (2026-09-22): si nadie aprueba a nadie, ¿cómo se pelea que una persona o un
comercio se haga pasar por otro, o que aparezca un duplicado?

La respuesta del protocolo: **nadie garantiza quién es quién**. Lo que hace es que cada afirmación
de identidad se pueda comprobar por cualquiera, que fingirla cueste, y que la reputación no se pueda
copiar. Un impostor puede elegir el mismo nombre; no puede tener el dominio, el Instagram, el local,
la cuenta de cobro ni los clientes del verdadero.

Este documento define cómo. Todo lo que dice existe primero como API (`openapi.yaml`) y como
herramienta MCP (`mcp/herramientas.json`); ninguna parte depende de una pantalla.

## 1. Principios

- **Sin verificadores, en ningún paso.** El protocolo no tiene humanos ni agentes que revisen,
  aprueben, arbitren o decidan nada sobre la identidad de nadie: ni el operador del nodo, ni un
  equipo de Vereda, ni un agente de IA. Cada estado de este documento sale de una prueba automática
  que el nodo comprueba solo y que cualquiera puede rehacer. Lo que no se puede resolver con
  evidencia automática queda a la vista como **sin prueba** y pesa cero.

- **La clave es la identidad.** `actor@nodo` y su historial de claves (`docs/claves-y-firmas.md`).
  Nadie puede firmar por otro: ni un impostor, ni el operador de otro nodo. Lo que alguien firmó, lo
  firmó él.
- **El nombre visible no prueba nada y no es único.** Dos comercios pueden llamarse igual. El
  protocolo no reserva nombres ni los asigna: los muestra junto con la evidencia (punto 3).
- **Ninguna verificación la otorga un tercero.** No hay tilde azul, ni sello "verificado por
  Vereda", ni una persona que revise documentos. En ningún esquema existe un campo así. Lo que hay son
  **pruebas**: el actor publica algo en un lugar que solo él controla, y cualquiera va y lo mira.
- **Todo se muestra y cualquiera lo recomprueba.** El nodo comprueba y firma su veredicto, pero no hay
  que creerle: cada prueba dice cómo rehacerla, y la mayoría se rehace sin preguntarle nada al nodo.
- **La reputación no se copia.** Reseñas, recompra y crédito de identidad (`docs/resenas.md`) cuelgan
  de la clave, no del nombre. El duplicado nace con cero pedidos entregados, y eso se ve.
- **La evidencia decide; el protocolo no borra ni elige.** Nada de este documento oculta un perfil,
  lo baja en el ranking ni le cambia la reputación. Lo único que cambia es lo que ve quien va a
  comprar, y eso alcanza para decidir.

## 2. Vinculaciones verificables

Una **vinculación** es una cuenta o un lugar del mundo que el actor dice que es suyo: su dominio, su
sitio, su Instagram, su WhatsApp, su local, su cuenta de cobro. Es `comunes.json#/$defs/vinculacion`,
va en la ficha pública (`comercio.vinculaciones`, `repartidor.vinculaciones`) y en
`GET /actores/{identidad}/verificacion`.

Tiene dos partes que escriben dos autores distintos:

- **La declaración** (`id`, `identidad`, `tipo`, `valor`, `declarada`), firmada por el actor con su
  clave. Dice "esto es mío".
- **Las señales** (`senales`), que escribe el nodo al comprobar: estado, cuándo se verificó, cuándo se
  comprobó por última vez, atestaciones. Quedan fuera de la firma, igual que las señales de una reseña
  (`docs/claves-y-firmas.md`, los campos que no escribió el firmante).

### El código de prueba

Cada declaración tiene un código que se deriva de ella y de nada más:

```
codigo = base64url( SHA-256( JCS(declaración sin 'firma' ni 'senales') )[0:16] )
texto  = "vereda:prueba=" + codigo
```

Son 22 caracteres: entran en un registro DNS, en la biografía de Instagram y en el pie de una página.
Como el código sale del hash de una declaración que nombra a **esa** identidad, copiar el código de
otro no sirve: prueba que la cuenta es del otro. `ejemplos/vectores-firma.json` trae el vector
`vinculacion-dominio-con-codigo` para reproducirlo byte por byte.

### Cómo se prueba cada tipo

| `tipo` | `valor` (público) | Dónde se publica la prueba | Cómo lo comprueba el nodo | Cómo lo recomprueba cualquiera |
| --- | --- | --- | --- | --- |
| `dominio` | `lahuerta.com.ar` | Registro DNS TXT en `_vereda.lahuerta.com.ar` con el texto | Consulta DNS | La misma consulta DNS, desde cualquier lado |
| `sitio` | `https://lahuerta.com.ar/contacto` | El texto en cualquier parte del cuerpo de esa página | `GET` por HTTPS | El mismo `GET`, o abrir la página y buscar el texto |
| `instagram` | `@lahuerta` | El texto en la biografía del perfil | Lee el perfil público | Abrir el perfil y comparar el código |
| `whatsapp` | `+5493415551234` | El nodo manda un código de desafío a ese número; el actor lo devuelve con `comprobarVinculacion`. Se recomienda además el texto en la descripción del perfil de empresa | Desafío | Escribirle al número y mirar la descripción. Si no está, queda el veredicto firmado del nodo |
| `local` | opcional: la ubicación ya está en la ficha | Un QR impreso en el local (abajo) | Cuenta atestaciones de presencia | Leer las atestaciones públicas y rehacer la cuenta |
| `cuenta_cobro` | nunca: la cuenta es privada | El titular que ve cada comprador en su banco al transferir (abajo) | Cuenta veredictos de compradores | Los números están en el pago y en la verificación |

`dominio`, `sitio` e `instagram` se recomprueban solos cada 7 días, y cuando el dueño lo pide
(`POST /actores/{identidad}/vinculaciones/{id}/comprobar`). `whatsapp` se renueva con un desafío nuevo
cada 180 días. Un nodo publica en `/.well-known/vereda.json` (`vinculaciones`) qué tipos sabe
comprobar; declarar uno que no, responde 422 `vinculacion_no_soportada`.

Al leer un sitio o un perfil, el nodo va solo por HTTPS, solo a direcciones públicas, con 5 segundos,
1 MB y 3 redirecciones como máximo. No es una cortesía: sin eso, una vinculación sería una forma de
hacer que el nodo pida URLs internas.

### Estados

`senales.estado`, calculado por el nodo:

| Estado | Cuándo |
| --- | --- |
| `pendiente` | Declarada, sin prueba encontrada todavía |
| `verificada` | La última comprobación encontró la prueba; en `local` y `cuenta_cobro`, las atestaciones pasan el umbral |
| `caida` | Estaba verificada y dos comprobaciones seguidas no encontraron la prueba. Vuelve a `verificada` sola si la prueba reaparece |
| `vencida` | Siguió `pendiente` 7 días, o un `whatsapp` pasó 180 días sin renovar el desafío |
| `contradicha` | Solo `cuenta_cobro`: los compradores dicen, con más peso, que el titular no coincide |

Solo `verificada` cuenta. `pendiente`, `caida` y `vencida` se muestran como **sin prueba** y pesan
cero en todo lo demás: no vinculan, no sirven para reclamar y no respaldan una denuncia.

Nada se borra: una vinculación caída o vencida sigue en el historial de
`GET /actores/{identidad}/verificacion`, con sus fechas. La ficha muestra las que no están vencidas.

### Local: el QR y las atestaciones de presencia

Al declarar una vinculación `local`, el nodo genera un secreto y lo devuelve **una sola vez**, dentro
del contenido del QR para imprimir:

```
vereda:presencia?actor=lahuerta@vereda.ar&vinculacion=<id>&s=<secreto>
```

El cliente que lo escanea en el local firma una **atestación de presencia**
(`comunes.json#/$defs/atestacion`, `tipo: presencia`) con su propia clave: "estuve acá". Lleva
`prueba = base64url(HMAC-SHA256(secreto, autor + "\n" + vinculacion))`, así el nodo sabe que quien
firma vio el QR sin que el secreto quede publicado en ninguna atestación.

- La app no manda la ubicación de la persona. La prueba es haber visto el QR, no un GPS.
- Una prueba que no corresponde al QR vigente responde 422 `prueba_invalida`. Una atestación por
  autor por vinculación: repetir responde 409 `atestacion_repetida`.
- **Son públicas y firmadas, como una reseña** (`GET /actores/{identidad}/atestaciones`). Es la única
  forma de que el conteo se pueda rehacer. La app lo dice antes de que la persona firme.
- Cada atestación pesa el **crédito de identidad** `k` de su autor (`docs/resenas.md`). Pesa `0` si
  el autor es el dueño o una identidad vinculada al comercio, con las mismas reglas que una reseña, y
  también si el autor no tiene ningún pedido entregado en la red.
- La vinculación queda `verificada` con **3 o más autores distintos que computan y peso total ≥ 2,0**.

Un QR se puede fotografiar y circular. Por eso cuenta el peso y no la cantidad. Crear identidades es
gratis, así que una identidad sin pedidos no suma nada; con un pedido entregado en un solo comercio
pesa `0,25`. Para llegar a `2,0` con identidades así hacen falta ocho, cada una con un pedido pagado y
entregado; dos vecinos con historia (`k = 1`) llegan solos. Si el comercio sospecha que su QR circula,
declara otra vinculación `local`, imprime el QR nuevo y la vieja queda en el historial con sus
atestaciones.

### Cuenta de cobro: el titular

La cuenta de cobro nunca es pública (`docs/datos-y-privacidad.md`). Lo que sí se comprueba es lo que
importa para no transferirle a un estafador: **que el titular del alias sea quien dice el comercio**.

1. Al pagar por transferencia, el comprador recibe en `pago.instrucciones` el alias, el `titular`
   declarado por el comercio, lo que dijeron los compradores anteriores (`comprobacion_titular`) y
   una `advertencia` para mostrar tal cual.
2. Su banco le muestra el titular real del alias antes de confirmar. La app le pregunta si coincide.
3. Al declarar la transferencia (`POST /pedidos/{id}/transferencia`), manda `titular_coincide`.

El nodo guarda **solo el veredicto** (sí o no, del comprador de ese pedido), nunca lo que el banco le
mostró. Con compradores distintos de los últimos 90 días, pesados por su `k`:

- `verificada` si el peso de "coincide" es ≥ 1,0 y mayor que el de "no coincide";
- `contradicha` si el peso de "no coincide" es ≥ 1,0 y mayor o igual que el de "coincide";
- `pendiente` en cualquier otro caso.

Solo puede opinar quien transfirió de verdad en un pedido de ese comercio: una campaña para ensuciar
el titular de alguien cuesta pedidos pagados. `comercio.verificacion.cuenta_cobro_coincide` es este
estado resumido a un booleano. Lo mismo vale para el repartidor cuando le pagan el envío por
transferencia (`concepto: envio`).

## 3. Duplicados y vinculados

Dos casos distintos, con el mismo criterio: detectarlos es determinista, el resultado es público, y
nadie borra ni elige.

### Vinculados

Dos comercios están **vinculados** si comparten cualquiera de estas cosas:

| `por` | Qué comparten |
| --- | --- |
| `dueno` | La misma persona los administra |
| `cuit` | El mismo CUIT |
| `cuenta_cobro` | El mismo alias o la misma referencia de PSP |
| `clave` | Una clave pública en sus historiales |
| `vinculacion` | La misma vinculación verificada: mismo dominio, sitio, Instagram o WhatsApp |

Son hechos que el nodo ya tiene. Se publican en `verificacion.vinculados` de los dos lados con el
**criterio**, nunca el valor: se ve que dos comercios comparten CUIT, no cuál es.

Efecto: el que ya fija `docs/resenas.md`, y ninguno más. Las reseñas y atestaciones entre vinculados
pesan `0` y se publican marcadas. Las sucursales de una cadena quedan vinculadas por `dueno`, y está
bien: es exactamente lo que quien compra tiene que saber.

Una persona también queda vinculada a un comercio si confirmó el mismo teléfono o email que su dueño
(punto 4). Eso solo hace que sus reseñas y atestaciones a ese comercio pesen `0`; no se publica en
ninguna lista, porque dos personas que comparten un teléfono no tienen por qué contárselo a nadie.

### Mismo nombre cerca

Dos comercios tienen **el mismo nombre cerca** si:

1. su nombre normalizado —NFKD, sin diacríticos, en minúsculas, solo letras y dígitos— es igual, o
   está a una edición de distancia cuando tiene 6 caracteres o más ("La Huerta" y "La Huertaa"); y
2. sus ubicaciones están a 1.500 m o menos, la escala de barrio de `docs/resenas.md`; y
3. no están vinculados (esos ya se muestran arriba).

**Un homónimo nunca es un error.** Dos "Verdulería de Marta" pueden ser dos verdulerías reales, y
las dos tienen derecho a llamarse así. Ninguna se bloquea, ninguna se renombra y ninguna pierde
posición. Cada una aparece en `verificacion.mismo_nombre_cerca` de la otra, con lo que alcanza para
distinguirlas sin preguntarle a nadie: antigüedad (`alta`), pedidos entregados, vinculaciones
verificadas y distancia redondeada a 100 m. Con eso la app puede avisar "hay otro comercio con el
mismo nombre a 300 m" y mostrar los dos.

### La evidencia decide

El protocolo no decide cuál es el verdadero. Pone a los dos uno al lado del otro: uno con dos años,
800 pedidos entregados, su dominio y su local verificados; el otro con tres días, cero pedidos y
ninguna vinculación. Quien compra no necesita que nadie le diga cuál es cuál.

Nada de esto toca el ranking (`docs/ranking-y-despacho.md`) ni la reputación: si una marca pudiera
bajar a alguien, sería un arma para la competencia desleal. El duplicado ya pierde solo, porque no
tiene lo único que no se copia: pedidos entregados y gente que vuelve.

## 4. Personas

Una persona no tiene dominio ni local. Lo que la hace creíble es el historial, y eso ya existe.

- **Historial.** `verificacion.historial`: fecha de alta, pedidos entregados, comercios distintos a
  los que les compró y su crédito de identidad `k` (`docs/resenas.md`). Son agregados: `mi_vereda`
  sigue siendo privada, y no se publica a qué comercios les compró.
- **Contacto confirmado.** `POST /yo/contacto` manda un código de 6 dígitos por SMS, WhatsApp o
  email (vence a los 10 minutos, 5 intentos); `POST /yo/contacto/confirmar` lo devuelve. El nodo
  guarda `HMAC-SHA256(sal secreta del nodo, valor normalizado)` —E.164 para el teléfono, minúsculas
  para el email— y el instante. **Nunca el valor.** Afuera se publica solo `contacto.telefono: true`.
  El hash sirve para una cosa: saber si dos identidades de este nodo confirmaron el mismo contacto
  (vinculadas, punto 3). Con otra sal en cada nodo, el hash no sirve para cruzar nodos, a propósito.
  Si la persona quiere que un comercio la llame, eso es `privado.telefono`, aparte y con sus propias
  reglas de retención.
- **Cliente frecuente.** Un comercio puede firmar una atestación `cliente_frecuente` sobre una persona
  que tiene 3 o más pedidos entregados en él (si no, 422 `sin_pedidos_suficientes`). No se publica
  hasta que la persona la acepta (`POST /yo/atestaciones/{id}/consentimiento`); si la rechaza, no se
  publica nunca. Es opcional para las dos partes y no cambia ningún peso: solo suma al historial que
  se muestra.

Nada de esto es obligatorio para comprar. Una persona sin contacto confirmado ni historial compra
igual; lo que cambia es cuánto pesan sus reseñas, que ya lo decide `k`.

El repartidor tiene las dos cosas: vinculaciones (`sitio`, `instagram`, `whatsapp`, y
`cuenta_cobro` por el titular del envío) y el historial de una persona, que en su caso ya muestran
`viajes_completados` y `viajes_soltados` (`docs/repartidores.md`, punto e).

## 5. Denuncia de suplantación

Cuando alguien ve un perfil que se hace pasar por otro, lo denuncia: `esquemas/denuncia.json`.

- **La firma quien denuncia**, con su clave y su sesión. Nunca por mandato: igual que una reseña, es
  una afirmación de la persona.
- **Dice qué reclama.** `denunciado` es el perfil que imita; `suplantado`, a quién imita (puede ser el
  mismo denunciante u otro); `reclama` es la vinculación que prueba quién es el verdadero —"el
  dominio `lahuerta.com.ar` es de `lahuerta@vereda.ar`"—, y `texto` lo cuenta en 1000 caracteres.
- **Es pública y va pegada al perfil denunciado** (`GET /actores/{identidad}/denuncias`), junto con
  el crédito `k` de quien denuncia. No se edita ni se borra.
- **El denunciado responde**, público y firmado, una vez (`respuesta`, como en una reseña).
- **No hay arbitraje.** Nadie la acepta ni la rechaza. El nodo calcula su estado cada hora con un
  criterio publicado, en `senales`, fuera de la firma:

| `senales.estado` | Cuándo |
| --- | --- |
| `respaldada` | El suplantado tiene verificada la vinculación reclamada y el denunciado no |
| `contradicha` | El denunciado tiene verificada la vinculación reclamada y el suplantado no |
| `abierta` | Ninguna de las dos, y no pasaron 14 días |
| `sin_respaldo` | Pasaron 14 días y sigue sin ser respaldada ni contradicha |

El estado cambia solo si cambia la evidencia: si el suplantado verifica su dominio el día 20, la
denuncia pasa a `respaldada` el día 20. Una denuncia sin evidencia termina `sin_respaldo` y sigue
visible con esa marca, que también es información.

Una sola denuncia por par denunciante–denunciado (409 `denuncia_repetida`). No hay efecto en ranking,
reputación ni despacho, por la misma razón que en el punto 3: una denuncia que bajara a alguien sería
el arma más barata del sistema.

## 6. Reclamar una ficha

Como el "reclamá este negocio" de Google, pero sin nadie del otro lado. Sirve cuando alguien creó una
ficha de mi comercio —un empleado que se fue, un vecino con buena intención, un impostor— y la quiero
a mi nombre.

1. **Reclamo.** `POST /comercios/{id}/reclamos` (`esquemas/reclamo.json`), con sesión y firmado por
   el reclamante, nunca por mandato. Dice con qué va a probar:
   - `local`: un QR propio del reclamo, que el nodo devuelve una sola vez, para imprimir en la
     ubicación de la ficha. Los clientes que lo escanean firman presencia, igual que en el punto 2.
   - `dominio`, `sitio`, `instagram` o `whatsapp`: **solo una vinculación que la ficha ya declara y
     que el dueño actual no tiene verificada**. Si no, 422 `prueba_no_admitida`. Sin esta regla,
     cualquiera se quedaría con cualquier ficha probando un dominio propio que nada tiene que ver.
   - `cuenta_cobro`, no: la cuenta es privada y su titular solo lo ve quien le transfiere, así que no
     hay nada que el reclamante pueda publicar.
2. **Prueba.** El texto es el mismo del punto 2 —`vereda:prueba=` más el código derivado del
   reclamo firmado—, así que prueba que el dominio o el Instagram es **del reclamante**. En
   `whatsapp`, el desafío al número. En `local`, hacen falta **5 o más autores distintos que computan
   y peso ≥ 3,0**, más que para una vinculación propia porque se trata de sacarle la ficha a alguien.
3. **Resolución, sola.** El nodo comprueba cada día, y cuando el reclamante lo pide
   (`comprobarReclamo`). El estado va en `senales`:

| `senales.estado` | Cuándo |
| --- | --- |
| `abierto` | Todavía sin prueba, dentro de los 30 días |
| `resuelto` | El reclamante probó y el dueño actual no tiene verificada esa misma vinculación (en `local`: ninguna `local` verificada) |
| `contradicho` | El dueño actual tiene verificada esa misma vinculación: la ficha ya está probada por quien la tiene |
| `vencido` | Pasaron 30 días sin prueba. Vence solo, sin que nadie lo cierre |

4. **Cambio de dueño.** Al resolverse, la ficha pasa a la clave del reclamante, en el acto:
   - la clave del comercio pasa a `retirada` y la nueva entra al historial con `reclamo` (el id del
     reclamo que la instaló), sin aval de la anterior (`docs/claves-y-firmas.md`);
   - se revocan los mandatos y las sesiones de administración del dueño anterior;
   - todo lo firmado antes sigue valiendo: pedidos, reseñas, respuestas. La reputación es del
     comercio, no de quien lo administraba;
   - la ficha queda marcada para siempre: `verificacion.reclamos.ultimo_cambio_de_dueno`, el reclamo
     resuelto en `GET /comercios/{id}/reclamos` y el evento `reclamo.resuelto`.
5. **Defensa, también automática.** El dueño actual recibe `reclamo.recibido`. Para defenderse no le
   escribe a nadie: verifica la vinculación reclamada, o su local, y el reclamo queda `contradicho`.
   Si pierde la ficha y era suya, reclama de vuelta con las mismas reglas.

Un reclamo abierto por reclamante y ficha (409 `reclamo_abierto`). Mientras está abierto no cambia
nada de la ficha: se ve en `verificacion.reclamos.abiertos` y nada más.

## 7. Qué recibe la app

El contrato de datos. Cómo se ve lo decide Leo; lo que sigue es qué datos tiene la app para mostrar y
en qué momento, sin pedir nada extra.

| Dónde | Qué dato | Para qué |
| --- | --- | --- |
| Ficha del comercio (`verComercio`) | `vinculaciones[]` con `senales.estado` | Qué probó este comercio y qué no |
| `GET /actores/{identidad}/verificacion` | `vinculados`, `mismo_nombre_cerca`, `denuncias` (conteo por estado), `historial`, `contacto`, `atestaciones` | Distinguir al verdadero del duplicado sin salir de la ficha |
| `GET /actores/{identidad}/denuncias` | Cada denuncia, con su respuesta y su estado | Leer las dos versiones y la evidencia |
| `pago.instrucciones` | `titular`, `comprobacion_titular`, `advertencia` | Advertir **antes** de transferir. La `advertencia` se muestra tal cual |
| `declararTransferencia` | `titular_coincide` | Recoger el veredicto del comprador |
| `verificacion.mismo_nombre_cerca` | Nombre, distancia, antigüedad, pedidos, pruebas | Avisar "hay otro con el mismo nombre a 300 m" y mostrar los dos |
| `GET /comercios/{id}/reclamos` | Reclamos con su prueba y su estado | Ver si la ficha cambió de dueño, cuándo y con qué prueba |

Ante una denuncia, la app muestra la verificación de los dos perfiles —denunciado y suplantado— lado
a lado: los datos son las dos respuestas de `GET /actores/{identidad}/verificacion`.

## 8. Entre nodos

- **Cada nodo responde por las vinculaciones de sus actores**, como responde por sus claves
  (`docs/federacion.md`). `GET /actores/{identidad}/verificacion` va firmado por el nodo (`firma`, con
  su dominio como firmante) y se cachea por ETag como cualquier lectura pública. Cada declaración
  adentro sigue firmada por el actor.
- Otro nodo puede **rehacer** las pruebas de `dominio` y `sitio` por su cuenta, sin creerle al nodo
  del actor; y las atestaciones y denuncias están firmadas por sus autores, verificables contra el
  historial de claves de cada uno.
- `vinculados` y `mismo_nombre_cerca` se calculan dentro de cada nodo: CUIT y cuenta de cobro no se
  federan, y un nodo no conoce los nombres de todos los demás.
- **Mudanza.** Las declaraciones viajan en `GET /yo/exportar` con su firma. El nodo nuevo las publica
  y las vuelve a comprobar desde cero (`pendiente`): el veredicto del nodo viejo no se hereda. Las
  atestaciones y denuncias recibidas viajan firmadas por sus autores.
- Una denuncia contra un actor de otro nodo se hace en el nodo del denunciado, que verifica la firma
  del denunciante contra su historial remoto. Mientras la prioridad sea un solo nodo, ambos viven en
  el mismo.

## Superficie de API

| Operación | Quién | Qué |
| --- | --- | --- |
| `GET /actores/{identidad}/verificacion` | Público, con caché | Todo lo de este documento sobre un actor, firmado por el nodo |
| `POST /actores/{identidad}/vinculaciones` | El actor o el dueño del comercio (sesión, o mandato `administrar` / `repartir`) | Declarar. Devuelve el texto a publicar y, en `local`, el QR |
| `POST /actores/{identidad}/vinculaciones/{id}/comprobar` | Ídem | Comprobar ahora; en `whatsapp`, con el código del desafío |
| `GET /actores/{identidad}/atestaciones` | Público, con caché | Atestaciones visibles sobre el actor |
| `POST /actores/{identidad}/atestaciones` | Sesión (presencia); sesión o mandato `administrar` (cliente frecuente) | Atestiguar |
| `POST /yo/atestaciones/{id}/consentimiento` | La persona atestiguada, con sesión | Aceptar o rechazar un "cliente frecuente" |
| `POST /yo/contacto` · `POST /yo/contacto/confirmar` | Sesión | Confirmar teléfono o email por desafío |
| `GET /actores/{identidad}/denuncias` | Público, con caché | Denuncias contra el actor |
| `POST /actores/{identidad}/denuncias` | Sesión, nunca mandato | Denunciar |
| `POST /actores/{identidad}/denuncias/{id}/respuesta` | El denunciado (sesión, o mandato `administrar` / `repartir`) | Responder una vez |
| `GET /comercios/{id}/reclamos` | Público, con caché | Reclamos de propiedad sobre la ficha |
| `POST /comercios/{id}/reclamos` | Sesión, nunca mandato | Reclamar la ficha. Devuelve el texto a publicar o el QR |
| `POST /comercios/{id}/reclamos/{reclamo}/comprobar` | El reclamante, con sesión | Comprobar ahora; se resuelve en el acto si prueba |

Cambios en lo que ya existía: `vinculaciones` en `comercio.json` y `repartidor.json`,
`contacto_confirmado` en `usuario.json`, `comprobacion_titular` y `advertencia` en
`pago.instrucciones`, `titular_coincide` en `declararTransferencia`, `vinculaciones` en
`/.well-known/vereda.json`, `reclamo` en la entrada de clave, y los eventos `vinculacion.*`,
`atestacion.recibida`, `denuncia.*` y `reclamo.*`
(`docs/eventos.md`).
