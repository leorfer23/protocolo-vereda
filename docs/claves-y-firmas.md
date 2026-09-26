# Claves y firmas

Cada actor y cada nodo tiene un par de claves Ed25519. Las claves rotan, se pierden y a veces se filtran. Esta página dice cómo cambia una clave sin que se caiga lo que ya se firmó con la anterior: una reseña de hace dos años tiene que seguir valiendo.

No hay autoridad certificante, registro central ni sellado de tiempo externo. Como en el email, el nodo responde por sus actores.

## Vectores de prueba

`ejemplos/vectores-firma.json` tiene los bytes exactos: el objeto, su canonicalización JCS en hexadecimal, la clave, la firma y un request RFC 9421 completo. Una implementación conforme reproduce byte a byte el JCS, el `Content-Digest` y la base de firma, y **verifica** cada firma contra la clave publicada.

Las firmas no se reproducen. Ed25519 admite firmar con azar: CryptoKit en iOS lo hace, y dos firmas del mismo mensaje con la misma clave salen distintas y las dos válidas. Un cliente puede producir firmas no deterministas; quien verifica nunca compara bytes de firma, comprueba la firma. Los vectores las traen deterministas (RFC 8032) solo porque así se generan.

Las claves de prueba se derivan de una semilla publicada, `SHA-256("vereda:vector:<etiqueta>")`, así que cualquiera llega a la misma clave privada sin que se la pasemos. Son claves de prueba y no se usan en producción.

`python3 validar.py` las verifica: re-deriva cada clave desde su semilla, recanonicaliza cada objeto, comprueba las firmas y rearma la base de firma del request HTTP desde sus cabeceras.

Para regenerarlos, `python3 generar-vectores.py`. Es determinista: dos corridas dan el mismo archivo.

El retiro y la entrega de un pedido los firma el repartidor sobre un objeto chico que se rearma desde el pedido (`pedido.json#/$defs/traspaso`); cómo lo manda desde el teléfono y qué hace el nodo si falta está en `docs/repartidores.md`, punto j. La rendición del efectivo al comercio la firman el repartidor y el comercio, cada uno su constancia con el monto (`pedido.json#/$defs/constancia_rendicion`, punto l del mismo documento).

Cómo entra una persona con su clave, qué clave abre sesión y cómo se respalda la clave privada con una frase está en `docs/acceso.md`.

## Historial

Un actor no tiene una clave: tiene un historial (`claves`), de la más vieja a la más nueva. Nunca se borra una entrada y hay exactamente una `activa`. `clave_publica` repite la activa para quien solo necesita esa.

| Estado | Qué significa | Sus firmas |
| --- | --- | --- |
| `activa` | La que firma hoy | Valen |
| `retirada` | Rotación normal; dejó de usarse en `hasta` | Las anteriores a `hasta` valen para siempre |
| `comprometida` | Alguien más pudo tenerla desde `comprometida_desde` | Ver abajo |

Es público: `GET /actores/{identidad}/claves` en el nodo del actor, y `claves` en `/.well-known/vereda.json` para el nodo. Se cachea por ETag.

## Verificar una firma

1. La firma verifica con `firma.clave_publica` sobre el JCS del objeto **sin los campos que no escribió el firmante**. Si no: `firma_invalida`.
2. Esa clave está en el historial de `firma.firmante`. Si no está en la copia en caché, se vuelve a pedir el historial una vez. Si sigue sin estar: `clave_desconocida`.
3. `firma.instante` cae entre `desde` y `hasta` de esa clave.
4. Si la clave está `comprometida`, la firma vale solo si el objeto ya estaba registrado por la otra parte antes de `comprometida_desde`. Si no: `clave_comprometida`.

### Los campos que no escribió el firmante

Una firma cubre lo que su autor escribió, y nada más. Son cuatro campos, en todo el protocolo:

| Campo | Quién lo escribe | Por qué no puede entrar en la firma |
| --- | --- | --- |
| `firma` | el autor, al final | es el resultado: no puede cubrirse a sí mismo |
| `respuesta` | **el reseñado**, después | si entrara, responder una reseña invalidaría la firma de quien la escribió |
| `senales` | **el nodo**, al recalcular | el peso de una reseña es una función del estado actual (`docs/resenas.md`): cambia solo, y el autor no lo firmó |
| `visible` | **el nodo** | la revelación simultánea la decide el nodo, no el autor |

Quien verifica los saca los cuatro antes de canonicalizar. Cada uno lleva su propia firma si le corresponde: `respuesta.firma` es del reseñado y se verifica igual, sobre la respuesta sin su `firma`.

La regla es la que hace posible que una reseña se marque, se responda y se revele sin que se rompa lo único que el protocolo promete de ella: que la escribió quien dice, y que nadie la tocó.

El paso 4 existe porque `instante` lo escribe quien firma: el que robó una clave puede poner cualquier fecha. Lo que no puede falsificar es que el nodo de la otra parte ya tenía guardado el objeto.

## Guardar la prueba

Quien guarda un objeto firmado por un actor de otro nodo guarda también la entrada de clave con la que lo verificó y el instante en que lo recibió. Así una reseña sigue siendo verificable aunque el nodo de su autor desaparezca, y el paso 4 tiene contra qué comparar.

## Rotar

`POST /yo/claves/rotar`. La clave anterior pasa a `retirada` y firma la entrada de la nueva (`avalada_por`). Ese aval encadena las claves sin depender del nodo, así el historial se puede verificar después de una mudanza. El nodo emite `clave.rotada`; quien tenga el historial en caché lo vuelve a pedir.

Con custodia del nodo, lo hace el nodo. Con custodia propia, la persona genera la clave nueva, la avala con la vieja y envía la entrada.

Rotar nunca se puede hacer por mandato. Un agente no toca claves.

Rotar pide firma fresca con la clave que se retira y **cierra todas las sesiones** de la persona, también la que rotó (`docs/acceso.md`, puntos 6 y 7): quien tenía un token viejo queda afuera.

## Clave comprometida

`POST /yo/claves/comprometida`, con la clave y desde cuándo. La puede declarar el actor, o el nodo si la custodiaba.

- La clave pasa a `comprometida` y se rota. La nueva no lleva aval: una clave filtrada no puede avalar nada. Responde solo el nodo.
- Con custodia propia, la persona genera la clave nueva y manda su entrada en `clave`, sin `avalada_por`; el nodo no puede generarla por ella (sería pasarle la custodia sin que la pida) y responde 422 si falta. Con custodia del nodo, la genera el nodo si no viene. Desde ese momento, la nueva es la única que abre sesión (`docs/acceso.md`).
- Se revocan todos los mandatos activos del actor. La persona los vuelve a otorgar con la clave nueva.
- Se cierran todas las sesiones del actor, en la misma transacción. Declararla pide firma fresca con la clave activa: un token robado solo no puede instalar una clave nueva (`docs/acceso.md`, punto 7).
- Una clave `retirada` puede pasar a `comprometida` si la filtración se descubre después.
- El nodo emite `clave.comprometida`.

Si se pierde una clave de custodia propia, el camino es el mismo: clave nueva sin aval.

## Clave de cifrado

La entrada de clave lleva además `clave_cifrado`, una clave pública X25519 para el chat cifrado (`x25519-xchacha20` en `mensaje.json`). Es una clave distinta de la de firma, no se deriva de ella: una clave se usa para una sola cosa. Viaja en el mismo historial y rota con la de firma, así que sale del mismo `GET /actores/{identidad}/claves` y no hace falta ninguna ruta nueva.

Si un destinatario no publica `clave_cifrado`, el chat de ese contexto va sin cifrar.

**Un comercio publica la suya con `PATCH /comercios/{id}`** (`clave_cifrado`, X25519 pública en base64url; `null` la retira). La carga quien lo administra, generada en su dispositivo: la privada queda ahí y el nodo nunca la ve, aunque custodie la clave de firma del comercio. Así el chat con un comercio es de punta a punta aunque su firma sea de custodia del nodo. El nodo no la guarda en la ficha sino en la entrada activa del historial de claves del comercio, donde la busca quien le escribe (`GET /actores/{identidad}/claves`). Una clave que no mide 32 bytes responde 422.

## Claves del nodo

- El `keyid` de las firmas HTTP (RFC 9421) es la clave pública del nodo.
- Al rotar, el nodo publica la nueva como `activa` y retira la anterior en el mismo instante. Quien recibe un `keyid` que no conoce vuelve a pedir `/.well-known/vereda.json` una vez.
- Un pedido firmado con una clave `retirada` se acepta si su `created` es anterior a `hasta`: estaba en vuelo durante la rotación.
- Si se compromete la clave de un nodo que custodia claves de actores, esas claves también están comprometidas. El nodo declara la suya y rota todas las que custodia.

## Reclamo de un comercio

Cuando un reclamo de propiedad se resuelve (`docs/identidad-y-verificacion.md`, punto 6), la clave del comercio pasa a `retirada` y la nueva entra sin `avalada_por` —la anterior era del dueño anterior— y con `reclamo`, el id del reclamo firmado que la instaló. Quien verifica el historial sigue la cadena por ahí: el reclamo es público, firmado por el reclamante, y dice con qué prueba se resolvió. Las firmas de la clave retirada anteriores a `hasta` siguen valiendo.

## Agentes

Un mandato nombra la clave del agente. Si el agente cambia de clave, hace falta un mandato nuevo.

## Mudanza

El paquete de `GET /yo/exportar` lleva el historial completo con sus avales. El nodo nuevo lo publica tal cual. Si la clave la custodiaba el nodo viejo, el nodo nuevo rota al importar: el nodo viejo conoció la clave privada.
