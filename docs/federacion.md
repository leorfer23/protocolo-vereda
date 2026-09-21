# Federación

Vereda es una red de nodos que hablan el mismo protocolo, como el email. Cualquiera puede correr un nodo; un usuario de un nodo puede pedirle a un comercio de otro desde el día uno. No hay blockchain ni nodo central.

## Identidad

Toda identidad es `actor@nodo`: `marta@vereda.ar`, `lahuerta@nodo.rosario.coop`. El nodo es un dominio. La identidad se resuelve como el email: el nodo de la derecha responde por el actor de la izquierda.

Cada actor tiene un par de claves Ed25519. La clave privada la custodia su nodo, cifrada, salvo que el actor elija custodiarla él (`custodia_clave: propia`). Con ella se firman reseñas, mandatos y las transiciones clave de un pedido (creación, aceptación, entrega). Las claves rotan sin invalidar lo ya firmado: ver `docs/claves-y-firmas.md`.

## Descubrimiento

`GET https://{nodo}/.well-known/vereda.json` devuelve nombre, versiones soportadas, clave pública del nodo, zona geográfica, endpoints (API, MCP, federación) y el link al código fuente. Un nodo descubre a otro por su dominio; no hay registro central.

## Quién guarda qué

| Dato | Vive en |
| --- | --- |
| Comercio, ofertas, modalidades, rondas | Nodo del comercio |
| Usuario, preferencias, listas, mandatos | Nodo del usuario |
| Repartidor, disponibilidad, ubicación | Nodo del repartidor (normalmente el de su cooperativa) |
| Pedido | Nodo del comercio es la fuente de verdad; el nodo del usuario guarda una copia firmada para su historial |
| Reseña | Nodo del autor la emite; nodo del destinatario la guarda y la publica |
| Mensajes | Nodo del comercio para pedidos; copia cifrada en el nodo del usuario |
| Catálogo maestro | Replicado entre nodos, con el EAN como clave |

## Un pedido entre nodos

1. `marta@vereda.ar` arma un carrito contra `lahuerta@nodo.rosario.coop`. Su nodo lee ofertas y modalidades del nodo del comercio (API pública, cacheable por ETag).
2. Al confirmar, el nodo de Marta firma el pedido con la clave de Marta y lo envía a `POST https://nodo.rosario.coop/v1/federacion/entrantes`, con firma HTTP del nodo (RFC 9421).
3. El nodo del comercio valida la firma contra el historial de claves de Marta (`GET https://vereda.ar/v1/actores/marta@vereda.ar/claves`), crea el pedido, genera el cobro con el PSP del comercio y devuelve la referencia de pago.
4. Cada transición del pedido se publica como evento firmado al nodo de Marta, que actualiza su copia.
5. La entrega la firma el repartidor; la reseña la firma cada parte y viaja al nodo del reseñado.

Si el nodo de Marta está caído, el pedido sigue: la fuente de verdad es el nodo del comercio. Si el del comercio está caído, no hay pedido, igual que si el comercio estuviera cerrado.

## Repartidores entre nodos

Un viaje lo despacha el nodo del comercio. Puede ofrecerlo a repartidores de su propio nodo o, si hay acuerdo de federación, a cooperativas de otros nodos que cubran la zona. El pago del envío va directo del usuario a la cuenta del repartidor, como siempre.

## Comisión

Si un nodo cobra comisión, se la cobra a sus propios comercios. Nada se cobra entre nodos.

## Confianza entre nodos

Un nodo acepta pedidos de cualquier nodo que publique un `.well-known` válido y firme correctamente. Puede bloquear nodos que envíen fraude (identidades falsas, reseñas de pedidos inexistentes), y esa lista de bloqueo es pública. No hay otro mecanismo de moderación entre nodos: la reputación de los actores viaja con ellos y es lo que cuenta.

## Mudanza

`GET /yo/exportar` devuelve un paquete firmado con identidad, clave, historial, reseñas y preferencias. Otro nodo lo importa y publica una redirección firmada desde la identidad vieja a la nueva (`marta@vereda.ar → marta@otro.ar`) durante 12 meses. La reputación se conserva porque las reseñas están firmadas por sus autores, no por el nodo. El paquete lleva el historial de claves completo. Si la clave la custodiaba el nodo viejo, el nodo nuevo rota al importar: el nodo viejo conoció la clave privada y ya no tiene por qué poder firmar.
