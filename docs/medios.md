# Imágenes y video

Un comercio se muestra con fotos y, si quiere, con clips cortos: el local por dentro, la pizza entrando al horno, los cajones que llegan del Mercado Central. Las fotos van en `imagenes` (`comunes.json#/$defs/imagen`) y los clips en `videos` (`comunes.json#/$defs/video`), en la ficha del comercio y en cada oferta. El video se suma a las imágenes, no las reemplaza: una app que no reproduce video sigue mostrando lo mismo que antes.

## Dónde van

| Dónde | Campo | Qué es |
| --- | --- | --- |
| `comercio.json` | `videos` | Hasta tres clips del local. El primero es la portada: la app lo muestra en la tarjeta y en la ficha cuando decide reproducir. |
| `oferta.json` | `videos` | Hasta tres clips del producto. |
| los dos | `imagenes` | Igual que siempre. Lo que se muestra cuando no hay video o no se reproduce. |

## Qué es un clip

- **Corto.** Quince segundos como máximo (`duracion_s`). Es algo que se repite en loop, no un video para mirar.
- **Sin sonido.** Siempre empieza callado. `con_sonido` dice si el archivo trae audio, para que la app pueda ofrecer activarlo; nunca lo activa sola.
- **Con póster obligatorio.** `poster` es una imagen con la misma proporción que el clip. Se muestra mientras carga y en su lugar cuando no se reproduce.
- **Vertical, 9:16, para los clips de oferta.** Es lo recomendado, no lo obligatorio: el feed en video del barrio (`GET /buscar?con_video=true`) se mira a pantalla completa en un teléfono, y una app puede mostrar ahí solo los clips verticales (los que declaran `ancho` y `alto` con `alto > ancho`). Un clip horizontal sigue valiendo en la ficha y en la tarjeta.
- **En un formato que todos reproducen.** `tipo` es `video/mp4` (H.264 o HEVC) o `video/webm`. El mp4 es el que reproducen todas las apps; el webm, solo la web.

## Lo decide la app, con lo que trae el documento

Ahorro de datos, movimiento reducido, una conexión lenta o una batería baja son decisiones de la app y de la persona, no del protocolo. El protocolo solo garantiza que la app pueda decidir sin bajar el video:

- `poster`: qué mostrar si decide no reproducir.
- `duracion_s`: siempre presente.
- `bytes`: el peso, para decidir si lo baja con datos móviles. Recomendado; si falta, la app puede tratarlo como pesado.
- `ancho` y `alto`: van juntos o no van. Dejan reservar el lugar antes de que cargue.
- `alt`: qué se ve, para lectores de pantalla y para agentes, que no miran el clip.

Con movimiento reducido activado, lo esperable es mostrar el póster y reproducir solo si la persona lo pide.

## El feed en video

El feed es la misma búsqueda de ofertas, no un algoritmo aparte: `GET /buscar` sin texto y con `con_video=true` trae, de a páginas, las ofertas con clip de los comercios que llegan al punto, en el orden público de `docs/ranking-y-despacho.md`. Nadie paga para aparecer, sin sesión el orden es el mismo para todos, y cada resultado trae la oferta entera: el botón de compra sabe qué producto es, cuánto sale y de qué local. Ver el feed no suma apariciones en búsqueda a las métricas del comercio.

## Subir fotos al nodo

Una dueña de local no tiene un hosting donde dejar sus fotos. Por eso un nodo **puede** ofrecer dónde subirlas. Es una capacidad opcional: cada operador decide si la ofrece, y ninguna app puede contar con que exista.

- **Cómo se sabe.** El nodo que la ofrece publica en `/.well-known/vereda.json` la URL en `endpoints.medios` y qué acepta en `medios`: `limite_bytes` (el tamaño máximo de un archivo), `tipos` (`image/jpeg`, `image/png`) y `maximo_por_comercio` (cuántas fotos distintas guarda por comercio). Sin `endpoints.medios`, la app pide la URL como siempre.
- **Solo fotos.** Video no se sube: sigue por URL, porque es lo más caro de servir.
- **Achicadas en el teléfono.** La app convierte una foto HEIC a JPEG, la achica hasta que entre en `limite_bytes` (en el nodo de referencia, 2 MB) y recién ahí la sube. El nodo no genera versiones ni recorta.
- **Quién sube.** El dueño del comercio con su sesión, o su agente con el mandato `administrar`, con `POST /medios?comercio=<id>` y el archivo tal cual en el cuerpo. La respuesta trae la `url`; el comercio la pone en `imagenes` de su ficha o de una oferta (o en el `poster` de un clip). Nadie aprueba nada: queda publicada cuando la pone.
- **Sin metadatos.** El nodo borra EXIF, ubicación, datos de la cámara y XMP antes de guardar: lo que sirve no dice dónde se sacó la foto. Mira los bytes, no la cabecera: lo que no es una imagen de `tipos` que se pueda decodificar no se guarda.
- **Tope por comercio.** Hasta `maximo_por_comercio` fotos distintas. La misma foto subida dos veces devuelve la misma URL y cuenta una vez.
- **Si el operador la apaga.** Deja de aceptar subidas (`501 no_implementado`) y saca `endpoints.medios` del anuncio, pero sigue sirviendo las fotos que ya se subieron: están en fichas publicadas.

| Qué pasa | Estado | Código |
| --- | --- | --- |
| El nodo no aloja fotos, o se apagó | 501 | `no_implementado` |
| No es el dueño, o el mandato no trae `administrar` | 403 | `no_es_el_dueno` |
| Pesa más que `limite_bytes` | 413 | `medio_muy_grande` |
| No es una imagen de `tipos` | 415 | `tipo_no_admitido` |
| El comercio ya tiene `maximo_por_comercio` fotos | 409 | `tope_de_medios_alcanzado` |

## La foto de la entrega

Cuando el comercio pide el código de entrega y el comprador no está (lo deja en portería, con un vecino), se entrega con foto y el pedido queda `sin_codigo` (`docs/repartidores.md`, punto m). Quien entrega sube esa foto al mismo lugar, con otras reglas, porque no es una foto para mostrar: es una prueba entre las partes de un pedido.

- **Quién sube.** Solo quien lleva el pedido, con `POST /medios?pedido=<id>`: el repartidor asignado mientras el pedido está `en_camino` (con su sesión, o su agente con `repartir`), o el comercio que lo entrega él mismo (retiro, o `asignacion.modo: comercio`) con el pedido `listo` (el dueño, su equipo con el permiso `pedidos`, o su agente con `administrar`). Otra parte del pedido recibe `403 no_es_el_repartidor` y quien no es parte `404 no_encontrado`, como al leer el pedido; un pedido en otro estado, `409 transicion_invalida`.
- **Las mismas fotos.** JPEG o PNG, hasta `limite_bytes`, sin EXIF ni ubicación: el nodo los borra igual que en las del comercio. La ubicación del repartidor en la puerta ya queda en su constancia firmada cuando corresponde; la foto no la repite.
- **Hasta 3 por pedido.** Fotos distintas; la misma dos veces devuelve la misma URL. La cuarta, `409 tope_de_medios_alcanzado` con `detalle.maximo_por_pedido`. No cuentan para `maximo_por_comercio`.
- **Privada.** La URL que devuelve (`GET /pedidos/{id}/fotos/{nombre}`, `verFotoEntrega`) la ven solo las partes del pedido con su token: el comprador, el comercio y el repartidor, y sus agentes. No se publica, no se federa y no se cachea en público. Va en `entregarPedido.foto` y queda en `pedido.sin_codigo.foto`.
- **Dura lo que duran los datos del pedido.** Se borra junto con la dirección y el nombre del comprador, a los `datos.retencion_dias` del comercio (90 por defecto, `docs/datos-y-privacidad.md`). Las que se subieron y no se usaron, también.
- **Por MCP.** El agente del repartidor (o del comercio que lleva él) la sube con `foto_entrega_subir` y manda la `url` en `viaje_entregar` o `pedido_entregar`.

**Si el nodo no aloja fotos.** Sin `endpoints.medios`, quien entrega no tiene dónde subir la foto. Por eso un comercio no puede elegir `codigo_entrega` `siempre` ni `solo_efectivo` en ese nodo (`422 codigo_entrega_sin_medios` al crear o editar la ficha). Si el operador apaga la subida con pedidos en curso que ya congelaron esa regla, la foto deja de ser obligatoria: el pedido se entrega igual y queda `sin_codigo` sin `foto`. Una entrega nunca se traba porque falte dónde subir una foto. Esto vale solo para los pedidos con envío: en retiro, agotados los intentos del código, la foto sigue siendo obligatoria aunque el nodo no aloje fotos, para que nadie se equivoque a propósito y se saltee el código.

| Qué pasa, con `pedido` | Estado | Código |
| --- | --- | --- |
| Vinieron `comercio` y `pedido`, o ninguno | 400 | `parametro_invalido` |
| No es quien lleva el pedido | 403 | `no_es_el_repartidor` |
| El pedido no está en camino a entregarse | 409 | `transicion_invalida` |
| El pedido ya tiene 3 fotos | 409 | `tope_de_medios_alcanzado` |

## Lo que cuesta al nodo

Un nodo lo corre cualquiera en su propio servidor, y el video es lo más caro de servir. Por eso:

- **El video vive en cualquier URL.** El comercio lo sube donde quiera (su hosting, un bucket, un CDN) y en la ficha va solo el enlace. El nodo guarda y sirve ese enlace, nada más.
- **El nodo no está obligado a alojarlo ni a transcodificarlo.** No genera versiones, no recorta, no convierte. Lo que publica es lo que declaró el comercio.
- **Alojar video es opcional y no es del protocolo.** Un nodo que quiera ofrecer dónde subir los clips puede hacerlo detrás de la misma interfaz de almacenamiento compatible con S3 que usa para las fotos (`docs/plan-implementacion.md`), con un límite de tamaño por archivo que publica él. Ninguna app puede contar con que exista.
- **Lo que declara el comercio es su responsabilidad.** El nodo valida la forma (`duracion_s` hasta 15, póster presente, tipo conocido) pero no baja el archivo para comprobar que dure lo que dice. Si no coincide, la app lo nota al reproducir y puede cortarlo en quince segundos.
