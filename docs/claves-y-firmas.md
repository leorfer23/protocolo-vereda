# Claves y firmas

Cada actor y cada nodo tiene un par de claves Ed25519. Las claves rotan, se pierden y a veces se filtran. Esta página dice cómo cambia una clave sin que se caiga lo que ya se firmó con la anterior: una reseña de hace dos años tiene que seguir valiendo.

No hay autoridad certificante, registro central ni sellado de tiempo externo. Como en el email, el nodo responde por sus actores.

## Vectores de prueba

`ejemplos/vectores-firma.json` tiene los bytes exactos: el objeto, su canonicalización JCS en hexadecimal, la clave, la firma y un request RFC 9421 completo. Una implementación conforme reproduce cada byte.

Las claves de prueba se derivan de una semilla publicada, `SHA-256("vereda:vector:<etiqueta>")`, así que cualquiera llega a la misma clave privada sin que se la pasemos. Son claves de prueba y no se usan en producción.

`python3 validar.py` las verifica: re-deriva cada clave desde su semilla, recanonicaliza cada objeto, comprueba las firmas y rearma la base de firma del request HTTP desde sus cabeceras.

Para regenerarlos, `python3 generar-vectores.py`. Es determinista: dos corridas dan el mismo archivo.

## Historial

Un actor no tiene una clave: tiene un historial (`claves`), de la más vieja a la más nueva. Nunca se borra una entrada y hay exactamente una `activa`. `clave_publica` repite la activa para quien solo necesita esa.

| Estado | Qué significa | Sus firmas |
| --- | --- | --- |
| `activa` | La que firma hoy | Valen |
| `retirada` | Rotación normal; dejó de usarse en `hasta` | Las anteriores a `hasta` valen para siempre |
| `comprometida` | Alguien más pudo tenerla desde `comprometida_desde` | Ver abajo |

Es público: `GET /actores/{identidad}/claves` en el nodo del actor, y `claves` en `/.well-known/vereda.json` para el nodo. Se cachea por ETag.

## Verificar una firma

1. La firma verifica con `firma.clave_publica` sobre el JCS del objeto sin `firma`. Si no: `firma_invalida`.
2. Esa clave está en el historial de `firma.firmante`. Si no está en la copia en caché, se vuelve a pedir el historial una vez. Si sigue sin estar: `clave_desconocida`.
3. `firma.instante` cae entre `desde` y `hasta` de esa clave.
4. Si la clave está `comprometida`, la firma vale solo si el objeto ya estaba registrado por la otra parte antes de `comprometida_desde`. Si no: `clave_comprometida`.

El paso 4 existe porque `instante` lo escribe quien firma: el que robó una clave puede poner cualquier fecha. Lo que no puede falsificar es que el nodo de la otra parte ya tenía guardado el objeto.

## Guardar la prueba

Quien guarda un objeto firmado por un actor de otro nodo guarda también la entrada de clave con la que lo verificó y el instante en que lo recibió. Así una reseña sigue siendo verificable aunque el nodo de su autor desaparezca, y el paso 4 tiene contra qué comparar.

## Rotar

`POST /yo/claves/rotar`. La clave anterior pasa a `retirada` y firma la entrada de la nueva (`avalada_por`). Ese aval encadena las claves sin depender del nodo, así el historial se puede verificar después de una mudanza. El nodo emite `clave.rotada`; quien tenga el historial en caché lo vuelve a pedir.

Con custodia del nodo, lo hace el nodo. Con custodia propia, la persona genera la clave nueva, la avala con la vieja y envía la entrada.

Rotar nunca se puede hacer por mandato. Un agente no toca claves.

## Clave comprometida

`POST /yo/claves/comprometida`, con la clave y desde cuándo. La puede declarar el actor, o el nodo si la custodiaba.

- La clave pasa a `comprometida` y se rota. La nueva no lleva aval: una clave filtrada no puede avalar nada. Responde solo el nodo.
- Se revocan todos los mandatos activos del actor. La persona los vuelve a otorgar con la clave nueva.
- Una clave `retirada` puede pasar a `comprometida` si la filtración se descubre después.
- El nodo emite `clave.comprometida`.

Si se pierde una clave de custodia propia, el camino es el mismo: clave nueva sin aval.

## Claves del nodo

- El `keyid` de las firmas HTTP (RFC 9421) es la clave pública del nodo.
- Al rotar, el nodo publica la nueva como `activa` y retira la anterior en el mismo instante. Quien recibe un `keyid` que no conoce vuelve a pedir `/.well-known/vereda.json` una vez.
- Un pedido firmado con una clave `retirada` se acepta si su `created` es anterior a `hasta`: estaba en vuelo durante la rotación.
- Si se compromete la clave de un nodo que custodia claves de actores, esas claves también están comprometidas. El nodo declara la suya y rota todas las que custodia.

## Agentes

Un mandato nombra la clave del agente. Si el agente cambia de clave, hace falta un mandato nuevo.

## Mudanza

El paquete de `GET /yo/exportar` lleva el historial completo con sus avales. El nodo nuevo lo publica tal cual. Si la clave la custodiaba el nodo viejo, el nodo nuevo rota al importar: el nodo viejo conoció la clave privada.
