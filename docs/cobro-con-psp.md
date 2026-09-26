# Cobro con proveedor de pagos (PSP)

Un comercio puede cobrar con tarjeta u otros medios de un proveedor (Mercado Pago, Ualá Bis, Mobbex, …) sin que Vereda toque la plata. La plata va a la cuenta del comercio; el nodo solo crea el cobro, guarda referencias y confirma cuando el proveedor dice que pagaron. Diseño del lanzamiento en `docs/investigaciones/pagos-lanzamiento.md`.

## Principios

- **Vereda nunca toca la plata.** El cobro se crea en la cuenta del comercio, con el token del comercio. El nodo no es marketplace: la comisión de plataforma es **siempre 0**. No manda `marketplace_fee` ni campos equivalentes.
- **Sin datos de tarjeta en el nodo.** El comprador paga en la página del proveedor (`link_pago`). El nodo no recibe número de tarjeta, CVV ni nada PCI.
- **Confirmar solo después de re-consultar.** Un webhook o una vuelta del navegador avisan; el nodo marca el cobro `confirmado` recién cuando re-consulta al proveedor y ve el pago aprobado. Idempotente: el mismo aviso dos veces no duplica.
- **Devoluciones y contracargos son del comercio con su proveedor.** Una devolución en Vereda es un pago con `concepto: devolucion`. Un contracargo no mueve plata en el nodo: publica el evento y listo.

## Cómo se sabe si el nodo lo ofrece

El nodo que ofrece cobradores publica `cobradores` en `/.well-known/vereda.json`: una lista de ids de proveedor (strings libres). Orientativos:

| Id | Proveedor |
| --- | --- |
| `mercado_pago` | Mercado Pago (OAuth) |
| `uala_bis` | Ualá Bis (credenciales del comercio) |
| `mobbex` | Mobbex |

No hay enum cerrado: un nodo puede anunciar otro id. Sin `cobradores`, `conectarCobrador` responde `501 no_implementado` y las apps no ofrecen la opción.

## Conectar y desconectar

Solo el dueño del comercio, o un agente / miembro con permiso `datos`:

1. `POST /comercios/{id}/cobrador/conectar` con `{psp, volver_a}` → `{url}` de autorización (o de pegar credenciales, según el proveedor).
2. El comercio autoriza en el proveedor. La vuelta OAuth y el webhook viven **fuera de `/v1`**: `/pagos/{psp}/volver` y `/pagos/{psp}/webhook`.
3. El nodo guarda los tokens **cifrados**. Nunca salen en la ficha, en `GET /comercios/{id}/cobrador` ni en ninguna respuesta.
4. `GET /comercios/{id}/cobrador` → `{psp, estado, titular, conectado_en}` (`conectado` / `vencido` / `revocado`).
5. `DELETE /comercios/{id}/cobrador` desconecta. Al conectar, `medios_cobro` suma `tarjeta`; al desconectar, la saca. Si el comercio revoca desde el proveedor, el webhook lo marca `revocado`.

Lo mismo por MCP: `cobrador_conectar` (devuelve la URL para pasársela a la persona), `cobrador_ver`, `cobrador_desconectar`.

En `privado.cuenta_cobro` el nodo guarda `estado`, `titular_psp` y `conectado_en` (además del alias de transferencia). Es privado: no se federa ni sale en la ficha pública.

## Checkout con tarjeta

1. El comprador elige `metodo_pago: tarjeta` al confirmar, solo si el comercio tiene `tarjeta` en `medios_cobro`. Si no, `422 medio_no_disponible` con `detalle.medios_cobro`.
2. El cobro nace `pendiente` con `link_pago`, `psp`, `psp_referencia` y `vence` (`ventana_pago_min` del comercio).
3. La app redirige a `link_pago`. Al volver, el estado real llega por el evento `pago.confirmado` (o `pago.fallido` / `pago.vencido`), no por la query string.
4. Quién vio la plata queda en `pago.confirmado_por`: `psp`, `comercio` o `repartidor`.

## Eventos

Además de `pago.pendiente` / `confirmado` / `vencido` / `fallido`:

| Evento | Cuándo |
| --- | --- |
| `pago.reembolsado` | El proveedor confirmó una devolución (`concepto: devolucion` o el cobro original revertido). |
| `pago.contracargo` | El proveedor avisó un contracargo. Informativo: la plata la discute el comercio con su proveedor. |

## Errores

| Qué pasa | Estado | Código |
| --- | --- | --- |
| El nodo no anuncia `cobradores` | 501 | `no_implementado` |
| No es el dueño, o falta permiso `datos` | 403 | `no_es_el_dueno` / `sin_permiso` |
| `metodo_pago: tarjeta` y el comercio no tiene `tarjeta` | 422 | `medio_no_disponible` |
