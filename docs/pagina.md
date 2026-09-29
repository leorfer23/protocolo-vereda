# La página del comercio

Cada comercio tiene una página pública, tipo Linktree, que cualquiera abre sin cuenta: `https://<app>/@santa-elena`. Es lo que el comercio pone en su bio de Instagram, en el cartel del local y en su estado de WhatsApp.

La página son **datos, no HTML**: un tema y una lista de bloques (`esquemas/pagina.json`) que vive en la ficha, en `pagina`. Así:

- **Todas se parecen a Vereda.** Tipografías, íconos, botones y espaciados son los de Vereda, en cada app. El comercio elige entre opciones cerradas, no inventa estilos.
- **Cada una es del comercio.** Elige qué bloques, en qué orden, con qué textos, colores, fondo y fotos. Nadie aprueba la página.
- **Se arma con el agente.** "Poné arriba el botón de pedir, después las promos y al final las preguntas": el agente lee la página (`pagina_ver`), la cambia y la guarda entera con `comercio_editar`.
- **Es segura por construcción.** No hay HTML, scripts, fuentes externas ni CSS. Los enlaces son `https`, `mailto:`, `tel:` o `vereda://`. Las apps dibujan cada bloque con sus propios componentes.
- **Está viva.** Productos, precios, stock, promociones, horarios, sucursales y reseñas se leen al mostrar la página, de la sucursal que atiende a quien mira (`docs/sucursales.md`). La página nunca repite datos de la ficha: los referencia.

## Tema

`tema` elige dentro de lo que ofrece Vereda. Los colores salen de `marca` (`color_primario`, `color_secundario`); `acento` pisa el de los botones.

| Campo | Opciones |
| --- | --- |
| `modo` | `auto` (sigue al dispositivo), `claro`, `oscuro` |
| `fondo` | `liso`, `primario`, `degradado` (primario → secundario), `imagen` |
| `tipografia` | `vereda`, `redonda`, `serif`, `mono`, `manuscrita` |
| `esquinas` | `redondeadas`, `rectas`, `pildora` |
| `botones` | `llenos`, `contorno`, `suaves` |

Las apps garantizan contraste legible: si un color de marca no contrasta con el fondo, lo oscurecen o aclaran para el texto, sin cambiar el tono.

## Bloques

| `tipo` | Qué muestra |
| --- | --- |
| `encabezado` | Logo, nombre, descripción, abierto ahora, reputación; portada opcional (imagen o video) |
| `pedir` | El botón para comprar, a la sucursal que atiende a quien mira o a una fija |
| `enlaces` | Botones a donde quiera: el corazón de un Linktree |
| `redes` | Las redes de la ficha, como íconos o botones |
| `whatsapp` | Escribir al WhatsApp de la ficha con un mensaje ya escrito |
| `texto` | Texto con **negrita**, _itálica_ y enlaces |
| `imagen`, `galeria`, `video` | Fotos y clips |
| `productos` | Del catálogo, en vivo: elegidos, de una categoría, más vendidos, con promo o nuevos |
| `promociones` | Las promos activas |
| `sucursales` | Mapa y lista, con cuál le llega a quien mira |
| `horarios` | Los de la ficha, con abierto ahora |
| `resenas` | Reputación y últimas reseñas firmadas; no se eligen ni se esconden |
| `aviso` | Una franja: feriado, promo, corte |
| `preguntas` | Preguntas frecuentes |
| `separador` | Espacio o línea |

Todo bloque lleva `id` (lo elige quien edita, único en la página: el nodo responde `422 documento_invalido` si se repite), `titulo` opcional, `visible` (desde, hasta, días: una promo del finde se muestra sola) y `estilo` (fondo, alineación, ancho) dentro del tema.

Una app que no conoce un `tipo` lo saltea: un bloque nuevo nunca rompe una página vieja.

## Sin página

Un comercio sin `pagina` igual tiene la suya: las apps muestran encabezado, pedir, redes, horarios y sucursales. Una sucursal sin página usa la de su casa (`verPagina` dice de quién es en `pagina_de`).

## El link

`GET /v1/paginas/{nombre}` (`verPagina`) resuelve el nombre corto, la parte local de la identidad, y devuelve ficha y página en una llamada. Las apps publican la página en `https://<app>/@<nombre>`, y responden a quien comparte el link (WhatsApp, Instagram) con título, descripción e imagen (`pagina.compartir`, o nombre, descripción y logo de la ficha).
