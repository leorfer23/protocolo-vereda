# Cambios

Lo que cambia en el protocolo después de publicarlo, del más nuevo al más viejo. Un cambio **incompatible** obliga a los clientes a actualizarse.

## 2026-09-23

- `confirmarCarrito` y `carrito_confirmar` responden `409 comercio_cerrado` con el comercio cerrado: sin `programado_para`, si `abierto_ahora` es false; programado, si sus `horarios` no cubren ese instante. No se crea el pedido. `comercio_cerrado` se suma a los códigos de `esquemas/error.json`.
- **Incompatible: `GET /buscar` responde una página.** Antes, un array de `{oferta, comercio, distancia_km}`; ahora `PaginaDeResultados` (`{resultados, cursor_siguiente}`), con `limite` (50 por defecto, 200 como máximo) y `cursor`, igual que `listarPedidosDelComercio`. La herramienta MCP `buscar_ofertas` también. Un cliente que leía el array tiene que leer `resultados`.
- `GET /buscar` y `buscar_ofertas` suman `con_video`: solo ofertas con clip. Es el feed en video del barrio, en el orden público de siempre (`docs/medios.md`, `docs/ranking-y-despacho.md`).
- `apariciones_busqueda` no cuenta los resultados con `con_video`.
- `docs/medios.md` recomienda clips de oferta verticales, 9:16.
