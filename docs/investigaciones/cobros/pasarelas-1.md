# Pasarelas de cobro para comercios de Vereda: Mercado Pago, MODO, Ualá Bis y Naranja X

Investigación de solo lectura, con fuentes públicas. Fecha de consulta: **2026-09-23** (todas las fuentes se leyeron ese día salvo que se indique otra fecha). No se usaron credenciales ni cuentas.

Convenciones:
- `[fuente: URL, fecha]`: la fecha es la de publicación o actualización si la página la muestra; si no, la fecha de consulta (2026-09-23, "consultado").
- **(NC)** = no confirmado en fuente oficial. Puede venir de una fuente secundaria, o la página oficial no cargó.
- Premisa de Vereda: el dinero va del comprador a la cuenta del comercio en el proveedor, Vereda no cobra comisión y el nodo solo necesita enterarse de que el pedido se pagó (webhook).

---

## 1. Mercado Pago (MP)

### 1.1 Cómo se conecta la cuenta del comercio a una plataforma

Hay dos caminos. Los dos cobran en la cuenta del vendedor:

- **A) OAuth, el camino oficial para plataformas.**
  - Flujo `authorization_code`, con PKCE opcional. El comercio autoriza la app de Vereda y Vereda recibe un `access_token` y un `refresh_token` a nombre del vendedor. [fuente: https://www.mercadopago.com.ar/developers/es/docs/security/oauth, consultado 2026-09-23]
  - Vigencia: el `authorization_code` dura 10 min y es de un solo uso. El `refresh_token` dura 6 meses. También existe `client_credentials`, pero solo sirve para los recursos propios de la app. [misma fuente]
  - Una guía técnica de terceros agrega que **el `refresh_token` rota en cada refresh**: si no se guarda el nuevo de forma atómica, se pierde el acceso al vendedor y hay que volver a autorizar. **(NC en doc oficial)** [fuente: https://cesarayala.dev/blog/mercado-pago-split-payments-marketplace/, 2026-06-24]
  - El producto oficial que usa OAuth para cobrar en nombre de vendedores es **"Split de Pagos 1:1 (marketplace)"**:
    - Integraciones soportadas: **Checkout Pro y Checkout API**.
    - Requisito: vendedor con **KYC nivel 6**.
    - El modelo 1:N es solo para vendedores con ejecutivo comercial asignado.
    - [fuente: https://www.mercadopago.com.ar/developers/es/docs/split-payments/split-1-1/prerequisites, consultado 2026-09-23]
  - Uso: "necesariamente usando un access token por cada vendedor, obtenido a través de OAuth". [fuente: https://www.mercadopago.com.ar/developers/en/docs/checkout-pro/how-tos/integrate-marketplace, consultado 2026-09-23]
- **B) El comercio pega sus propias credenciales (access token de producción) en el nodo.**
  - Es lo que hacen los plugins (WooCommerce, Prestashop, etc.).
  - La doc de credenciales dice que se pueden **compartir credenciales "de forma segura con otra cuenta de Mercado Pago"** (máx. 10). Para operar en nombre de terceros recomienda OAuth. [fuente: https://www.mercadopago.com.ar/developers/es/docs/your-integrations/credentials, consultado 2026-09-23]
  - Para activar credenciales de producción, el comercio tiene que declarar rubro y **URL del sitio** (campo obligatorio), aceptar los términos y pasar un reCAPTCHA. Es un paso extra para un comercio chico sin web. [misma fuente]

### 1.2 ¿Se puede cobrar sin comisión de plataforma?

- `marketplace_fee` (Checkout Pro, en `/checkout/preferences`) y `application_fee` (Checkout API, en `/payments`) definen la parte que se lleva la plataforma. Primero se descuenta la comisión de MP y después la del marketplace. [fuente: https://www.mercadopago.com.ar/developers/en/docs/checkout-pro/how-tos/integrate-marketplace, consultado 2026-09-23]
- La doc dice "**si querés** cobrar una comisión… definí el monto en `marketplace_fee`". Eso sugiere que es opcional. [fuente: https://www.mercadopago.cl/developers/pt/docs/checkout-pro-preferences/how-tos/integrate-marketplace, consultado 2026-09-23]
- **No encontré una línea oficial que diga explícitamente "fee = 0 permitido" (NC).** Técnicamente alcanza con omitir el campo: el pago se crea con el token del vendedor y es un pago normal del vendedor.
- Cobrar con el token del vendedor sin ser marketplace: la doc oficial de credenciales permite compartirlas con otra cuenta. No encontré una cláusula que lo prohíba. **(NC en términos legales AR: no pude leer los TyC argentinos completos.)**

### 1.3 Productos y uso desde iOS

- **Checkout Pro** (redirect a MP): en iOS se abre con **SFSafariViewController**, y en Android con Custom Tabs. Con `back_urls` + `auto_return` se vuelve a la app por deep link. [fuente: https://www.mercadopago.com.ar/developers/en/docs/checkout-pro/integrate-checkout-pro/mobile/ios/swift, consultado 2026-09-23]
  - Si el comprador tiene la app de MP, Checkout Pro puede ofrecer pagar con saldo o cuenta.
  - Sirve con OAuth: la preferencia se crea con el token del vendedor.
- **Checkout API / Bricks**: formulario propio con tokenización de tarjeta. Es compatible con `application_fee`. Hay SDK iOS oficial (`mercadopago/sdk-ios`). [fuente: https://github.com/mercadopago/sdk-ios, consultado 2026-09-23]
  - Para Vereda (app libre, sin PCI) conviene más Checkout Pro o Bricks web.
- **Link de pago**: se genera desde el panel del comercio. No tiene API propia; el equivalente programático es la preferencia de Checkout Pro (`init_point`).
- **QR** (estático, dinámico e híbrido) vía **API de Orders**:
  - Doc publicada el 2025-09-24. [fuente: https://www.mercadopago.com.ar/developers/es/news/2025/09/24/QR-Code-Integration-with-Orders-API, 2025-09-24]
  - Descripción de los modelos. [fuente: https://www.mercadopago.com.ar/developers/es/docs/qr-code/overview, consultado 2026-09-23]
  - El QR de MP es interoperable: se puede pagar con otras billeteras, pero en ese caso solo con dinero en cuenta, no con tarjeta. [fuente: https://www.mercadopago.com.ar/herramientas-para-vender/cobrar-con-qr, consultado 2026-09-23]
- **Point** (posnet): se integra con la misma API de Orders. Hay devoluciones parciales vía API desde 2025-12-15. [fuente: https://www.mercadopago.com.ar/developers/es/news/2025/12/15/Generate-partial-refunds-via-API-with-Mercado-Pago-Point, 2025-12-15]
- **No confirmé** si Split 1:1 (con fee) funciona con QR o Point. La doc de prerequisitos solo nombra Checkout Pro y API **(NC)**. Sin fee y con el token del vendedor, QR y Point son cobros normales del vendedor.

### 1.4 Costos para el comercio (precios de lista, sin IVA)

**Checkout / Link de pago (online)** [fuente: https://www.mercadopago.com.ar/herramientas-para-vender/check-out y https://www.mercadopago.com.ar/herramientas-para-vender/link-de-pago, consultado 2026-09-23]

| Acreditación | Comisión |
|---|---|
| En el momento | 6,29% + IVA |
| 10 días | 4,39% + IVA |
| 18 días | 3,39% + IVA |
| 35 días | 1,49% + IVA |

- Las páginas no separan crédito, débito y dinero en cuenta para online: es la misma tasa según el plazo elegido.
- Las cuotas "sin interés" ofrecidas por el comercio se suman: 3x 10,49%, 6x 18,69%, 12x 32,29%, etc.
- "Los costos pueden variar de acuerdo a los impuestos provinciales".

**QR** [fuente: https://www.mercadopago.com.ar/herramientas-para-vender/cobrar-con-qr, consultado 2026-09-23]

| Medio de pago | En el momento | Con plazo |
|---|---|---|
| Dinero en cuenta MP / otras billeteras o bancos (transferencia) | 0,8% + IVA | a 2 días: 0,8% |
| Débito | 1,35% + IVA | a 2 días: 0,85% |
| Crédito | 5,99% + IVA | a 10 días: 4,19% |
| Mercado Crédito (cuotas sin tarjeta) | 1,35% + IVA | — |

- **Ajuste por provincia (vigente desde 2026-03-06, según prensa)**: en PBA, link/checkout al momento 6,60%, a 35 días 1,56%, Point crédito 6,60%, Point débito 3,41%, QR con dinero en cuenta 0,80%. **(NC oficial: fuente secundaria; la página oficial de ayuda devolvió 403.)** [fuente: https://calcularsueldo.com.ar/impuestos/13982/mercado-pago-cambia-sus-cargos-por-venta-asi-quedan-los-nuevos-costos.html, 2026-03-11]
- Tabla oficial detallada de ayuda: https://www.mercadopago.com.ar/ayuda/costo-recibir-pagos_220. **No se pudo leer: 403 o render por JS (NC).**

### 1.5 Alta y requisitos

- Cuenta MP gratuita para persona física o jurídica. Cobrar no exige monotributo (las retenciones cambian según la condición fiscal, ver 1.8). **(NC oficial: no pude leer la ayuda de alta.)**
- Split 1:1: el vendedor necesita **KYC nivel 6** (validación de identidad completa). [fuente: https://www.mercadopago.com.ar/developers/es/docs/split-payments/split-1-1/prerequisites, consultado 2026-09-23]

### 1.6 Webhooks y estados

- Se configuran en "Tus integraciones" o por pago con `notification_url`, que tiene prioridad sobre el panel.
- Tópicos: `payment`, `orders` (API, Point, QR), `topic_merchant_order_wh`, `topic_chargebacks_wh`, etc.
- Firma: header **`x-signature`** (`ts=…,v1=<HMAC-SHA256>`) con la clave secreta de la app, más `x-request-id`. Los SDKs traen `WebhookSignatureValidator`.
- Hay que responder 200 o 201 en **22 s**. Si no, se reintenta cada 15 min, con intervalos más largos después del 3er intento.
- Después se consulta `GET /v1/payments/{id}`. IPN sigue figurando como alternativa, sin aviso de baja.
- [fuente: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/additional-content/notifications/webhooks, consultado 2026-09-23]
- Con OAuth, la app de Vereda recibe las notificaciones de los pagos creados con tokens de sus vendedores (webhook de la app). **(NC explícito en doc.)**
- Estados de pago habituales: `pending`, `approved`, `authorized`, `in_process`, `in_mediation`, `rejected`, `cancelled`, `refunded`, `charged_back`. **(NC: la página oficial de estados devolvió 404 al leerla.)**

### 1.7 Devoluciones y contracargos

- **Refunds API**: `POST /v1/payments/{id}/refunds`, total (body vacío) o parcial (`amount`).
  - Plazo: **hasta 180 días** desde la aprobación.
  - Requiere **saldo suficiente** en la cuenta.
  - Cancelación: solo si el pago está `pending` o `in_process`; los pendientes expiran a los 30 días.
  - [fuente: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-preferences/additional-settings/refunds-and-cancellations, consultado 2026-09-23]
- **En marketplace (Split 1:1)**: la devolución se descuenta **proporcionalmente** de la cuenta del vendedor y de la del marketplace.
  - Si el vendedor no tiene saldo, el marketplace no puede hacer la devolución total: debe devolver su parte y decidir si cubre el resto.
  - [fuente: https://www.mercadopago.com.ar/developers/es/docs/split-payments/split-1-1/integration-configuration/integrate-marketplace, consultado 2026-09-23]
  - Con fee 0, la parte del marketplace es 0, así que **Vereda no pondría dinero**. **(inferencia)**
- **Contracargos**:
  - Los asume el **vendedor**: "el importe en disputa permanece retenido en la cuenta del vendedor". [fuente: https://www.mercadopago.com.ar/developers/es/docs/checkout-api-orders/payment-management/chargebacks/introduction, consultado 2026-09-23]
  - API: `GET /v1/chargebacks/{id}`, `POST /v1/chargebacks/{id}/documentation` (máx. 10 archivos, 10 MB en total, jpg/png/pdf), y una sola presentación mientras `documentation_status=pending`.
  - Resultado: `coverage_applied=true` significa que el vendedor recupera los fondos. La resolución puede tardar hasta 6 meses según la red.
  - [fuente: https://www.mercadopago.com.ar/developers/es/docs/checkout-api-orders/payment-management/chargebacks/management, consultado 2026-09-23]
  - **Quién responde en Split 1:1 (vendedor o marketplace): la doc no lo dice (NC).**

### 1.8 Retenciones e impuestos que aplica MP

- **IIBB vía SIRTAC** (Comisión Arbitral): alícuota por padrón COMARB, **tope 5%**. Adhieren BA, Catamarca, Chaco, Chubut, Córdoba, Entre Ríos, Formosa, Jujuy, La Rioja, Mendoza, Misiones, Neuquén, Río Negro, Salta, San Juan, San Luis, Santa Cruz, Santiago del Estero y Tierra del Fuego. Los certificados se bajan los primeros 5 días hábiles del mes siguiente. **(NC oficial: fuentes secundarias; las notas de vendedores.mercadolibre.com.ar dieron 403.)** [fuente: https://blog.mycontador.com.ar/mercado-pago-retenciones-de-ingresos-brutos-a-traves-del-sirtac/ ; https://contablix.ar/blog/retenciones-percepciones-ecommerce-argentina-2026, consultado 2026-09-23]
- Para no categorizados y monotributistas hay notas oficiales específicas (no se pudieron leer): https://vendedores.mercadolibre.com.ar/nota/retencion-de-iibb-para-sujetos-no-categorizados , https://vendedores.mercadolibre.com.ar/nota/retencion-de-iibb-para-monotributistas-en-mercado-libre **(NC)**
- **IVA y Ganancias**: según fuentes secundarias, las **retenciones** de IVA y Ganancias se eliminaron desde 2024-09-01 (RG 5554/2024). Sigue una **percepción de IVA** (RG 5319/2023, mod. RG 5794/2025): 8% si no tiene impuestos activos en ARCA, 7% para monotributistas excedidos, 1–3% para RI. **(NC oficial.)** [fuente: https://contablix.ar/blog/retenciones-percepciones-ecommerce-argentina-2026, consultado 2026-09-23]

---

## 2. MODO

### 2.1 Qué es y cómo se conecta

- MODO **no es adquirente ni tiene cuenta de comercio propia**. Es un "facilitador tecnológico" que manda la transacción al gateway del comercio. [fuente: https://merchants.modo.com.ar/docs/f7d031b5-f72c-4bfc-b1c9-e24fbf7a10de, 2025-05-12]
- **Online (Botón de pago, SDK v2)**: el comercio tiene que estar dado de alta en un gateway:
  - Gateways: Decidir Plus / Payway Ventas Online, Decidir 2.0, Posnet Gateway (IPG/Fiserv), Getnet o Line Payments.
  - Después completa el formulario de MODO y en **~48 h hábiles** recibe **username + password + processor_code**.
  - [fuente: https://merchants.modo.com.ar/docs/384027d2-6a91-436d-9151-add574d58af6, 2026-04-29 ; https://merchants.modo.com.ar/docs/bf5f5ddd-e9d2-40c8-ae64-5c8078caca89, 2026-03-16]
- Auth: `POST {base}/v2/stores/companies/token` con username y password.
  - Devuelve un JWT válido **7 días**.
  - Rate limit: **10 pedidos cada 10 min**.
  - Header `User-Agent: <Merchant-Name>` obligatorio.
  - [fuente: https://merchants.modo.com.ar/docs/ae9bf7c2-01cb-4107-9147-9649882bc5c0, 2025-08-26]
- **No existe OAuth ni modelo "plataforma"**: cada comercio tiene sus credenciales. Para Vereda, el comercio tendría que cargar en el nodo su username y password de MODO. Hay un "Multi-Merchant" documentado solo para el plugin de Magento. [índice: https://merchants.modo.com.ar/docs]
- Para el alta en Payway, el CUIT tiene que estar **inscripto en AFIP/ARCA en alguna condición de IIBB**: sin inscripción no hay alta. Pasos: primero el establecimiento e-commerce en Payway; 24 h después, la cuenta Decidir Plus. [fuente: https://www.modo.com.ar/ayuda/preguntas-frecuentes/C%C3%B3mo-generar-claves-de-Payway-y-Payway-ventas-online, consultado 2026-09-23]
- **QR presencial**: lo emite el adquirente del comercio (Payway, Fiserv/Posnet, Clover, Nave, Getnet). No hay alta en MODO. [fuente: https://www.modo.com.ar/blog/como-aceptar-pagos-con-qr-con-modo-en-tu-comercio, consultado 2026-09-23]

### 2.2 Fee de plataforma

- MODO no tiene concepto de fee de plataforma. Tiene **split de pagos** (`sub_payments`), solo con Decidir 2.0 (con "pagos distribuidos") o Line. La suma de subpagos tiene que ser igual al total. [fuente: https://merchants.modo.com.ar/docs/cbbac79b-68a5-43ac-9e8a-4b15dad314f1, 2025-09-29]
- Sin split, el pago va entero al establecimiento del comercio. **Fee 0 es el caso por defecto.**

### 2.3 Productos y uso desde iOS

- Botón de pago:
  - `POST {base}/v2/payment-requests/` con `amount`, `currency=ARS`, `cc_code` (cuotas), `processor_code`, `external_intention_id` único y `webhook_notification` opcional.
  - Responde **`qr` + `deeplink`** (`https://www.modo.com.ar/pagar/…`).
  - Vence en **5 a 10 min** (default 10).
  - [fuente: https://merchants.modo.com.ar/docs/f6bc2e95-a4c3-47c4-8db9-de9d1e8d4024, 2026-03-18 ; contenido v2 visto en la página de Split, 2025-09-29]
- Flujo mobile: se redirige a una pantalla en el navegador donde el usuario **elige la app del banco o MODO**, y esa app se abre por **deep link**. Desde iOS alcanza con abrir el deeplink (`UIApplication.open`) o la web en SFSafariViewController. [fuente: https://merchants.modo.com.ar/docs/2dfd535a-89ff-40ab-80c7-b7ebc5bb4564, 2025-05-12]
- Medios: débito y crédito de bancos adheridos (con promos bancarias), y "cuenta bancaria" (`payment_method: ACCOUNT`, según la doc de devoluciones).

### 2.4 Costos

- "Sin costos ni comisiones adicionales" de MODO: el comercio paga el arancel de su gateway o adquirente. [fuente: https://www.modo.com.ar/comercios/tiendas-online, consultado 2026-09-23]
- Referencia Payway (e-commerce y link de pago):
  - Débito 2,0%. Crédito 3,0% (Amex 2,8%).
  - **Débito 0% para monotributistas.**
  - Acreditación: débito 1 día hábil; crédito 5, 8, 10 o 18 días hábiles según el rubro (BCRA).
  - "Anticipación" a 24 h con costo aparte.
  - **Falta confirmar si es + IVA y la fecha de la tabla (NC).**
  - [fuente: https://ayuda.payway.com.ar/cobros/plazos-acreditacion-y-comisiones, consultado 2026-09-23]
- Por norma, el crédito tiene un **tope de arancel de 1,8%** (según el buscador para Payway). **(NC: contradice el 3,0% de arriba; puede ser para POS/presencial.)** [fuente: https://ayuda.payway.com.ar/novedades/cambio-de-aranceles-0, consultado 2026-09-23]

### 2.5 Webhooks y estados

- Webhook en la URL registrada en el alta o en `webhook_notification`. Hay que responder 200 inmediato y procesar de forma asíncrona.
- **Firma: JWS flattened (RFC 7515)** en el campo `signature` del body. Se valida contra el JWKS `https://merchants.playdigital.com.ar/v2/payment-requests/.well-known/jwks.json` y se compara el payload firmado con el body.
- Estados: `CREATED`, `SCANNED`, `PROCESSING`, `ACCEPTED`, `REJECTED`.
- Reintentos: máx. 3, **solo ante 5xx** (a los 2 s, 4 s y 8 s).
- [fuente: https://merchants.modo.com.ar/docs/23d9d449-a132-4cbb-8466-d8086d90b41c, 2026-01-07]

### 2.6 Devoluciones y contracargos

- `POST {base}/v2/payment-requests/{id}/refund` con `amount` opcional (sin él, devuelve el total).
  - Hay que usar **siempre** este flujo, o las promos o el cashback quedan mal.
  - Parciales: mínimo $30 en Decidir y Line, $8 en Getnet (D+1).
  - Con `ACCOUNT` vía Payway **solo se puede devolver el total**.
  - [fuente: https://merchants.modo.com.ar/docs/06de9e0c-7507-4661-b4ee-b493a25184c4, 2026-09-21]
- Contracargos: los gestiona el **gateway o adquirente** del comercio (Payway, Fiserv, etc.), no MODO. MODO menciona "protección contra contracargos" en su marketing sin detallarla. **(NC.)** [fuente: https://www.modo.com.ar/comercios/tiendas-online, consultado 2026-09-23]

### 2.7 Retenciones

- Las aplica el adquirente (Payway/Fiserv): SIRCREB, SIRTAC y regímenes provinciales según la condición fiscal. **(NC: no se revisó la documentación fiscal de Payway.)**

---

## 3. Ualá Bis

### 3.1 Conexión

- **API Cobros Online v2**. Auth por **`client_credentials`**: `username` + `client_id` + `client_secret_id` en `https://auth.developers.ar.ua.la/v2/api/auth/token`. El token dura **24 h**. [fuente: https://developers.ualabis.com.ar/v2/authentication/create, consultado 2026-09-23]
- Las credenciales se piden desde la app (Cobros → Tiendas online → Página web) o en el portal, y llegan por mail. [fuente: https://www.ualabis.com.ar/apicheckout, consultado 2026-09-23]
- **No hay OAuth ni modelo multi-comercio**: cada comercio carga sus credenciales en el nodo.
- La API v1 queda deprecada el **2026-12-31**. [fuente: https://developers.ualabis.com.ar/, consultado 2026-09-23]
- Los TyC dicen que "la Cuenta de Usuario y las **Claves** serán personales… **intransferibles**". Se refiere a la clave de acceso a la cuenta. **No encontré una cláusula específica sobre credenciales de API cargadas en una plataforma de terceros (NC).** [fuente: https://assets.ctfassets.net/t5yal6u1wvnw/1EsrWh7PHBXHsiLdMpJShT/c6985c60a366656085b5e09d66af3052/_05.05.23__-_TyC_UalaBis.docx.pdf, 2023-05-05]

### 3.2 Fee de plataforma

- No existe split ni `application_fee`: el cobro es 100% del comercio. Fee 0 por construcción.

### 3.3 Productos y uso desde iOS

- `POST https://checkout.developers.ar.ua.la/v2/api/checkout` con `amount`, `description`, `callback_success`, `callback_fail`, `notification_url` y `external_reference`.
  - Devuelve un **`checkout_link`** (checkout web alojado).
  - Monto entre $25 y $9.999.999.
  - [fuente: https://developers.ualabis.com.ar/v2/orders/create, consultado 2026-09-23]
- Desde iOS: abrir `checkout_link` en SFSafariViewController y volver por `callback_success` (universal link). No encontré un SDK nativo ni un deep link a la app de Ualá **(NC)**.
- Hay SDK oficial Node: https://github.com/Uala-Developers/ualabis-nodejs
- Link de pago y QR (interoperable) se generan desde la app. No encontré una API pública para el QR **(NC)**. [fuente: https://www.ualabis.com.ar/qr, consultado 2026-09-23]

### 3.4 Costos

- **Link de pago: 4,9% + IVA** en crédito, débito y prepagas. [fuente: https://www.ualabis.com.ar/link-de-pago, consultado 2026-09-23 (hero "agosto2026")]
- Checkout (API / Tiendanube): 4,9% + IVA para cualquier medio, con **acreditación instantánea** en la cuenta Ualá. [fuente: https://ayuda.tiendanube.com/es_ES/uala/preguntas-frecuentes-sobre-uala-bis, 2026-02-11]
- **QR**: 0% los primeros 3 meses (franquicia BCRA), después 0,8% en todos los medios. **(según snippet del sitio oficial; falta confirmar el IVA.)** [fuente: https://www.ualabis.com.ar/qr, consultado 2026-09-23]
- No ofrece plazos de acreditación alternativos: todo se acredita "en el acto".
- Un buscador mostró cifras distintas para link (4,4% + IVA) **(NC, posiblemente desactualizado)**.

### 3.5 Alta y requisitos

- Cuenta Ualá (app) y aceptar los TyC de Cobros. Puede ser persona física (no inscripta, monotributo o RI) o jurídica (Ualá Bis Empresas). [fuente: https://www.ualabis.com.ar/personas-juridicas, consultado 2026-09-23]
- La activación tarda ~24 h si ya es usuario Ualá y ~48 h si es nuevo. [fuente: Tiendanube FAQ, 2026-02-11]

### 3.6 Webhooks y estados

- Se envía un POST a `notification_url` con `uuid`, `external_reference`, `status`, `created_date` y `api_version`.
- Estados: `PENDING` (al crear), `PROCESSED`, `APPROVED`, `REJECTED`.
- Hay que responder 200. Si no, se reintenta hasta 3 veces más.
- **No hay firma documentada.** Mitigación: el nodo tiene que volver a consultar la orden con `GET /orders/{uuid}` antes de marcarla pagada.
- [fuente: https://developers.ualabis.com.ar/v2/orders/create/webhook, consultado 2026-09-23]

### 3.7 Devoluciones y contracargos

- API: `POST /orders/{uuid}/refund` (`amount`, `notification_url`), solo para órdenes `APPROVED`. Webhook `REFUNDED` / `NOT_REFUNDED`. [fuente: https://developers.ualabis.com.ar/v2/refunds/create y /v2/refunds/create/webhook, consultado 2026-09-23]
- Según los TyC y Tiendanube, **solo se puede devolver el total**.
  - Desde 24 h y hasta 30 días después del cobro.
  - Hace falta saldo suficiente.
  - [fuente: Tiendanube FAQ, 2026-02-11 ; TyC §9, 2023-05-05]
- **Contracargos**: "Ualá trasladará al Usuario la responsabilidad por la transacción cuestionada. El Usuario autoriza… a debitar el monto". [fuente: TyC Ualá Bis §8, 2023-05-05]

### 3.8 Retenciones

- Según la condición fiscal declarada, "AFIP, los fiscos provinciales y/o municipales" pueden aplicar retenciones y percepciones. [fuente: TyC §fiscal, 2023-05-05]
- Ualá (como billetera) está adherida a **SIRCUPA** (IIBB sobre cuentas de pago). [fuente: https://chequeado.com/el-explicador/preguntas-y-respuestas-sobre-la-nueva-retencion-de-ingresos-brutos-que-arba-aplicara-sobre-transferencias-a-billeteras-virtuales/, consultado 2026-09-23]
- No se confirmó si además aplica SIRTAC a los cobros con tarjeta **(NC)**.

---

## 4. Naranja X

**Aviso:** el día de la consulta (2026-09-23) todo naranjax.com devolvía **HTTP 500** ("Estamos trabajando para volver pronto…"), y developers.naranjax.com daba **403** (challenge de Cloudflare). Casi todo lo que sigue sale de snippets de buscador de páginas oficiales **(NC hasta verificar)**.

### 4.1 Conexión

- Hay portal de desarrolladores (https://developers.naranjax.com/) y se mencionan "integración por API y plugins". No se pudo leer. **Mecanismo de auth, OAuth o multi-comercio: NC.** Existe un plugin WooCommerce de terceros (Wanderlust). [fuente: https://shop.wanderlust-webdesign.com/shop/woocommerce-naranjax/, consultado 2026-09-23]
- Productos: **botón de pago** para web o catálogo, **link de pago** (WhatsApp/redes), **QR interoperable**, Tap (celular como POS) y POS. [fuente: https://www.naranjax.com/soluciones-de-cobro y https://www.naranjax.com/codigo-qr-comercios, snippets, consultado 2026-09-23]

### 4.2 Fee de plataforma

- No se encontró split ni fee de plataforma. **NC.**

### 4.3 Costos (snippets oficiales, NC)

- Crédito: "arancel por venta del **1,8% + IVA**", más **costo de financiación** según el plazo. Ejemplo oficial con Plan Z y "Día NX": 1,8% + 8,65% de financiación (+ IVA). [fuente: https://www.naranjax.com/gestiona-tus-ventas (snippet), consultado 2026-09-23]
- Plazos para Tap, Link y QR: **en el día, a 2, a 14 o a 60 días**, según débito o crédito. Se eligen en la app con la primera venta.
- Dinero en cuenta: **0,8% + IVA**. Con tarjeta Naranja X "no se descuenta extra".
- También pueden sumarse impuestos provinciales o municipales.

### 4.4 Alta, webhooks, devoluciones, contracargos, retenciones

- **Todo NC**: no se pudo leer la documentación. Los TyC de Soluciones de Cobro están en un dominio de dev caído (https://images-flow-toque.new-dev.naranja.dev/toque-images/tos.pdf → 530).

---

## 5. Encaje con Vereda (análisis)

- **Webhook confiable y firmado**:
  - MP: HMAC `x-signature`.
  - MODO: JWS con JWKS público.
  - Ualá Bis: sin firma, así que hay que re-consultar la orden.
  - Naranja X: desconocido.
- **Conexión sin que Vereda toque plata ni secretos compartidos**:
  - Solo MP ofrece OAuth: el comercio autoriza y el nodo guarda un token revocable. Hay que manejar la rotación del refresh cada ≤6 meses.
  - En MODO y Ualá Bis el comercio carga sus credenciales en el nodo: el nodo custodia secretos de cobro.
- **Fee 0**:
  - MP: se omite `marketplace_fee` / `application_fee`, o se usa el token propio del comercio.
  - MODO y Ualá: no hay fee de plataforma.
  - Ningún proveedor obliga a cobrar comisión de plataforma **(MP: NC explícito)**.
- **Devoluciones**: con OAuth o credenciales, el nodo puede devolver vía API (MP hasta 180 días y parcial; MODO según gateway; Ualá solo total y ≤30 días). El dinero siempre sale del saldo del comercio.
- **Contracargos**: en todos los casos confirmados (MP y Ualá) los absorbe el comercio. En MODO, el adquirente del comercio. Vereda queda afuera siempre que no cobre fee **(MP split: NC)**.
- **Fricción de alta**:
  - Ualá Bis: la más baja (app + credenciales por mail).
  - MP: baja si ya tiene cuenta, pero producción pide URL de sitio. Con OAuth, esa URL la pone Vereda (la app es de Vereda).
  - MODO: la más alta (Payway + IIBB inscripto + formulario + 48 h).
- **iOS**: todo se resuelve con checkout web en SFSafariViewController más universal link de vuelta (MP y Ualá), o con el deep link de MODO. No hace falta SDK nativo ni manejar datos de tarjeta (PCI fuera de alcance).
- **Precaución App Store**: los pedidos son bienes físicos o comida, así que no aplica el IAP de Apple (guideline 3.1.3(e)). **(NC: no se verificó en esta investigación.)**

---

## 6. Tabla resumen

| Proveedor | Conexión | Fee plataforma 0 posible | Costo comercio (sin IVA) | Acreditación | Alta | Webhook | Devoluciones / contracargos | Encaje con Vereda |
|---|---|---|---|---|---|---|---|---|
| **Mercado Pago** | OAuth (auth code + PKCE, refresh 6 meses) **o** access token propio | Sí: omitir `marketplace_fee`/`application_fee` (opcional según doc; "0 explícito" NC) | Online: 6,29% al momento / 4,39% 10d / 3,39% 18d / 1,49% 35d. QR: 0,8% cuenta, 1,35% débito, 5,99% crédito. Varía por provincia (PBA 6,60% desde 2026-03, NC) | Al momento a 35 días, elegible | Cuenta MP; KYC 6 para split; URL de sitio para credenciales prod | Sí, HMAC `x-signature`, 22 s, reintentos | API total/parcial ≤180 d con saldo; contracargo al vendedor (split: NC) | **Alto**: única con OAuth, firma, QR y Point |
| **MODO** | Credenciales por comercio (user/pass → JWT 7 d); requiere gateway (Payway/Fiserv/Getnet/Line) | Sí (no hay fee; split opcional con Decidir/Line) | MODO 0%. Arancel del gateway (Payway e-comm: débito 2%, crédito 3%; débito 0% monotributo; IVA y fecha NC) | Según gateway (débito 1 d hábil, crédito 5–18 d hábiles) | Payway + CUIT inscripto IIBB + form MODO (48 h) | Sí, JWS + JWKS; reintento solo ante 5xx | API refund (parcial según gateway); contracargo vía adquirente | **Medio**: buen webhook y deep link, pero alta pesada y sin OAuth |
| **Ualá Bis** | Credenciales por comercio (client_credentials, token 24 h) | Sí (no existe fee) | Link/API 4,9% todo medio; QR 0,8% (0% primeros 3 meses) | Instantánea | App Ualá, persona física o jurídica, 24–48 h | Sí, **sin firma**; hasta 3 reintentos | API solo total, 24 h–30 d; contracargo al comercio (TyC) | **Medio**: alta simple, pero sin firma ni OAuth; caro en tarjeta |
| **Naranja X** | NC (portal dev inaccesible) | NC | Crédito 1,8% + financiación según plazo; cuenta 0,8% (NC) | En el día / 2 / 14 / 60 d (NC) | NC | NC | NC | **Bajo / pendiente**: sin doc verificable hoy |

---

## 7. No confirmado (pendiente de verificar)

1. **MP**: una frase oficial que permita `marketplace_fee = 0` u omitirlo en Split 1:1. Tampoco se revisaron los TyC argentinos sobre usar el token del vendedor sin ser marketplace.
2. **MP**: quién responde el contracargo en Split 1:1 (vendedor o marketplace), y si el marketplace sin fee queda expuesto.
3. **MP**: la tabla oficial de costos por medio (crédito, débito, dinero en cuenta) para online y el ajuste provincial vigente. La página de ayuda `costo-recibir-pagos_220` no fue legible (403 / JS).
4. **MP**: la lista oficial de estados de pago (la página dio 404) y si los webhooks de pagos OAuth llegan a la app del integrador.
5. **MP**: si Split 1:1 soporta QR o Point.
6. **MP**: la rotación del `refresh_token` en cada uso (solo fuente secundaria).
7. **MP / general**: las retenciones SIRTAC y la percepción de IVA (RG 5319/5794), solo de fuentes secundarias. Las notas oficiales de vendedores.mercadolibre.com.ar dieron 403.
8. **MODO/Payway**: si los aranceles de Payway e-commerce son + IVA, la fecha de la tabla y la contradicción con el "hasta 1,8%" de crédito.
9. **MODO**: qué cubre la "protección contra contracargos".
10. **Ualá Bis**: el IVA sobre el 0,8% de QR, si aplica SIRTAC a los cobros con tarjeta, y si existe firma de webhook o una API de QR.
11. **Ualá Bis**: si los TyC permiten cargar credenciales de API en una plataforma de terceros (la cláusula de "Claves intransferibles" es sobre la clave de acceso a la cuenta).
12. **Naranja X**: todo (auth, webhooks, devoluciones, contracargos, alta, costos exactos). El sitio devolvía 500 y el portal dev 403 el 2026-09-23. Hay que reintentar.
13. **Apple**: que la guideline 3.1.3(e) exime a Vereda de IAP por bienes físicos.
