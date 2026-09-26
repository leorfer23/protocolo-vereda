# Acceso: entrar sin que nadie te deje entrar

En Vereda nadie aprueba usuarios. No hay alta que alguien revise ni contraseña. Con
**custodia propia** la identidad de una persona es una clave Ed25519 que genera en su
dispositivo, y entrar a un nodo es probar que la tiene. Con **custodia del nodo** la clave
la guarda el nodo, y el nodo puede ofrecer entrar con un código por mensaje.

Esta página es el contrato entre una app y cualquier nodo: cómo se entra, qué clave abre
sesión, cómo se guarda la clave en el dispositivo y cómo se la lleva a otro. Una app nativa
que la cumple funciona contra cualquier nodo conforme.

## Dónde vive: `/acceso`, fuera de `/v1`

Las rutas de acceso cuelgan de la raíz del dominio (`https://{nodo}/acceso/...`), no de
`/v1`. En `openapi.yaml` lo dicen con un `servers` propio en cada ruta, y están bajo el tag
`acceso`.

Por qué afuera:

- **Es cómo se consigue la credencial de `/v1`, no una operación de `/v1`.** Una `/v2` el día
  de mañana usa las mismas sesiones; si el acceso fuera parte de una versión, cambiar de
  versión obligaría a volver a entrar.
- **Es lo que ya sirven el nodo de referencia y su SDK.** Moverlo rompería a los clientes que
  existen sin ganar nada.
- **No es para agentes.** Un agente nunca entra por `/acceso`: actúa con un mandato que la
  persona le otorga desde su sesión (`docs/mandatos.md`,
  `esquemas/mandato.json`). Por eso tampoco hay herramienta MCP de acceso: el servidor MCP
  autentica con el mandato.

Qué ofrece cada nodo lo dice `acceso` en `/.well-known/vereda.json`
(`esquemas/acceso.json#/$defs/capacidades`):

```json
{ "acceso": { "custodia_propia": true, "alternativo": ["email"] } }
```

Una app mira eso antes de ofrecer la entrada. Un nodo que publica `custodia_propia: true`
tiene que servir el flujo de abajo tal cual; la suite de conformidad lo prueba en el nivel B.

## 1. Custodia propia: desafío, firma, sesión

```
dispositivo                                 nodo
  |  genera (o ya tiene) su par Ed25519       |
  |---- POST /acceso/desafio ---------------->|  guarda el desafío (pocos minutos, un solo uso)
  |<--- 201 { desafio, vence, nodo } ---------|
  |  firma JCS {clave_publica, desafio, nodo} |
  |---- POST /acceso/sesion ----------------->|  verifica, quema el desafío,
  |                                           |  crea el usuario si la clave es nueva
  |<--- 201 { token, vence, identidad,        |
  |           nuevo, usuario } ---------------|
  |---- GET /v1/yo   Authorization: Bearer -->|
```

**Pedir el desafío.** `POST /acceso/desafio` con `{ "clave_publica": "<base64url>" }`.
Responde `201 { desafio, vence, nodo }`. Responde igual para una clave conocida que para una
nueva: la ruta no sirve para averiguar quién tiene cuenta. El desafío tiene al menos 128 bits
de azar, es de un solo uso y vence pronto (2 minutos en el nodo de referencia).

**Firmar.** El dispositivo firma con Ed25519 el JCS (RFC 8785) de:

```json
{ "clave_publica": "…", "desafio": "…", "nodo": "vereda.ar" }
```

`nodo` es el que vino en el desafío: ata la firma a ese nodo, y una firma capturada no sirve
en otro. `clave_publica` ata el desafío a la clave que lo pidió. La firma va en base64url sin
relleno, como toda firma del protocolo. Los bytes exactos del JCS están en
`ejemplos/vectores-acceso.json` → `prueba_de_clave`; la firma de ese vector se verifica, no
se reproduce: CryptoKit en iOS firma Ed25519 con azar, y su firma, distinta, vale igual.

**Canjear.** `POST /acceso/sesion` con `{ clave_publica, desafio, firma, nombre? }`. Responde
`201` con `esquemas/acceso.json#/$defs/sesion`:

```json
{ "token": "…", "vence": "2026-10-22T13:00:36Z", "identidad": "6l2jezbsouyuvlza@vereda.ar",
  "nuevo": true, "usuario": { "…": "esquemas/usuario.json" } }
```

- `nombre` es el nombre que se muestra y solo se usa si la clave es nueva. Volver a entrar no
  lo pisa.
- `nuevo: true` dice que el usuario se creó en este canje, con `custodia_clave: propia`.
- El token va en `Authorization: Bearer <token>` en todo `/v1`.

**Renovar.** `POST /acceso/renovar` con la sesión. Devuelve `{ token, vence }` y el token
viejo deja de valer en el mismo momento: es la misma sesión con otro token (punto 6).

**Cerrar.** `DELETE /acceso/sesion` con la sesión. `204`, y el token deja de valer. La clave
se queda en el dispositivo.

Renovar y cerrar son de la persona: un token de mandato recibe `403`. Cuánto dura una sesión
lo decide cada nodo (30 días en el de referencia) y lo dice `vence`.

### Qué rechaza el canje

| Qué pasó | Respuesta |
| --- | --- |
| Falta el desafío o la firma, o la clave no es Ed25519 en base64url | `422 cuerpo_invalido` |
| El desafío no existe, ya se usó, venció o se emitió para otra clave | `401 no_autenticado`, sin decir cuál |
| La firma no verifica | `401 firma_invalida` |
| La clave está `retirada` en el historial del actor | `401 clave_rotada` |
| La clave está `comprometida` | `401 clave_comprometida` |
| Demasiados pedidos desde la misma IP (`topes.acceso_por_minuto_por_ip`, `docs/topes.md`) | `429 tope_alcanzado` con `Retry-After` |

Una firma que no verifica **no gasta** el desafío: un error no obliga a pedir otro. Una que
verifica lo gasta antes de emitir el token, de forma atómica: dos canjes simultáneos del mismo
desafío no ganan los dos.

### Qué clave abre sesión

**Solo la `activa` del historial** (`docs/claves-y-firmas.md`).

- `retirada` → `clave_rotada`. Rotar es cerrarle la puerta a la clave vieja: es lo que hace la
  persona cuando pierde un dispositivo. Si la retirada siguiera entrando, rotar no serviría.
- `comprometida` → `clave_comprometida`. Quien la tenga, no entra.

Que una clave no abra sesión **no invalida lo que firmó antes**: eso lo resuelve la
verificación de firmas, no el acceso. Una es "¿esto lo firmó esa persona?", la otra es
"¿quién puede entrar hoy?".

La consecuencia práctica: la persona rota desde el dispositivo que tiene la clave activa, y
los demás dispositivos dejan de entrar hasta que reciben la clave nueva (punto 4). Es el
rasgo, no el defecto.

### Qué identidad te toca

La identidad la acuña el nodo; el protocolo solo exige que sea `actor@nodo`
(`comunes.json#/$defs/identidad`) y que no cambie en los accesos siguientes con la misma
clave. **Recomendado**, y lo que hace el nodo de referencia: derivarla de la clave.

```
base32(SHA-256(clave_pública_cruda)[:10]), sin relleno y en minúscula  +  "@"  +  dominio
```

Una identidad derivada no se la puede llevar otro, y no hay nombres lindos que alguien tenga
que arbitrar en un alta sin portero. El nombre que se muestra es `nombre`. Vector:
`ejemplos/vectores-acceso.json` → `identidad_derivada`.

Una app no puede asumir la regla: usa la `identidad` que devuelve el canje.

## 2. Custodia del nodo: código o enlace por mensaje (opcional)

Un nodo puede guardar la clave de sus usuarios (`custodia_clave: nodo` en
`esquemas/usuario.json`) y dejarlos entrar con un código por email, WhatsApp o SMS. Es
**opcional por nodo**: lo ofrece quien lista el canal en `acceso.alternativo`, y el proveedor
que manda el mensaje lo elige cada nodo. La spec fija solo el contrato:

1. `POST /acceso/codigo` con `{ canal, valor }` (`canal`: `email`, `whatsapp` o `sms`;
   `valor`: el email o el teléfono en E.164). Responde `202` exista o no una cuenta con ese
   contacto. El mensaje trae un código de 6 dígitos, un enlace, o los dos. El enlace lleva
   un código largo y abre la app o la web del nodo, que hace el paso 2 por la persona.
2. `POST /acceso/codigo/canje` con `{ canal, valor, codigo, nombre? }`. Responde `201` con la
   misma `sesion` del punto 1. Si el contacto es nuevo, el usuario se crea con custodia del
   nodo y el contacto queda confirmado.

El código vence a los 10 minutos y admite cinco intentos; después hay que pedir otro. Todo
rechazo del canje es `401 no_autenticado`. Un nodo que no ofrece el canal responde
`501 no_implementado`.

Una cuenta con custodia del nodo puede pasar a custodia propia rotando
(`POST /v1/yo/claves/rotar` con la entrada nueva generada en el dispositivo): desde ahí entra
por el punto 1.

## 3. La clave en el dispositivo

La clave es la identidad. No hay portero, así que nadie puede recuperártela: perder el
dispositivo no puede ser perderla. Por eso la semilla es **extraíble a propósito**, pero solo
sale del dispositivo cifrada con una frase (punto 4).

Cada dispositivo guarda:

| Qué | Cuánto mide | Se sincroniza |
| --- | --- | --- |
| Semilla Ed25519 (firma y acceso) | 32 bytes | **No.** Nunca por la nube de la plataforma. Solo en un respaldo cifrado con frase |
| Clave privada X25519 del chat (`clave_cifrado` en `docs/claves-y-firmas.md`) | 32 bytes | Igual que la semilla, en el mismo respaldo |
| Identidad activa y su nodo | texto | Puede, no es secreta |
| Token de sesión | texto | **No.** Cada dispositivo abre la suya |

Recomendación (no obligación) por plataforma:

- **iOS.** Keychain, `kSecClassGenericPassword`, con
  `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`: no viaja al llavero de iCloud ni se restaura
  en otro iPhone desde un backup. El Secure Enclave no maneja Ed25519 ni X25519 (solo P-256),
  así que la clave no puede vivir adentro; se puede usar una clave P-256 del Secure Enclave
  para cifrar la semilla antes de guardarla, y pedir Face ID o Touch ID
  (`SecAccessControl` con `.userPresence`) para las firmas que importan.
- **Android.** Una clave AES-256-GCM en Android Keystore (StrongBox si el equipo lo tiene)
  cifra la semilla, y el resultado se guarda en el almacenamiento privado de la app, excluido
  del Auto Backup (`dataExtractionRules`). Una clave generada adentro del Keystore no se puede
  exportar, y lo que no se puede exportar no se puede respaldar: por eso el Keystore envuelve
  la semilla en vez de tenerla.
- **Web.** IndexedDB `vereda`, almacén `claves`, `keyPath: "identidad"`, filas
  `{ identidad, clave_publica, llave?, privada?, creada }`. `llave` es un `CryptoKey` Ed25519
  **no extraíble** (WebCrypto): firma, pero ni un script ajeno en la página puede leerlo.
  `privada` es la semilla como `Uint8Array` de 32 bytes y queda solo hasta que la persona guarda
  su respaldo con frase (§4); después, otro respaldo es rotar la clave, no volver a exportar
  esta. Un navegador sin Ed25519 en WebCrypto no tiene `llave` y guarda `privada`, que es lo
  único que firma. Una fila vieja con solo `privada` se lee igual: se le suma la `llave` y la
  semilla queda hasta el próximo respaldo.
  `localStorage["vereda.identidad"]` la identidad activa y `localStorage["vereda.sesion"]` el
  token. Es lo que implementa el SDK web del nodo de referencia; un cliente web que quiera
  convivir con él usa los mismos lugares. `identidad` es `""` hasta que el nodo la acuña.

## 4. El respaldo con frase

El **único** formato en que la clave privada sale de un dispositivo, y el formato de
intercambio entre apps y nodos: un respaldo hecho en la web se abre en iOS, en Android o en
el cliente de otro nodo. Esquema: `esquemas/acceso.json#/$defs/respaldo`. Vectores:
`ejemplos/vectores-acceso.json` → `respaldos`.

```json
{
  "formato": "vereda.clave.v3",
  "clave_publica": "<Ed25519, base64url>",
  "clave_cifrado": "<X25519 pública, base64url; solo si adentro va la privada>",
  "identidad": "marta@vereda.ar",
  "creada": "2026-09-21T15:04:05-03:00",
  "kdf": { "nombre": "PBKDF2", "hash": "SHA-256", "iteraciones": 600000, "sal": "<16 bytes>" },
  "cifrado": { "nombre": "AES-GCM", "nonce": "<12 bytes>", "texto": "<cifrado + etiqueta>" }
}
```

Todo binario va en base64url sin relleno. Para escribirlo:

1. **Texto claro.** El JCS de `{ "firma": <semilla Ed25519>, "cifrado": <privada X25519> }`
   (`texto_claro_v3`). `cifrado` va solo si la persona tiene clave de chat; si va, afuera va
   `clave_cifrado` con su pública.
2. **Frase.** La elige la persona, al menos 8 caracteres. Se normaliza a **NFKD** (como
   BIP-39) y se codifica en UTF-8. Un teclado de iPhone, uno de Android y uno de
   computadora pueden producir bytes distintos para la misma `ñ` o la misma tilde
   (compuesta o descompuesta): normalizada, la frase da siempre los mismos bytes y nadie
   queda afuera de su propio respaldo. La normalización es parte de v3 desde el principio.
3. **Llave.** PBKDF2-HMAC-SHA-256 sobre la frase, con 16 bytes de sal al azar y **600000**
   iteraciones, 32 bytes de salida.
4. **AAD.** El JCS del respaldo entero **sin** `cifrado`. Así nadie puede cambiar
   `clave_publica`, `identidad` ni las iteraciones sin que el archivo deje de abrirse.
5. **Cifrar.** AES-256-GCM con 12 bytes de nonce al azar. `texto` es el cifrado con la
   etiqueta de 16 bytes pegada al final, que es lo que devuelve WebCrypto.

Para leerlo, al revés, y además:

- Un `formato` desconocido se rechaza, no se adivina. Una combinación de KDF o cifrado que no
  es la de arriba, también.
- Menos de 100000 iteraciones se rechaza: un archivo así hace barata una frase corta.
- Si la frase no abre el sobre, el mensaje no distingue "frase incorrecta" de "archivo
  alterado".
- La clave pública que sale de la semilla tiene que ser `clave_publica`, y la X25519, si viene,
  `clave_cifrado`. Si no, el respaldo está corrupto.

`vereda.clave.v2` es el formato anterior del SDK web: el mismo sobre, sin `clave_cifrado`, el
texto claro es la semilla Ed25519 cruda de 32 bytes y la frase entra al KDF **tal cual**, sin
normalizar. Se sigue **leyendo**; no se escribe
más, porque restaurar un v2 en otro dispositivo pierde la clave del chat y con ella los
mensajes cifrados.

El archivo se puede guardar donde sea —mail, nube, un pendrive— porque sin la frase no es
nada. Con la frase es la identidad entera: la app lo tiene que decir así, con esas palabras
o parecidas.

## 5. Restaurar

**En otro dispositivo, mismo nodo.** La app importa el respaldo con la frase, guarda la
clave como en el punto 3 y hace el flujo del punto 1. El nodo encuentra la clave en el
historial y devuelve la misma identidad con `nuevo: false`. Si la persona rotó después de
hacer el respaldo, la clave del respaldo es `retirada` y el canje responde `clave_rotada`:
hace falta un respaldo de la clave nueva.

**En otro nodo.** La clave sola no se lleva la cuenta: en un nodo nuevo, la misma clave
acuña otra identidad, con otro dominio. Para conservar identidad, historial de claves y
reputación está la mudanza (`docs/federacion.md` → Mudanza): el paquete firmado de
`GET /v1/yo/exportar` y la declaración de mudanza que firma la clave de la persona. Con
custodia propia la clave no cambia en la mudanza; con custodia del nodo, el nodo nuevo rota
al importar.

## 6. Dónde está abierta tu cuenta

Cada canje (punto 1 o punto 2) abre una **sesión**: un token por dispositivo. La persona las
ve y las cierra sin depender de nadie.

- **`GET /v1/yo/sesiones`** lista las vigentes (`esquemas/acceso.json#/$defs/sesion_abierta`):
  `id`, `etiqueta`, `creada`, `ultimo_uso`, `vence`, `forma` (`clave` o `codigo`) y
  `actual: true` en la que hace el pedido. Nunca el token, ni nada que permita rearmarlo.
- **`DELETE /v1/yo/sesiones/{id}`** cierra una. **`DELETE /v1/yo/sesiones`** cierra todas menos
  la actual ("Cerrar las otras") y dice cuántas cerró.
- **`etiqueta`** la declara la app al abrir la sesión (`etiqueta` en `POST /acceso/sesion` o en
  el canje de código): "iPhone de Marta". El nodo no la adivina ni lee el `User-Agent` para
  inventar una: si no viene, la sesión va sin etiqueta y la app muestra `creada` y `forma`.
- **Renovar no abre una sesión nueva.** El token cambia; el `id` y `creada` quedan.
- **`sesion.abierta`** le llega a la persona (en todas sus sesiones) cada vez que se abre una, con `datos: {id, etiqueta?, forma}`. Es el aviso "se abrió
  tu cuenta en un dispositivo nuevo". `mandato.otorgado` le llega igual.

Todo esto es de la persona: un token de mandato recibe `403`, y no hay herramienta MCP. Las
sesiones de alguien no son asunto de su agente.

**Qué las cierra todas.** Rotar la clave (`POST /v1/yo/claves/rotar`) y declararla
comprometida (`POST /v1/yo/claves/comprometida`) cierran **todas** las sesiones de la
identidad, también la que hizo el pedido, en la misma transacción que el cambio de clave. Si
no, un ladrón con un token seguiría adentro 30 días después de que la persona rotó. Con
custodia propia la app vuelve a entrar al toque con la clave nueva (punto 1); con custodia
del nodo, con un código. Lo mismo hace un reclamo de propiedad resuelto.

## 7. Firma fresca para lo que importa

Un token robado (de un teléfono sin bloqueo, de un `localStorage` leído por un script) no
alcanza para lo que no tiene vuelta atrás. Estas operaciones piden, **además del token**, una
firma de la clave activa de la persona hecha hace menos de 5 minutos:

| Operación | Cuándo |
| --- | --- |
| `editarComercio` | Si cambia `privado.cuenta_cobro` (a dónde transfieren los compradores) |
| `conectarCobrador` | Siempre: activa un proveedor de pagos, o sea a qué cuenta va la plata de los que pagan con tarjeta (`docs/cobro-con-psp.md`) |
| `rotarClave`, `declararClaveComprometida` | Siempre |
| `invitarAlEquipo`, `cambiarMiembro` | Siempre |
| `sacarDelEquipo` | Si saca a otro. Irse uno mismo, no |
| `otorgarMandato` | Siempre |
| `exportarCuenta`, `exportarComercio` | Siempre |

`openapi.yaml` las marca con `x-firma-fresca`, y `validar.py` exige que declaren las cabeceras.

**La cabecera.** Es una firma HTTP RFC 9421, el mismo mecanismo que firma entre nodos, con
otra etiqueta y otros componentes:

```
Content-Digest: sha-256=:<SHA-256 del cuerpo crudo, base64 estándar>:
Signature-Input: fresca=("@method" "@path" "@query" "content-digest");created=1790000000;keyid="<clave activa>";alg="ed25519";tag="vereda-fresca"
Signature: fresca=:<Ed25519 de la base de firma, base64 estándar>:
```

- La etiqueta es `fresca`, y los componentes van esos cuatro y en ese orden. `@path` y
  `@query` en vez de `@target-uri`: la firma sobrevive a un proxy que cambia el host (el
  worker de la webapp), y la clave ya ata la firma a la persona.
- `content-digest` cubre el cuerpo (RFC 9530). Sin cuerpo (`GET /yo/exportar`, un `DELETE`),
  el SHA-256 de cero bytes. Sin query, `@query` es `?`.
- `keyid` es la clave pública **activa** del historial de la persona, en base64url como en el
  resto del protocolo. `tag="vereda-fresca"` impide que una firma hecha para otra cosa sirva
  acá.
- `created` a menos de `acceso.firma_fresca.ventana_segundos` (300, nunca más) de la hora del
  nodo, para atrás o para adelante.

Los bytes exactos, en `ejemplos/vectores-firma.json` → `firma_fresca`. En el teléfono, la app
pide Face ID, huella o el código del equipo antes de firmar: es el único paso que la persona
ve.

**Qué verifica el nodo.** La etiqueta, los componentes y el tag; el `Content-Digest` contra el
cuerpo; `created` dentro de la ventana; que `keyid` sea la clave `activa` del dueño de la
sesión; y la firma. Una firma presente que falla rechaza siempre, aunque el nodo esté en fase
de gracia. El motivo va en `detalle.motivo`:

| Qué pasó | `detalle.motivo` |
| --- | --- |
| No vino firma | `falta` |
| `created` fuera de la ventana | `vencida` |
| Cabeceras mal formadas, digest que no coincide o firma que no verifica | `invalida` |
| `keyid` no es la clave activa de quien llama | `clave_no_activa` |
| Custodia del nodo y la sesión no es reciente | `sesion_no_reciente` |

Todos responden `403 firma_fresca_requerida`. La persona está autenticada; lo que falta es la
prueba de que es ella, ahora.

**Con custodia del nodo** el dispositivo no tiene la clave y no puede firmar. En su lugar vale
una sesión abierta hace menos de `ventana_segundos`: la app le pide a la persona que vuelva a
entrar con un código y hace la operación con esa sesión.

**Por mandato.** Un agente no tiene la clave de la persona, así que no puede hacer estas
operaciones. Es a propósito: son las que una persona no quiere que haga nadie más. El agente
le dice que la haga ella desde la app.

**Declarar la clave comprometida también la pide**, firmada con la clave activa, que es
justamente la que se declara. Parece raro y es lo que protege: sin eso, un token robado
alcanzaba para instalar una clave del ladrón como la nueva activa, y la cuenta era suya. La
persona legítima siempre puede firmar, con la clave de su dispositivo o restaurada de su
respaldo (punto 5). Si el ladrón también tiene la clave, puede lo mismo que ella: por eso
existen el respaldo y el aviso `sesion.abierta`.

**Fase de gracia.** Las apps publicadas antes de esta regla no firman. El nodo anuncia qué
hace en `acceso.firma_fresca` de `/.well-known/vereda.json`:

```json
{ "acceso": { "custodia_propia": true, "firma_fresca": { "exigida": false, "ventana_segundos": 300 } } }
```

Con `exigida: false` el nodo verifica la firma si viene y rechaza una mala, pero acepta la
operación sin ella. Cuando pasa a `exigida: true` lo anuncia antes con `exigida_desde`. Un
nodo que no publica `firma_fresca` no la verifica ni la exige. Una app nueva firma siempre,
exija o no el nodo.

## Lo que un nodo no hace

- **No pide mail ni teléfono para entrar con clave.** Un usuario existe sin ninguno de los
  dos. El que quiera dejarlos los confirma aparte (`POST /v1/yo/contacto`).
- **No distingue en sus respuestas si una clave o un contacto ya tiene cuenta.**
- **No guarda el token en claro.** Guardar un hash alcanza para reconocerlo, y robar la base
  no da sesiones.
