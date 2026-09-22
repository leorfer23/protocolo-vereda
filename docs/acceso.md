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
  persona le otorga desde su sesión (`docs/mandatos.md` del nodo de referencia,
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
relleno, como toda firma del protocolo. Los bytes exactos están en
`ejemplos/vectores-acceso.json` → `prueba_de_clave`.

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
viejo deja de valer en el mismo momento.

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
| Demasiados pedidos | `429` con `Retry-After` |

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
  `{ identidad, clave_publica, privada, creada }` con `privada` como `Uint8Array` de 32 bytes;
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
2. **Frase.** La elige la persona, al menos 8 caracteres. Se normaliza a **NFC** y se codifica
   en UTF-8: un teclado que compone la tilde distinto no puede dejar a nadie afuera de su
   propio respaldo.
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

`vereda.clave.v2` es el formato anterior del SDK web: el mismo sobre, sin `clave_cifrado`, y
el texto claro es la semilla Ed25519 cruda de 32 bytes. Se sigue **leyendo**; no se escribe
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

## Lo que un nodo no hace

- **No pide mail ni teléfono para entrar con clave.** Un usuario existe sin ninguno de los
  dos. El que quiera dejarlos los confirma aparte (`POST /v1/yo/contacto`).
- **No distingue en sus respuestas si una clave o un contacto ya tiene cuenta.**
- **No guarda el token en claro.** Guardar un hash alcanza para reconocerlo, y robar la base
  no da sesiones.
