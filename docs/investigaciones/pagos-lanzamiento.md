# Pagos con pasarela en el lanzamiento del 28/9: decisión y plan

Documento de decisión del 2026-09-25. Construye sobre [`cobros.md`](cobros.md) (2026-09-23) y no repite su comparativa: acá solo va lo que cambia, lo que se verificó de nuevo y el plan. Fuentes públicas, sin cuentas ni gasto. No es asesoramiento legal.

Lo que Leo fijó hoy: **los pagos con pasarela entran en el lanzamiento del 28/9** y **Vereda no cobra comisión** (fee de plataforma 0). Los principios siguen: Vereda nunca toca la plata, el cobro va directo a la cuenta del comercio, el efectivo es un diferencial.

Los anexos de esta vuelta: [`pagos-lanzamiento/mercado-pago.md`](pagos-lanzamiento/mercado-pago.md), [`pagos-lanzamiento/mobbex-uala.md`](pagos-lanzamiento/mobbex-uala.md) y [`pagos-lanzamiento/conciliacion.md`](pagos-lanzamiento/conciliacion.md). Lo que dice **(NC)** no está confirmado en una fuente oficial.

---

## 1. Recomendación

**Mercado Pago, conectado por OAuth, cobrando en la cuenta del comercio, sin comisión de Vereda, con checkout web por redirección y webhook firmado al nodo.** Ualá Bis como alternativa inmediata después (mismo adaptador, credenciales que pega el comercio), Mobbex más adelante.

Por qué MP y no otro para el 28/9:

- Es el único con **OAuth oficial** (el comercio toca "Conectar" y listo; access token de 180 días, refresh token de 6 meses que **rota en cada renovación**, confirmado en la doc) y **webhook firmado** (HMAC-SHA256 en `x-signature` con la clave secreta de la aplicación del operador, 22 s para responder, reintentos cada 15 min). Los demás piden pegar credenciales y no firman.
- La mayoría de los comercios ya tiene cuenta. El alta en Vereda es un toque, no un formulario.
- **Fee 0 está en la doc oficial**: en `POST /checkout/preferences`, `marketplace_fee` "default value is 0" y solo se puede mandar si hay un `marketplace` definido, cuyo default es "NONE". El nodo crea la preferencia con el token OAuth del comercio y omite los dos campos: es un cobro normal del comercio y Vereda no aparece en la plata en ningún momento (anexo MP, §1). Lo que en `cobros.md` era (NC) quedó confirmado.
- El checkout es una URL (`init_point`). Se abre en el navegador, en la webapp o en un `SFSafariViewController`: no hay SDK nativo, no hay datos de tarjeta en el nodo, no hay PCI.
- Contracargos y devoluciones son entre el comercio y MP. Con fee 0, Vereda no pone plata en ninguna devolución.

Lo que ya estaba decidido y no cambia: la tensión de marca con MP la resolvió Leo al meter pagos en el lanzamiento. La interfaz sigue neutra: el comercio elige su proveedor, la app nunca lo presenta como "el" medio.

**Alternativa: Ualá Bis.** Sin nada que registrar para el operador: el comercio genera `client_id` y `client_secret` en su app de Ualá y los pega en el portal; token de 24 h, checkout por redirección, webhook sin firma (se re-consulta siempre), acreditación instantánea, PSPCP registrado (N.º 33.549). Cara en tarjeta (4,9%), barata en QR y dinero en cuenta (0,8%). Es la salida para quien no quiere MP y son cuatro endpoints (anexo Mobbex/Ualá, §B).

**Mobbex** queda tercero: Dev Connect es tan cómodo como OAuth y es el más barato en tarjeta (1,9% / 2,6%), pero exige cuenta y aplicación Mobbex por operador de nodo, con alta de "unos días hábiles", vida del token sin documentar y webhook sin firma ni reintentos documentados. No cierra en tres días.

---

## 2. El MVP que se puede mergear antes del 28

Cuatro piezas, en este orden. Todas caben en la spec y en el nodo que ya existen: `servicio.PSP`, `ConfirmarCobro` (idempotente, "para el webhook del PSP"), `psp` y `psp_referencia` en el pedido, `link_pago` y `metodo: tarjeta` en `pago.json`.

### 2.1 Conexión de la cuenta del comercio (portal)

1. En **Datos → Cobros** del portal, el comercio toca "Cobrar con Mercado Pago".
2. El portal pide al nodo `POST /comercios/{id}/cobrador/conectar` `{psp: "mercado_pago", volver_a}` y recibe la `url` de autorización de MP (con `state` firmado por el nodo y PKCE).
3. El comercio autoriza en MP. MP vuelve al nodo (`/pagos/mercado_pago/volver?code&state`, fuera de `/v1`), el nodo canjea el código por `access_token` + `refresh_token` del comercio, los guarda **cifrados** y redirige al portal (`volver_a`).
4. El portal muestra "Conectado · Juan Pérez (MP)" y "Desconectar" (`DELETE /comercios/{id}/cobrador`). Al conectar, `medios_cobro` suma `tarjeta`; al desconectar, lo saca. Si el comercio revoca desde MP, el tópico `mp-connect` del webhook avisa y el nodo marca `revocado`.

Lo que necesita el operador del nodo, una vez: una **aplicación en "Tus integraciones"** de su cuenta de MP (gratis, sin aprobación ni certificación), con la URL de vuelta (https, estática) y la URL del webhook de su nodo, y los permisos `read`, `write` y `offline_access` (sin este último no hay refresh). De ahí salen `client_id`, `client_secret` y la clave secreta del webhook, que van al nodo como variables de entorno (`VEREDA_PAGOS_MP_*`). El nodo publica `cobradores: ["mercado_pago"]` en `/.well-known/vereda.json`; un nodo sin eso responde `501 no_implementado` y las apps no ofrecen la opción. Mismo patrón que `medios`.

### 2.2 Checkout por web, con redirección

1. El comprador elige "Tarjeta o Mercado Pago" al confirmar (`metodo_pago: tarjeta`). Solo aparece si el comercio tiene `tarjeta` en `medios_cobro`.
2. El nodo crea la preferencia de Checkout Pro **con el token del comercio**: `external_reference = pedido_id`, `notification_url` del nodo, `back_urls` de la webapp, `expiration` igual al `vence` del cobro (la `ventana_pago_min` del comercio), **sin `marketplace_fee`**. Devuelve el pago `pendiente` con `link_pago = init_point`, `psp = "mercado_pago"`, `psp_referencia = preference_id`. Con `binary_mode: true` el pago solo puede quedar aprobado o rechazado, nunca "en proceso", que es lo que un pedido de barrio necesita.
3. La webapp redirige a `link_pago`. El comprador paga en MP (tarjeta, dinero en cuenta, cuotas si el comercio las da).
4. MP vuelve a `back_urls` (`https://app.protocolovereda.com/pedido/{id}`, con `payment_id`, `status` y `external_reference` en la query; `back_urls` tiene que ser https, `auto_return: approved`). La webapp muestra el pedido; el estado real llega por el evento, no por la query string.

Sin cambio en la app iOS del 28/9: la build que va a revisión sigue con efectivo y transferencia, así que **no hay nueva revisión de App Store**. La app suma tarjeta después, con `SFSafariViewController` y vuelta por `vereda://` (§5).

### 2.3 Webhook en el nodo y avisos

1. MP manda `POST /pagos/mercado_pago/webhook?data.id=…` (fuera de `/v1`) con `x-signature` (`ts=…,v1=…`) y `x-request-id`. El nodo **valida el HMAC-SHA256** del manifiesto `id:[data.id];request-id:[x-request-id];ts:[ts];` con la clave secreta de la app y responde 200 en menos de 22 s. Si no responde, MP reintenta cada 15 min, con intervalos más largos después del tercero.
2. Nunca confía en el aviso: **re-consulta** `GET /v1/payments/{id}` con el token del comercio y comprueba `external_reference`, `transaction_amount` y `status = approved`.
3. Llama a `ConfirmarCobro("mercado_pago", referencia)`: el cobro pasa a `confirmado` con `confirmado_por: psp`, el pedido a `pagado`, y salen `pago.confirmado` y `pedido.pagado` como hoy. Un aviso repetido no hace nada (idempotente por `payment_id`).
4. Los avisos ya existen: el comprador y el comercio los reciben por `GET /eventos` (SSE) y por sus webhooks salientes; el repartidor, cuando el pedido pagado entra en despacho (`viaje.ofrecido`). No hay push APNs/FCM en el nodo hoy (`TODO(avisos)`) y no entra en el MVP.
5. **Red de seguridad:** el barrido de cada minuto (`Mantener`) re-consulta a MP los cobros `pendiente` con `psp` antes de vencerlos, por si un webhook se perdió. Rechazado o vencido en MP: `fallido` y el pedido se cancela con `pago_vencido`, como cualquier pendiente.
6. Devoluciones: `POST /v1/payments/{id}/refunds` con el token del comercio y `X-Idempotency-Key` (obligatorio), total o parcial, hasta 180 días, con saldo del comercio; queda como cobro `concepto: devolucion`. Contracargos: del comercio con MP; el nodo solo anota `pago.contracargo` si llega el tópico (fuera del MVP).

### 2.4 Conciliación de transferencias por centavos únicos

Ya está en la spec con este PR (`CAMBIOS.md` 2026-09-25):

- El nodo hace único el `instrucciones.monto` entre los cobros pendientes por transferencia del mismo destinatario, descontando de 1 a 99 centavos, al azar, solo cuando otro cobro de las últimas 24 h pidió el mismo monto (`ajuste_centavos`, nunca positivo: restar es un descuento; sumar sería cobrar más que el precio exhibido, Res. 4/2025). El monto no se reusa hasta 24 h después de cerrar el cobro, porque una transferencia puede llegar tarde. Es lo que hace el e-commerce de Indonesia hace diez años con su "kode unik", y lo que Stripe hace al conciliar por monto exacto (anexo conciliación, §1). El comercio reconoce la transferencia por el monto exacto, sin leer el concepto. Default del protocolo; se apaga con `privado.cuenta_cobro.centavos_unicos: false`.
- **Confirmación en un toque:** el portal lista los pedidos "por confirmar" con el monto exacto y lo que declaró el comprador; el comercio compara con el aviso "Recibiste $12.499,63" de su billetera y toca "Ya vi la plata". Esto es lo que entra el 28/9.
- **Confirmación automática:** solo si la cuenta de cobro del comercio es Mercado Pago y su API deja listar las transferencias entrantes al CVU (anexo conciliación, §3). Si se confirma, el mismo barrido de cada minuto busca, con el token del comercio, una transferencia entrante con el monto exacto de cada pendiente y la confirma con `confirmado_por: psp`. Es un PR aparte (§4) y no bloquea el lanzamiento.
- **¿Con cuánto pagás?** (`paga_con_centavos`) también entra con este PR: el comprador dice el billete, el repartidor lleva cambio.

### Qué queda fuera del 28/9

- Tarjeta en las apps iOS y Android (entra en la versión siguiente, sin tocar la build en revisión).
- Ualá Bis y Mobbex (mismo adaptador; Ualá Bis es el primero después).
- QR interoperable y Point de MP (API de Orders): otro producto, otra vuelta.
- Push al teléfono: no hay infraestructura de avisos en el nodo.
- Comprobante estructurado con OCR, Live Activity y Share Extension (`cobros.md` §1): mejoras de iOS, después.
- Contracargos por API, cuotas configurables por el comercio, cobradores múltiples por comercio.
- Confirmación automática de transferencias por API de MP hasta que se pruebe con una transferencia real.

---

## 3. Qué cambia en la spec (PR aparte, el primero del plan)

| Cambio | Dónde | Tamaño |
|---|---|---|
| `metodo_pago` suma `tarjeta` en `confirmarCarrito` y `carrito_confirmar`; con ese medio el pago nace `pendiente` con `link_pago`, `psp`, `psp_referencia` y `vence`. `medio_no_disponible` si el comercio no lo tiene. | `openapi.yaml`, `mcp/herramientas.json`, `docs/carrito-y-reserva.md` | Chico |
| `POST /comercios/{id}/cobrador/conectar` (`conectarCobrador`: `{psp, volver_a}` → `{url}`), `GET /comercios/{id}/cobrador` (`verCobrador`: `{psp, estado, titular, conectado_en}`), `DELETE /comercios/{id}/cobrador` (`desconectarCobrador`). Solo el dueño o `administrar` con permiso `datos`. Herramientas MCP `cobrador_conectar` (devuelve la URL para que el agente se la pase a la persona), `cobrador_ver`, `cobrador_desconectar`. | `openapi.yaml`, `mcp/herramientas.json` | Mediano |
| `privado.cuenta_cobro` suma `estado: conectado \| vencido \| revocado`, `titular_psp` y `conectado_en`. Los tokens nunca están en la ficha ni en ninguna respuesta: viven cifrados en el nodo. | `esquemas/comercio.json` | Chico |
| `pago.confirmado_por: comercio \| psp \| repartidor` (quién vio la plata). | `esquemas/pago.json` | Chico |
| `/.well-known/vereda.json` publica `cobradores: ["mercado_pago"]` (`CapacidadCobradores`). Sin eso, `conectarCobrador` es `501 no_implementado`. | `openapi.yaml` | Chico |
| Eventos informativos `pago.reembolsado` y `pago.contracargo`. | `docs/eventos.md` | Chico |
| `docs/cobro-con-psp.md`: reglas. El nodo crea el cobro en la cuenta del comercio con su token; marca pagado solo después de re-consultar; nunca guarda datos de tarjeta; devoluciones con `concepto: devolucion`; el contracargo es entre el comercio y su proveedor; webhook y vuelta de OAuth fuera de `/v1` (`/pagos/{psp}/webhook`, `/pagos/{psp}/volver`); fee de plataforma siempre 0. Un id de proveedor es un string libre con tabla orientativa (`mercado_pago`, `uala_bis`, `mobbex`), sin enum cerrado. | `docs/` | Mediano |
| Suite de conformidad: nivel B prueba `tarjeta` solo si el nodo publica `cobradores`. | `docs/suite-conformidad.md`, `conformidad/` | Chico |

Ya mergeado con este PR: centavos únicos (`instrucciones.ajuste_centavos`, `cuenta_cobro.centavos_unicos`) y `paga_con` (`paga_con_centavos`, `pago.paga_con`, `viaje.por_pedido[].paga_con`, error `paga_con_insuficiente`).

---

## 4. Plan por PRs y repo

Una rama por punto, squash, sin apilar (`memory-git`). Estimaciones para un worker con el gate local verde; "S" medio día, "M" un día, "L" un día y medio. Orden por dependencia; los que no dependen entre sí van en paralelo.

| # | Repo | PR | Depende de | Tamaño |
|---|---|---|---|---|
| 0 | protocolo-vereda | **Este PR**: centavos únicos, `paga_con`, este documento | — | hecho |
| 1 | protocolo-vereda | Spec del cobrador: §3 completo (`tarjeta`, `conectarCobrador`/`verCobrador`/`desconectarCobrador`, `cuenta_cobro.estado`, `confirmado_por`, `cobradores` en well-known, `docs/cobro-con-psp.md`, conformidad) | 0 | M |
| 2 | vereda-nodo | Centavos únicos y `paga_con`: ajuste del monto en `armarPedido` (`servicio/confirmar.go`) y en los otros tres lugares que crean cobros, columna `monto_a_transferir` con índice único parcial por destinatario entre pendientes, `paga_con` en `Pago` y en `viaje.por_pedido`, `422 paga_con_insuficiente`, tests con `NuevaBaseDePrueba` | 0 | M |
| 3 | vereda-nodo | Cobrador MP, conexión: tabla `cobradores` (comercio, psp, user_id, tokens **cifrados** AES-GCM con `VEREDA_PAGOS_CLAVE`, vence, estado), cliente OAuth (authorize URL con `state` firmado y PKCE, canje, refresh con rotación atómica), `montarPagos(mux)` con `/pagos/mercado_pago/volver`, `conectarCobrador`/`verCobrador`/`desconectarCobrador`, `cobradores` en well-known, config `VEREDA_PAGOS_MP_CLIENT_ID/CLIENT_SECRET/WEBHOOK_SECRET/URL_PUBLICA` con el patrón de `medios`, `api/operaciones.go` regenerado | 1 | L |
| 4 | vereda-nodo | Cobrador MP, cobro: `MercadoPago` que cumple `servicio.PSP` (`Requerido` crea la preferencia sin `marketplace_fee`, `Reembolsar` por API), `PSPDe` por comercio, webhook `/pagos/mercado_pago/webhook` (HMAC, re-consulta, `ConfirmarCobro`), barrido de pendientes con `psp` en `Mantener` antes de `VencerCobros`, `confirmado_por`, MCP `carrito_confirmar` con `tarjeta`, tests con un MP falso en `httptest` | 3 | L |
| 5 | vereda-nodo | Mock: un **MP falso** en `mock/` (autoriza, crea preferencia, página de "pagar/rechazar", manda el webhook firmado) para los e2e de la webapp y el QA agéntico. Imprescindible: los pagos de prueba de MP **no mandan webhooks**, y Checkout Pro se prueba con cuentas de prueba, no con credenciales de test | 4 | S |
| 6 | vereda-webapp | Portal: "Cobrar con Mercado Pago" en Datos → Cobros (estado, conectar, desconectar, vuelta por `?cobrador=`), lista "por confirmar" con el monto exacto de centavos únicos, arreglo del `estado === 'declarada'` en `PedidoVista` (hoy el botón "Ya vi la plata" no aparece), SDK regenerado desde la spec | 1 (tipos), 3 (e2e) | M |
| 7 | vereda-webapp | Comprador: "Tarjeta o Mercado Pago" en el checkout, redirección a `link_pago`, vuelta a `/pedido/:id` con el estado por SSE, "¿Con cuánto pagás?" en efectivo, monto con centavos en la pantalla de transferencia (ya se muestra bien) | 1 (tipos), 4 y 5 (e2e) | M |
| 8 | vereda-webapp | E2E con el mock y el MP falso (`npm run e2e:mock`): conectar, pagar aprobado, pagar rechazado, vencido; y `e2e:prod-lectura` sin escribir | 5, 6, 7 | S |
| 9 | vereda-nodo | Conciliación automática de transferencias con la cuenta MP del comercio: barrido que busca transferencias entrantes con el monto exacto de cada pendiente y confirma con `confirmado_por: psp`. **Solo si el anexo de conciliación lo confirma y una transferencia real lo prueba.** | 3 | M |
| 10 | vereda-app | iOS y Android, versión siguiente: `tarjeta` en `CheckoutModelo` con `SFSafariViewController` / Custom Tabs y vuelta por link universal https (MP exige `back_urls` https: iOS necesita Associated Domains, que hoy no tiene; Android ya tiene el App Link); "¿Con cuánto pagás?"; cuenta de cobro y "Cobrar con Mercado Pago" en Datos. **Pantallas y copy los decide Leo** (2-3 opciones antes de abrir). | 1, 4 | M + M |

Camino crítico para el 28/9: **1 → 3 → 4 → 5 → 8**, con 2, 6 y 7 en paralelo. Son tres días de nodo y dos de webapp si hay dos workers; con uno solo, entran 1-4 y 6-7 y el e2e completo (8) queda para el 29.

Lo que necesita a **Leo** antes de mergear 3 y 4:

1. Crear la aplicación de Mercado Pago en "Tus integraciones" de su cuenta (gratis): nombre, URL de vuelta `https://ar.protocolovereda.com/pagos/mercado_pago/volver`, URL del webhook `https://ar.protocolovereda.com/pagos/mercado_pago/webhook`, tópico `payment`. Copiar `client_id`, `client_secret` y la clave secreta del webhook al nodo de producción. Sin esto el nodo no publica `cobradores` y nada se ofrece.
2. Confirmar el copy de los dos botones: "Cobrar con Mercado Pago" (portal) y "Tarjeta o Mercado Pago" (checkout), o darnos los suyos.
3. Los términos del nodo tienen que decir que el comercio es el proveedor y que el cobro es entre el comercio y su pasarela (`legal.md`, *Juárez* vs *Almirón*). Lo escribe el agente de legales.

---

## 5. Riesgos que quedan

- **El refresh token de MP rota en cada uso (confirmado en la doc).** Si el nodo no guarda el nuevo de forma atómica, pierde al comercio y hay que reconectar. El PR 3 lo hace en una sola transacción.
- **Tokens en el nodo.** Un token permite crear cobros y devoluciones en la cuenta del comercio. Cifrado en reposo con clave por variable de entorno, permisos mínimos (`offline_access read write`), revocación desde el portal y aviso al comercio. Hoy el nodo no cifra nada en reposo: es infraestructura nueva y chica.
- **Webhook con la firma de la app del operador para pagos creados con el token del comercio.** Es lo que la doc describe para marketplaces (anexo MP, §3); se prueba en sandbox antes de mergear el PR 4.
- **Costos por provincia.** MP cobra según la provincia del vendedor desde el 2026-03-06 (CABA 6,29 % al momento, PBA y Córdoba 6,60 %; 1,49 % / 1,56 % a 35 días; QR 0,8 % con dinero en cuenta). Es entre el comercio y MP; la app no lo muestra como si fuera de Vereda.
- **Legal.** MercadoLibre S.R.L. está inscripta en el BCRA como PSPCP y agregador, y su procesadora como adquirente: la adhesión del comercio la hace MP. Con fee 0, sin QR propios, sin ordenar transferencias y sin tocar plata, ni el proyecto ni el operador quedarían alcanzados por el BCRA ni la UIF (`cobros/legal.md`). Sigue siendo lectura propia: conviene la opinión escrita de un abogado antes de crecer, no antes del 28.
- **Producción sin datos de prueba.** Todo se prueba contra el mock y el MP falso; en prod solo lectura hasta que Leo cargue la app de MP (`memory-qa`).
