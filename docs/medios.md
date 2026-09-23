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
- **En un formato que todos reproducen.** `tipo` es `video/mp4` (H.264 o HEVC) o `video/webm`. El mp4 es el que reproducen todas las apps; el webm, solo la web.

## Lo decide la app, con lo que trae el documento

Ahorro de datos, movimiento reducido, una conexión lenta o una batería baja son decisiones de la app y de la persona, no del protocolo. El protocolo solo garantiza que la app pueda decidir sin bajar el video:

- `poster`: qué mostrar si decide no reproducir.
- `duracion_s`: siempre presente.
- `bytes`: el peso, para decidir si lo baja con datos móviles. Recomendado; si falta, la app puede tratarlo como pesado.
- `ancho` y `alto`: van juntos o no van. Dejan reservar el lugar antes de que cargue.
- `alt`: qué se ve, para lectores de pantalla y para agentes, que no miran el clip.

Con movimiento reducido activado, lo esperable es mostrar el póster y reproducir solo si la persona lo pide.

## Lo que cuesta al nodo

Un nodo lo corre cualquiera en su propio servidor, y el video es lo más caro de servir. Por eso:

- **El video vive en cualquier URL.** El comercio lo sube donde quiera (su hosting, un bucket, un CDN) y en la ficha va solo el enlace. El nodo guarda y sirve ese enlace, nada más.
- **El nodo no está obligado a alojarlo ni a transcodificarlo.** No genera versiones, no recorta, no convierte. Lo que publica es lo que declaró el comercio.
- **Alojarlo es opcional.** Un nodo que quiera ofrecer dónde subir los clips puede hacerlo detrás de la misma interfaz de almacenamiento compatible con S3 que usa para imágenes (`docs/plan-implementacion.md`), con un límite de tamaño por archivo que publica él. Ese servicio es suyo, no del protocolo: ninguna app puede contar con que exista.
- **Lo que declara el comercio es su responsabilidad.** El nodo valida la forma (`duracion_s` hasta 15, póster presente, tipo conocido) pero no baja el archivo para comprobar que dure lo que dice. Si no coincide, la app lo nota al reproducir y puede cortarlo en quince segundos.
