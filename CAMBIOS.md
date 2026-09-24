# Cambios

Lo que cambia en el protocolo después de publicarlo, del más nuevo al más viejo. Un cambio **incompatible** obliga a los clientes a actualizarse.

## 2026-09-23

- `crearResena` y `responderResena` dicen quién firma cuando escribe quien administra un comercio: si la sesión administra el comercio del pedido, la reseña (y la respuesta a una reseña que recibió el comercio) es del comercio y la firma el nodo con la clave del comercio que custodia, aunque la persona custodie la suya. Quien escribió una reseña no la responde como el comercio. Es lo que el nodo de referencia ya hacía (`docs/resenas.md`, "Quién firma cuando reseña un comercio").
- `openapi.yaml` declara el cuerpo de 29 respuestas exitosas que no lo tenían: las que mueven un pedido devuelven el pedido como quedó (`pedido.json`), crear y editar devuelven el recurso (`lista`, `suscripcion`, `ronda`, `grupo`, `cotizacion`, `viaje`, `mensaje`, `resena`, `mandato`), `otorgarMandato` suma el `token` del agente, y `borrarCuenta`, `pedirConfirmacionDeContacto` y `registrarWebhook` su objeto chico. `pedirCodigoDeAcceso`, `rechazarViaje` y `recibirFederacion` dicen que no tienen cuerpo. Es lo que el nodo de referencia ya respondía: ningún cliente cambia, pero ahora puede validarlo y tiparlo. `validar.py` falla si vuelve a aparecer una 2xx sin esquema.
- `confirmarCarrito` y `carrito_confirmar` responden `409 comercio_cerrado` con el comercio cerrado: sin `programado_para`, si `abierto_ahora` es false; programado, si sus `horarios` no cubren ese instante. No se crea el pedido. `comercio_cerrado` se suma a los códigos de `esquemas/error.json`.
- **Incompatible: `GET /buscar` responde una página.** Antes, un array de `{oferta, comercio, distancia_km}`; ahora `PaginaDeResultados` (`{resultados, cursor_siguiente}`), con `limite` (50 por defecto, 200 como máximo) y `cursor`, igual que `listarPedidosDelComercio`. La herramienta MCP `buscar_ofertas` también. Un cliente que leía el array tiene que leer `resultados`.
- `GET /buscar` y `buscar_ofertas` suman `con_video`: solo ofertas con clip. Es el feed en video del barrio, en el orden público de siempre (`docs/medios.md`, `docs/ranking-y-despacho.md`).
- `apariciones_busqueda` no cuenta los resultados con `con_video`.
- `docs/medios.md` recomienda clips de oferta verticales, 9:16.
