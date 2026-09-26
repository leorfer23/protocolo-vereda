# Pagos con pasarela en el lanzamiento del 28/9: decisión y plan

Documento de decisión del 2026-09-25. Construye sobre [`cobros.md`](cobros.md) (2026-09-23) y no repite su comparativa: acá solo va lo que cambia, lo que se verificó de nuevo y el plan. Fuentes públicas, sin cuentas ni gasto. No es asesoramiento legal.

Lo que Leo fijó hoy: **los pagos con pasarela entran en el lanzamiento del 28/9** y **Vereda no cobra comisión** (fee de plataforma 0). Los principios siguen: Vereda nunca toca la plata, el cobro va directo a la cuenta del comercio, el efectivo es un diferencial.

**Actualización del 2026-09-25 (tarde), decisiones de Leo: el proveedor oficial es Ualá Bis; Mercado Pago queda segundo y Mobbex tercero. Y es multi-proveedor:** el comercio activa uno o varios a la vez desde el portal, y el comprador elige con cuál paga entre los activos de ese comercio, además del efectivo y la transferencia. La spec no favorece a ninguno (`docs/cobro-con-psp.md`, que ahora trae la interfaz del proveedor, las devoluciones, el proveedor de prueba y los interruptores). La aplicación de Mercado Pago del operador deja de bloquear nada. §1 y §4 quedan reescritos en ese orden; §2 describe el flujo de Mercado Pago tal como se investigó y sigue valiendo para cuando entre, con las diferencias de Ualá Bis en §1.

Los anexos de esta vuelta: [`pagos-lanzamiento/mercado-pago.md`](pagos-lanzamiento/mercado-pago.md), [`pagos-lanzamiento/mobbex-uala.md`](pagos-lanzamiento/mobbex-uala.md) y [`pagos-lanzamiento/conciliacion.md`](pagos-lanzamiento/conciliacion.md). Lo que dice **(NC)** no está confirmado en una fuente oficial.

---

## 1. Recomendación

**Ualá Bis primero, con las credenciales del propio comercio, cobrando en su cuenta, sin comisión de Vereda, con checkout web por redirección y re-consulta de cada aviso.** Mercado Pago segundo, por OAuth; Mobbex tercero, también con las credenciales del comercio. **El comercio activa los que quiera a la vez** y el comprador elige. Dos proveedores falsos (`prueba` por credenciales, `prueba_redireccion` por redirección) para la suite de conformidad y los e2e.

Por qué Ualá Bis primero:

- **Nada que registrar para el operador del nodo.** No hay aplicación, aprobación ni KYC del operador: el comercio genera `username`, `client_id` y `client_secret_id` en su app (Cobros online → API) y los pega en el portal. El nodo solo necesita su clave de cifrado. Con MP, en cambio, cada operador tiene que crear y mantener su aplicación en "Tus integraciones" antes de que un solo comercio pueda conectar.
- **Fee 0 por construcción**: la API no tiene split ni fee de plataforma. Todo va a la cuenta Ualá del comercio.
- **Acreditación al instante**, PSPCP inscripto en el BCRA (N.º 33.549), contracargos a cargo del comercio, devoluciones por API hasta 90 días.
- **Son cuatro endpoints** (token, checkout, re-consulta, devolución) y ninguna decisión técnica pendiente (anexo Mobbex/Ualá, §B).

Lo que cambia respecto de MP y la spec ya cubre:

- **Conectar con credenciales, no con OAuth.** `conectarCobrador` acepta las dos formas según el anuncio del proveedor (`conexion: credenciales | redireccion`); con credenciales el nodo las prueba antes de guardarlas y responde el cobrador ya conectado, o `422 credenciales_invalidas`.
- **El aviso no viene firmado.** El nodo nunca cree el cuerpo: siempre re-consulta `GET /v2/api/orders/{uuid}`. Idempotencia por referencia + estado (Ualá no manda id de aviso).
- **Se marca pagado en `APPROVED`, nunca en `PROCESSED`.**
- **Mínimo $25 por cobro**: el anuncio lo publica en `monto_minimo` y un pedido menor con tarjeta es `422 monto_menor_al_minimo`.
- **Token de 24 h sin refresh**: se vuelve a pedir con las credenciales. Si el comercio las regenera, el nodo lo ve en el 401 y el cobrador queda `credenciales_rechazadas` hasta que pegue las nuevas.
- **Cara en tarjeta (4,9 %)**, barata en QR y dinero en cuenta (0,8 %), pero el QR no tiene API. Es entre el comercio y Ualá; la app no lo muestra como si fuera de Vereda.

**Mercado Pago, segundo.** Es el único con OAuth oficial (el comercio toca "Conectar" y listo) y webhook firmado, y la mayoría de los comercios ya tiene cuenta. Queda detrás de que el operador cree su aplicación (§4). El flujo investigado está en §2 y en el anexo MP; `marketplace_fee` se omite y el default es 0.

**Mobbex** queda tercero, **con las credenciales del comercio**: el comercio crea su propia aplicación en el portal de desarrolladores de Mobbex (`api_key`) y copia el token de su entidad (`access_token`); el operador no registra nada, igual que con Ualá Bis. Es el más barato en tarjeta (1,9% / 2,6%) y el de más medios. Dev Connect (tipo OAuth) queda descartado porque exige cuenta y aplicación Mobbex por operador de nodo. Pendientes (NC): vida del token, plazo de devolución y reintentos del webhook, que no firma.

La interfaz sigue neutra: el comercio elige su proveedor, la app nunca lo presenta como "el" medio, y el efectivo sigue adelante.

---

## 2. El MVP que se puede mergear antes del 28

Cuatro piezas, en este orden. Todas caben en la spec y en el nodo que ya existen: `servicio.PSP`, `ConfirmarCobro` (idempotente, "para el webhook del PSP"), `psp` y `psp_referencia` en el pedido, `link_pago` y `metodo: tarjeta` en `pago.json`.

### 2.1 Conexión de la cuenta del comercio (portal)

> Las rutas de §2 y §3 son las de #65, con un solo cobrador por comercio. Desde el PR multi-proveedor van por proveedor (`/comercios/{id}/cobradores/{psp}/…`) y el comercio tiene varios a la vez: la referencia es `docs/cobro-con-psp.md`.

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

Una rama por punto, squash, sin apilar (`memory-git`). Estimaciones para un worker con el gate local verde; "S" medio día, "M" un día, "L" un día y medio. Orden por dependencia; los que no dependen entre sí van en paralelo. Todo se construye contra `docs/cobro-con-psp.md`.

| # | Repo | PR | Depende de | Tamaño |
| --- | --- | --- | --- | --- |
| 0 | protocolo-vereda | Centavos únicos, `paga_con`, este documento (#64) | — | hecho |
| 1 | protocolo-vereda | Cobrador neutral: `tarjeta`, `conectarCobrador`/`verCobrador`/`desconectarCobrador`, `confirmado_por`, `cobradores` (#65) | 0 | hecho |
| 2 | protocolo-vereda | **Pagos completos en la spec, multi-proveedor**: cobradores como colección por `psp` (varios activos a la vez, `cobradores` en la ficha, `psp` elegido al confirmar), conectar con credenciales o por redirección y con firma fresca, anuncio con `conexion`/`campos`/`ambientes`/`monto_minimo`/`reembolso`, interfaz del proveedor y mapeo de estados, `reembolsarPago` + MCP `pedido_reembolsar`, proveedor `prueba`, interruptores, `comercio.cobrador_cambiado`, conformidad de tarjeta de punta a punta | 1 | M |
| 3 | vereda-nodo | Centavos únicos y `paga_con` (en curso) | 0 | M |
| 4 | vereda-nodo | **Cobrador base**: tabla de cobradores con credenciales y tokens **cifrados** (AES-GCM con la clave del nodo), interfaz de adaptador (probar, crear cobro, re-consultar, reembolsar, interpretar aviso), `conectarCobrador`/`verCobrador`/`desconectarCobrador` con las dos formas, `cobradores` en well-known según interruptores, `/pagos/{psp}/webhook` con re-consulta e idempotencia por referencia + estado, barrido de pendientes en `Mantener` antes de `VencerCobros`, `reembolsarPago`, `confirmado_por`, MCP. Uno por `psp`, varios por comercio, `cobradores` en la ficha y `psp` en `confirmarCarrito`. Con los adaptadores **`prueba`** y **`prueba_redireccion`** (página pagar/rechazar, `POST link_pago`, aviso doble, autorización simulada) como primeros proveedores | 2 | L |
| 5 | vereda-nodo | **Adaptador Ualá Bis v2**: token de 24 h (y `credenciales_rechazadas` en el 401), checkout con `amount` en centavos y `external_reference` = id del pago, re-consulta, mapeo `PENDING/PROCESSED/APPROVED/REJECTED/REFUNDED`, devolución con resultado por aviso, mínimo $25. Tests contra un Ualá falso en `httptest`, **sin llamar a Ualá** | 4 | M |
| 6 | vereda-nodo | Mock local con `prueba` encendido, para los e2e de la webapp y el QA agéntico | 4 | S |
| 7 | vereda-webapp | Portal, Datos → Cobros: los proveedores del comercio con su estado, activar varios a la vez, conectar con credenciales (los `campos` del anuncio) o por redirección, desconectar, `credenciales_rechazadas`; "por confirmar" de transferencias (en curso); devolver desde el pedido. **Pantallas y copy los decide Leo** (2-3 opciones) | 2 (tipos), 4 y 6 (e2e) | M |
| 8 | vereda-webapp | Comprador: tarjeta en el checkout (solo con `tarjeta` en `medios_cobro`), eligiendo el proveedor entre los `cobradores` del comercio, redirección a `link_pago`, vuelta a `/pedido/:id` con el estado por SSE (en curso, sin proveedor fijo) | 2, 6 | M |
| 9 | vereda-webapp | E2E contra el mock con `prueba`: conectar, pagar, procesado, rechazar, vencer, devolver parcial y total; y `e2e:prod-lectura` sin escribir | 6, 7, 8 | S |
| 10b | vereda-nodo | **Adaptador Mobbex**: `api_key` + `access_token` del comercio, `POST /p/checkout` con `reference` única y sin `split`, re-consulta `GET /p/operations/{id}`, códigos de estado (200–302 pagado), devolución total o parcial desde el día siguiente. Tests con un Mobbex falso | 4 | M |
| 10 | vereda-nodo | **Adaptador Mercado Pago**: OAuth con PKCE y refresh que rota (atómico), preferencia sin `marketplace_fee` con `binary_mode`, webhook HMAC + re-consulta, devolución con `X-Idempotency-Key`, tópico de desconexión → `revocado`. Tests con un MP falso | 4 | L |
| 11 | vereda-app | iOS y Android: tarjeta en el checkout con `SFSafariViewController` / Custom Tabs y vuelta por link universal https (iOS necesita Associated Domains), cobrador en Datos, devolver. **Pantallas y copy los decide Leo** | 2, 5 | M + M |
| 12 | vereda-nodo | Conciliación automática de transferencias con la cuenta MP del comercio. Solo si una transferencia real lo prueba; con Ualá Bis no hay API de transferencias | 10 | M |

Camino crítico para cobrar con tarjeta: **2 → 4 → 5**, con 6 → 9 para probarlo de punta a punta y 7, 8 en paralelo. Mercado Pago (10), Mobbex (10b) y las apps (11) no bloquean a Ualá Bis: cada proveedor es un adaptador aparte y un comercio los suma cuando existan.

Lo que necesita **Leo**:

1. Para Ualá Bis, nada que registrar. En producción, el operador (Leo) genera y guarda la **clave de cifrado del nodo** y enciende `uala_bis`; sin eso el nodo no lo anuncia.
2. Una cuenta Ualá Bis propia con credenciales de **test** si quiere una prueba real antes de abrirlo a comercios (sin eso, todo se prueba contra `prueba` y el Ualá falso).
3. El copy y las pantallas de activar proveedores (varios a la vez, credenciales o botón), de elegir con qué paga el comprador y de devolver, con 2-3 opciones.
4. Para Mercado Pago, cuando toque: la aplicación en "Tus integraciones" (URL de vuelta `https://ar.protocolovereda.com/pagos/mercado_pago/volver`, webhook `https://ar.protocolovereda.com/pagos/mercado_pago/webhook`, tópico `payment`).
5. Los términos del nodo tienen que decir que el comercio es el proveedor y que el cobro es entre el comercio y su pasarela (`legal.md`). Lo escribe el agente de legales.

---

## 5. Riesgos que quedan

- **El refresh token de MP rota en cada uso (confirmado en la doc).** Si el nodo no guarda el nuevo de forma atómica, pierde al comercio y hay que reconectar. El PR 3 lo hace en una sola transacción.
- **Credenciales de Ualá Bis en el nodo.** Con `client_secret_id` se puede cobrar y devolver en la cuenta del comercio. Van cifradas en reposo, se prueban antes de guardarse, nunca salen en una respuesta ni en un log, y desconectar las borra. Que los TyC de Ualá permitan cargarlas en software de un tercero sigue **(NC)**.
- **Aviso de Ualá sin firma.** Cualquiera puede mandar un aviso falso; por eso el nodo nunca cree el cuerpo y re-consulta siempre, y la URL de aviso lleva un token por cobro.
- **Tokens en el nodo.** Un token permite crear cobros y devoluciones en la cuenta del comercio. Cifrado en reposo con clave por variable de entorno, permisos mínimos (`offline_access read write`), revocación desde el portal y aviso al comercio. Hoy el nodo no cifra nada en reposo: es infraestructura nueva y chica.
- **Webhook con la firma de la app del operador para pagos creados con el token del comercio.** Es lo que la doc describe para marketplaces (anexo MP, §3); se prueba en sandbox antes de mergear el PR 4.
- **Costos por provincia.** MP cobra según la provincia del vendedor desde el 2026-03-06 (CABA 6,29 % al momento, PBA y Córdoba 6,60 %; 1,49 % / 1,56 % a 35 días; QR 0,8 % con dinero en cuenta). Es entre el comercio y MP; la app no lo muestra como si fuera de Vereda.
- **Legal.** MercadoLibre S.R.L. está inscripta en el BCRA como PSPCP y agregador, y su procesadora como adquirente: la adhesión del comercio la hace MP. Con fee 0, sin QR propios, sin ordenar transferencias y sin tocar plata, ni el proyecto ni el operador quedarían alcanzados por el BCRA ni la UIF (`cobros/legal.md`). Sigue siendo lectura propia: conviene la opinión escrita de un abogado antes de crecer, no antes del 28.
- **Producción sin datos de prueba.** Todo se prueba contra el mock y el MP falso; en prod solo lectura hasta que Leo cargue la app de MP (`memory-qa`).
