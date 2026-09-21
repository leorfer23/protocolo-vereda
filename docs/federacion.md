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

## Entrega entre nodos

Todo lo que un nodo le manda a otro es un evento (`esquemas/evento.json`) a `POST /federacion/entrantes`.

**Idempotencia.** La clave es el `id` del evento. El receptor guarda los `id` que ya aplicó: si llega uno repetido con el mismo contenido responde `202` sin volver a aplicarlo; si llega con otro contenido, `409`. Reintentar nunca duplica un pedido.

**Orden.** Entre nodos, `secuencia` es obligatoria. El emisor entrega en orden por entidad y no envía la secuencia siguiente hasta que la anterior fue aceptada. Si el receptor ve un salto responde `409 secuencia_fuera_de_orden` con `detalle.ultima_secuencia`, y el emisor reenvía desde ahí.

**Cola por destino.** El emisor guarda lo pendiente en una cola persistente por nodo destino. Un nodo lento o caído no frena las entregas a los demás, y reiniciar el emisor no pierde nada.

**Qué se reintenta.**

| Respuesta | Qué hace el emisor |
| --- | --- |
| `202` | Listo |
| Error de red, `408`, `429`, `5xx` | Reintenta con espera exponencial durante 24 h, respetando `Retry-After` |
| `400 version_no_soportada` | Reenvía una vez en una versión común; si no hay, abandona |
| `401`, otros `4xx` | No reintenta: el mensaje está mal y repetirlo no lo arregla |
| `409 secuencia_fuera_de_orden` | Reenvía desde `ultima_secuencia` |

Como referencia, no como norma: primer reintento al minuto, duplicando hasta una hora, con variación al azar para no golpear todos juntos.

**Pasadas las 24 h** el emisor deja de insistir con ese evento pero no lo tira. La próxima vez que logre entregarle algo a ese nodo, manda primero lo pendiente, en orden.

**Crear un pedido es distinto.** Hay una persona esperando, así que `pedido.creado` se intenta 30 segundos como máximo. Si no hay respuesta, confirmar falla con `nodo_no_disponible`, no se reserva nada del lado del usuario, y el nodo del usuario encola un `pedido.cancelado` con ese mismo motivo: si el pedido llegó a crearse y lo que se perdió fue la respuesta, el comercio lo cancela y libera lo reservado. Si tampoco llega, la ventana de pago lo vence sola.

## Versiones

- La versión mayor va en la ruta (`/v1`). La menor va en `version_esquema` de cada objeto y en la cabecera `Vereda-Version` de cada entrega.
- Cada nodo publica en `.well-known/vereda.json` las `versiones` que acepta. El emisor elige la más alta que comparten.
- Dentro de una mayor, una menor solo agrega campos opcionales. Quien recibe un campo que no conoce lo ignora, pero guarda el objeto tal cual llegó: la firma cubre todos los campos, también los que no entiende.
- Por eso una menor nunca agrega campos a los objetos cerrados (`monto`, `cantidad`, `firma`, `clave`): un validador viejo los rechazaría. Eso es un cambio mayor.
- Si el receptor no acepta la versión responde `400 version_no_soportada` con `detalle.versiones`. El emisor reenvía una vez en una común.
- Si no hay ninguna versión en común, no hay pedido. La persona ve que ese comercio está en un nodo incompatible, igual que si estuviera cerrado.
- Una mayor nueva convive con la anterior: el nodo publica las dos en `versiones` y atiende las dos rutas mientras quiera.

## Repartidores entre nodos

Un viaje lo despacha el nodo del comercio. Puede ofrecerlo a repartidores de su propio nodo o, si hay acuerdo de federación, a cooperativas de otros nodos que cubran la zona. El pago del envío va directo del usuario a la cuenta del repartidor, como siempre.

## Comisión

Si un nodo cobra comisión, se la cobra a sus propios comercios. Nada se cobra entre nodos.

## Confianza entre nodos

Un nodo acepta pedidos de cualquier nodo que publique un `.well-known` válido y firme correctamente. Puede bloquear nodos que envíen fraude (identidades falsas, reseñas de pedidos inexistentes), y esa lista de bloqueo es pública. No hay otro mecanismo de moderación entre nodos: la reputación de los actores viaja con ellos y es lo que cuenta.

## Mudanza

`GET /yo/exportar` devuelve un paquete firmado con identidad, historial de claves, reseñas y preferencias. El nodo nuevo lo importa y publica una **declaración de mudanza** (`comunes.json#/$defs/mudanza`) en `GET /actores/{identidad}/mudanza`.

**La declaración la firma el actor, no el nodo.** Esa es toda la diferencia: `marta@vereda.ar → marta@otro.ar` vale porque la firmó la clave de Marta, y esa clave se verifica contra su historial, que viaja en el paquete con los avales encadenados. El nodo viejo no tiene que estar de acuerdo, ni estar vivo.

La reputación se conserva sola: las reseñas están firmadas por sus autores, no por el nodo.

Si la clave la custodiaba el nodo viejo, el nodo nuevo rota al importar. El nodo viejo conoció la clave privada y ya no tiene por qué poder firmar.

### Cuando el nodo viejo no coopera

El nodo viejo puede negarse a publicar la redirección, o haber desaparecido. Qué se rompe y qué no:

| | Sobrevive |
| --- | --- |
| Verificar lo que Marta firmó antes | Sí. Quien lo guardó guardó también la entrada de clave con la que lo verificó (`docs/claves-y-firmas.md`) |
| Su reputación | Sí. Las reseñas están firmadas por sus autores y viven en los nodos de los reseñados |
| Probar que la identidad nueva es la misma persona | Sí, con la declaración firmada, que cualquiera verifica sin consultar al nodo viejo |
| Que alguien que solo conoce `marta@vereda.ar` la encuentre sola | **No.** Ahí hay que preguntarle a Marta, o al nodo nuevo si se sabe cuál es |

Lo último no tiene arreglo sin un registro central, y un registro central es justamente lo que esta red no tiene. Se elige que una identidad sea difícil de encontrar antes que fácil de secuestrar.

**Lo que el nodo viejo nunca puede hacer:** publicar una mudanza falsa. Necesitaría firmar con la clave de Marta. Si la custodiaba y la usa, eso es una clave comprometida y se declara como tal (`docs/claves-y-firmas.md`).

## Disputas

La red no arbitra. Eso ya está en el README; esto dice qué significa cuando dos nodos se contradicen.

- **Fuente de verdad.** Para un pedido, el nodo del comercio. Si las dos copias difieren, la del comercio manda y la del usuario se corrige contra ella.
- **Evidencia.** El historial firmado del pedido, y nada más. Cada transición lleva quién y cuándo. Lo que no está firmado no es evidencia.
- **Quién responde ante quién.** Cada operador de nodo responde por los actores que hospeda, ante ellos y ante la ley que le aplique (`docs/datos-y-privacidad.md`). No responde ante los actores de otro nodo, y ningún nodo responde por otro.
- **La red no compensa.** No hay fondo de garantía, ni reembolso, ni reversión de pagos. La plata nunca pasó por la red: fue directo del usuario al comercio y al repartidor.
- **Lo que sí queda.** El desacuerdo se refleja en la reputación, que está firmada y es portable, y un nodo puede bloquear a otro por fraude con la lista de bloqueo pública.

Esto es una elección, no una omisión. Comprarle a un desconocido acá da menos garantías que en una plataforma con respaldo central, y favorece al comercio del barrio que ya conocés.

## Catálogo maestro

Un producto envasado se describe una vez por EAN para que los comercios solo pongan precio y stock. Es dato compartido, y el dato compartido entre nodos sin autoridad central genera conflictos.

**La regla: no hay merge automático.** Cada nodo publica su propia versión de un EAN en `GET /catalogo/{ean}` y la firma quien la aportó. Un mismo EAN puede tener versiones distintas en nodos distintos, y eso no es un error.

Cuando un nodo quiere el dato de un EAN que no tiene:

1. Le pregunta a nodos que ya conoce, por ejemplo aquellos de los que ya recibió pedidos.
2. Copia la versión que elija **con su `aportado_por` y su firma intactos**, así queda registrado de dónde salió.
3. Si recibe versiones que se contradicen, elige por su propio criterio, que es suyo y no del protocolo. Criterios razonables: quién la aportó, cuál trae más campos, cuál es más reciente.
4. Nunca fusiona campos de dos versiones. Un producto mitad de un nodo y mitad de otro no lo firmó nadie.

El comercio siempre manda sobre el catálogo. Si el catálogo dice 900 g y el comercio publica 1 kg, vale lo que publica el comercio: el catálogo describe el producto, la oferta describe lo que se vende.

Un EAN mal cargado se corrige aportando una versión nueva, no editando la ajena.
