# Pasarelas de pago en Argentina para Vereda (parte 2)

Investigación de solo lectura sobre fuentes públicas. Fecha de consulta de **todas** las fuentes: **2026-09-23**, salvo que se indique otra fecha de publicación o actualización.
Las fuentes de terceros (comparadores, blogs) están marcadas como **[secundaria]**. Lo que no pude verificar en una fuente oficial va a la sección **No confirmado**.

**Requisito de Vereda:** cada comercio cobra en **su propia cuenta** del proveedor. El nodo (open source, lo puede operar cualquiera) **no toca la plata ni cobra comisión**, y solo necesita enterarse por webhook de que el pedido está pagado.

## Vocabulario

- **Agregador (PSP/payfac):** el proveedor es el comercio ante Visa y Mastercard (sus números de comercio), y el vendedor opera como sub-comercio. Alta rápida con CUIT o CUIL, sin contrato de adquirencia propio. Ejemplos: Ualá Bis, Mobbex Agrupador, dLocal Go.
- **Adquirente directo:** el comercio firma directamente con el adquirente (Payway, Fiserv, Getnet) y recibe **su propio número de establecimiento**. El adquirente liquida a la cuenta bancaria del comercio.
- **Gateway:** capa técnica que procesa contra los números de comercio **propios** del comercio, que los tuvo que sacar antes con un adquirente. Ejemplos: Payway gateway "venta online", Mobbex Gateway.

---

## 1. Mobbex

- **Conexión de terceros: Dev Connect (tipo OAuth).** Es el mejor encaje encontrado.
  - Flujo: la plataforma llama a `/developer/connect` con un `return_url`. El comercio se autentica en `mobbex.com/p/developer/connect/...` y vuelve con `connectStatus=done`. Después la plataforma pide `/developer/connect/{id}/credentials` y recibe el **access token** del comercio, más su nombre, CUIT y logo. [fuente: https://mobbex.dev/dev-connect, consultado 2026-09-23]
  - Mobbex lo promociona para "ERPs, CRMs y SaaS" que embeben cobros "por tenant". [fuente: búsqueda sobre mobbex.dev/dev-connect, 2026-09-23]
- **Crear el checkout:** van dos headers, `x-api-key` (la app, o sea la plataforma) y `x-access-token` (el comercio). [fuente: https://mobbex.dev/checkout, 2026-09-23]
  - Así el nodo podría crear checkouts **en la cuenta del comercio** con su propia api-key de desarrollador.
- **Webhook:** se configura **por checkout** (campo `webhook`). Es un POST JSON cuando la operación queda aprobada, rechazada, vencida o capturada. Si el checkout vence, llega un aviso `checkout_expired`.
  - El campo `reference` es único e impide dos pagos con la misma referencia, así que sirve como id del pedido. [fuente: https://mobbex.dev/checkout y https://mobbex.dev/webhooks, 2026-09-23]
  - La doc **no menciona firma** del webhook. Ver No confirmado.
- **Split y marketplace:** existe (parámetro `split`).
  - En la modalidad "split distribuido", todos los comercios operan en Mobbex Gateway **con sus propios números de establecimiento**, y la prevención de fraude queda a cargo del ORIGINADOR. [fuente: https://ayuda.mobbex.com/modalidad-con-split-de-pagos, 2026-09-23]
  - **Vereda no necesita split:** con Dev Connect, cada comercio es el merchant de su propia cuenta y la plataforma no retiene nada.
- **Dos modalidades:**
  - **Agrupador** (Mobbex agrega): el comercio "asume total responsabilidad" por las decisiones de los adquirentes sobre contracargos, y Mobbex le traslada los costos. [fuente: T&C Mobbex Agrupador, https://ayuda.mobbex.com/terminos-y-condiciones-de-mobbex-agrupador, visto en snippet de búsqueda 2026-09-23. La página devolvió "not found" al abrirla.]
  - **Gateway:** usa números de comercio propios. [fuente: https://ayuda.mobbex.com/modalidad-con-split-de-pagos]
- **Costos, plan Essential:** 1,9% + IVA en débito, 2,6% + IVA en crédito y prepagas, 3,9% + IVA en suscripciones. Sin alta ni mínimos.
  - El plan Enterprise tiene arancel a medida, un mínimo de $70.000.000/mes, multiadquirente y split. [fuente: https://www.mobbex.com/planes/, 2026-09-23]
- **Acreditación:** débito en 2 días hábiles, crédito entre 10 y 18 días hábiles según la entidad, QR al instante. [fuente: https://www.mobbex.com/faq/, 2026-09-23]
- **Alta:** "lleva unos días hábiles según validación". Los requisitos exactos no figuran en el FAQ. [fuente: https://www.mobbex.com/faq/]
- **Medios de pago:** tarjetas, transferencia, DEBIN, Rapipago y Pago Fácil, billeteras (MODO, Ualá, NaranjaX), QR interoperable del BCRA. Hay SDK Node (`mobbex` en npm) y plugins para WooCommerce, Magento, PrestaShop, VTEX y Tiendanube. [fuentes: https://www.mobbex.com/faq/, https://www.npmjs.com/package/mobbex, 2026-09-23]
- **Tipo:** **agregador (Essential/Agrupador) o gateway (con números propios)**.

## 2. Payway (ex Prisma / Decidir)

- **Qué es:** adquirente directo. El comercio "se adhiere a Payway" y recibe por mail **su número de establecimiento** y sus credenciales. [fuente: https://ayuda.payway.com.ar/cobros/medios-de-pago/venta-online, 2026-09-23]
- **Conexión de terceros:** **no hay OAuth**.
  - Cada sitio tiene una API key pública y una privada, entregadas por soporte de Payway. [fuentes: https://github.com/payway-ar/sdk-php-ventaonline y https://github.com/payway-ar/sdk-node-ventaonline, 2026-09-23]
  - Para Vereda, el comercio tendría que **cargar sus propias keys en el nodo**.
  - Endpoints: `https://developers-ventasonline.payway.com.ar/api/v2` (sandbox) y `https://ventasonline.payway.com.ar/api/v2` (producción). [fuente: https://github.com/payway-ar/sdk-java-ventaonline]
- **API y SDK:** tokenización del lado del front (SDK JS) y cobro del lado del back. Hay SDKs en PHP, Java, .NET y Node, y plugins para WooCommerce y PrestaShop. Docs en https://developers.payway.com.ar/ y https://documentacion-ventasonline.payway.com.ar/.
  - Existe un formulario de pago (hosted) con `notifications_url`, "URL donde se enviarán notificaciones relacionadas con la operación". [fuente: https://github.com/payway-ar/sdk-node-ventaonline/blob/master/README.md, 2026-09-23]
  - El formato y la firma del webhook no están confirmados.
- **Devoluciones:** totales (`refund`) y parciales (`partialRefund`), y ambas se pueden anular. [fuente: README SDK Node, idem]
- **Split y agregadores:**
  - "Pagos distribuidos" (`sub_payments` por monto o por porcentaje).
  - `aggregate_data` para que un **comercio agregador** informe los datos del sub-comercio. Eso implica que la plataforma sea agregador ante Payway, lo cual **no encaja** con Vereda.
  - [fuente: idem]
- **Costos:**
  - Plataforma de venta online: "1% + IVA por venta online", además de los aranceles de las tarjetas. [fuente: https://ayuda.payway.com.ar/cobros/medios-de-pago/venta-online, 2026-09-23]
  - Aranceles de e-commerce y link de pago: **débito 2,0%, crédito 3,0%**.
  - Presencial: débito 1,2% (Visa/Cabal) o 1,4% (Master); crédito 2,0%; AMEX 2,8%; QR 0,8%.
  - Monotributistas: 0% en productos de débito.
  - [fuente: https://ayuda.payway.com.ar/cobros/plazos-acreditacion-y-comisiones, 2026-09-23]
  - Hubo cambio de aranceles de débito el 24/04/2026. [fuente: https://ayuda.payway.com.ar/novedades/cambio-de-aranceles-0, snippet 2026-09-23]
- **Acreditación:** débito en 1 día hábil. Crédito en 5, 8, 10 o 18 días hábiles según el rubro (AMEX 9). QR al instante. Prepaga en 2 días hábiles. [fuente: idem]
- **Contracargos:** los gestiona Payway como adquirente contra el comercio (práctica estándar). No encontré la cláusula exacta; ver No confirmado.
- **Tipo:** **adquirente directo + gateway**. El comercio necesita su número de establecimiento de Payway, pero no contratos separados con cada marca.

## 3. Getnet (Santander)

- **Qué es:** adquirente directo. "El dinero… lo vas a recibir directamente en tu cuenta bancaria sin intermediarios". Para integrar hay que "comunicarse con un ejecutivo de ventas". [fuente: https://www.getnet.net/ar/cobra-online/get-checkout, 2026-09-23]
- **Conexión de terceros:** **no hay OAuth**.
  - El comercio pide un Client ID y un Client Secret a consultasecommerce@globalgetnet.com.ar.
  - En el plugin se carga la URL del webhook ("Notificaciones") junto con un usuario y contraseña de webhook que define el propio comercio.
  - [fuente: https://www.getnet.net/ar/ayuda/integraciones-ecommerce/woocommerce, snippet 2026-09-23. La central de ayuda devolvió 503.]
- **API:**
  - Web Checkout en iFrame, lightbox o redirect, para AR, CL, UY y otros. [fuente: https://docs.globalgetnet.com/en/products/online-payments/web-checkout, 2026-09-23]
  - Hay productos "Payment Link API" y "Chargeback API". [fuente: https://docs.globalgetnet.com/en/products]
  - La "Global/Regional API" lista Argentina. [fuente: https://docs.globalgetnet.com/en/products/online-payments/regional-api]
- **Marketplace/split:** existe la Marketplace API, pero el split figura **solo para Brasil**. [fuente: https://docs.globalgetnet.com/en/products/online-payments/marketplace-api, snippet 2026-09-23]
- **Costos:** el arancel depende del plazo de acreditación que elija el comercio. Tope "hasta", más IVA:
  - QR: 0,80%, acreditación inmediata.
  - Débito: 1% (1 día hábil), 1,53% (inmediata).
  - Crédito en 1 pago: 2% (8 días hábiles), 6,75% (24 h), 7,28% (inmediata).
  - La acreditación inmediata es solo con cuenta Santander.
  - [fuente: https://www.getnet.net/ar/aranceles, 2026-09-23]
  - No está claro si estos aranceles aplican igual a Get Checkout online. Ver No confirmado.
- **Tipo:** **adquirente directo**. El número de comercio es de Getnet.

## 4. Fiserv Argentina (ex First Data / Posnet / Clover)

- **Link de pago Fiserv:**
  - Requiere ser **comercio Fiserv existente**, con terminal Posnet o Clover y número de comercio activo.
  - Bonificado al 100% por 12 meses. 3DS Mastercard: 2,5 pb (tope USD 3).
  - Acreditación: débito 48 h hábiles, crédito en 1 cuota 10 días hábiles, crédito en 2 o más cuotas 48 h hábiles.
  - La página **no menciona API ni webhook**.
  - [fuente: https://linkdepago.fiservargentina.com/, 2026-09-23]
- **Clover:** la **Ecommerce API de Clover figura solo para "North America"**. Para Argentina hay REST API, Pay Display (semi-integrado) y webhooks del lado de POS. [fuentes: https://docs.clover.com/dev/docs/region-specific-features y https://docs.clover.com/dev/docs/quick-reference-guides-latam-developers, 2026-09-23]
  - Clover sí tiene OAuth v2 para apps del App Market. [fuente: https://docs.clover.com/dev/docs/ecommerce-api-tokens-and-oauth-api-tokens]
  - No encontré que eso aplique a cobros online en AR.
- **Fiserv LATAM eCommerce API:** existe (Api-Key y Message-Signature HMAC, devoluciones y anulaciones). La página muestra "Mexico" y **no confirma Argentina ni webhooks**. [fuente: https://docs.apis-fiserv.com/latam/docs/ecommerce-api-eng, 2026-09-23]
- **MODO:** "Si cobrás con PosNet Gateway de Fiserv, contactá a tu asesor comercial para integrar MODO". Esto sugiere que existe un "Posnet Gateway" e-commerce. [fuente: https://www.modo.com.ar/comercios/tiendas-online/integracion-modo, snippet 2026-09-23]
- **Tipo:** **adquirente directo**. El e-commerce por API para terceros en AR **no está confirmado** públicamente.

## 5. dLocal y dLocal Go

- **dLocal (enterprise):** su modelo es el cruce de fronteras. Actúa como **merchant of record** local para comercios extranjeros. "For Platforms" hace onboarding, split y retención de fondos, o sea que la plataforma cobra por cuenta de sus usuarios. [fuentes: https://www.dlocal.com/our-solution/dlocal-for-platforms/, snippet 2026-09-23; https://docs.dlocal.com/docs/argentina]
  - Soporta tarjetas locales, transferencias, Rapipago, Pago Fácil, QR interoperable y MODO. Tiene refunds y chargebacks en tarjetas. El QR no admite refund. [fuente: https://docs.dlocal.com/docs/argentina, 2026-09-23]
  - Encaje con Vereda: **malo**. Es para plataformas que custodian fondos.
- **dLocal Go (autoservicio):**
  - Se puede abrir con empresa registrada en Argentina, entre otros países. [fuente: https://helpcenter.dlocalgo.com/es/articles/7065105-donde-tiene-que-estar-registrada-mi-empresa-si-quiero-abrir-una-cuenta-de-dlocal-go, snippet 2026-09-23]
  - Sin costos fijos. Hasta USD 3.000 procesa con el paso 1 de verificación; para volumen ilimitado y retiros hace falta el paso 2. [fuente: https://helpcenter.dlocalgo.com/en/articles/7339127-how-do-i-integrate-my-website-with-the-dlocal-go-api]
  - Acreditación al saldo dLocal Go: tarjeta 7 días, transferencia 3 días; después hasta 48 h hábiles al banco. [fuente: helpcenter dLocal Go, snippet 2026-09-23]
  - Tarifario de pagos **internacionales**, Argentina (documento "April 2023"): tarjetas 3,49%, efectivo 2,99%, transferencia 1,99%, más impuestos. [fuente: https://dlocalgo.com/wp-content/uploads/2024/09/pricinglist.pdf, 2026-09-23]
  - Devolución de menos de USD 10: fee de USD 1. [fuente: https://helpcenter.dlocalgo.com/en/articles/6960181-dlocal-go-fees]
  - API: cada cuenta tiene sus propias keys (ver doc https://docs.dlocalgo.com/integration-api/). No hay OAuth para plataformas.
- **Tipo:** **agregador / merchant of record**. Es la opción pensada para cobro cross-border. Para un comercio argentino vendiendo en ARS a vecinos, el encaje no está confirmado.

## 6. Stripe

- **Argentina no figura** entre los países donde un negocio puede abrir una cuenta Stripe. En LatAm solo aparecen Brasil y México. [fuente: https://stripe.com/global, 2026-09-23]
- **Connect:** las transferencias cross-border a cuentas conectadas no incluyen AR. Global Payouts sumó cuentas bancarias receptoras en Argentina en 2026, pero eso es solo **para pagarles**, no para que cobren. [fuentes: https://docs.stripe.com/connect/cross-border-payouts y https://docs.stripe.com/changelog/dahlia/2026-03-25/cross-border-payouts-new-countries, 2026-09-23]
- **Conclusión:** **no sirve** para que un comercio argentino cobre en su cuenta.

## 7. Nave (Banco Galicia)

- **Conexión de terceros:** **no hay OAuth**.
  - El comercio pide Client ID, Client Secret y POS ID a integraciones@navenegocios.com.
  - La API corre sobre `api.ranty.io`, con autenticación M2M en `services.apinaranja.com` (infraestructura de Naranja X).
  - El plugin recibe webhooks. **Las devoluciones son manuales desde el dashboard** en la versión del plugin.
  - [fuente: https://wordpress.org/plugins/nave-for-woocommerce/, actualizado 2026-05-27, consultado 2026-09-23]
  - Portal de desarrolladores: https://navenegocios.ar/home/developers (es una SPA; no pude leer el contenido).
- **Costos:**
  - Dinero en cuenta (transferencia/QR): los primeros 3 meses sin comisión (hasta 1.000 UVA/mes), después **0,8% + IVA**.
  - Crédito: CFT de 0% en 1 cuota y de 7,64% en 3 cuotas.
  - Acreditación "al instante".
  - [fuentes: snippets de https://navenegocios.ar/home y https://www.galicia.ar/empresas/tarjetas-y-cuentas/cuenta-comercio/nave, 2026-09-23]
  - Los % de débito y crédito online **no están confirmados**.
- **Tipo:** probablemente **agregador (PSP)**. No confirmado.

## 8. viüMi (Banco Macro)

- **Conexión de terceros:** **no hay OAuth**. El comercio "contacta a viüMi para obtener las claves" (`client_id` y `client_secret`), y la plataforma pide un JWT con `client_credentials` y crea la orden en `POST {base_url}/api/v2/orders`. [fuentes: https://developers.viumi.com.ar/page/checkout/requirements y https://developers.viumi.com.ar/page/checkout/integration, 2026-09-23]
- **Webhook:** no aparece en esas dos páginas. Hay una sección "Estado de la orden" para consultarlo. Ver No confirmado.
- **Costos y acreditación:** no están publicados en https://www.macro.com.ar/empresas/cobros-y-pagos/viumi.
- **Tipo:** no confirmado.

## 9. Ualá Bis

- **Qué es:** Alau Tecnología S.A.U., "Proveedor de Servicios de Pago registrado ante el Banco Central". [fuente: https://www.ualabis.com.ar/preguntas-frecuentes, 2026-09-23]
- **Conexión de terceros:** **no hay OAuth**. El comercio genera sus credenciales en la app (Cobros → Tiendas online → Página web) y las carga en la plataforma. [fuente: https://www.ualabis.com.ar/apicheckout, snippet 2026-09-23]
- **API v2:** `POST /checkout` con `amount` (en centavos, mínimo 2500), `callback_success`, `callback_fail`, **`notification_url`** y `external_reference`. Bearer token vía `/v2/authentication/create`. **La API v1 se depreca el 31/12/2026.** [fuentes: https://developers.ualabis.com.ar/v2/orders/create y https://developers.ualabis.com.ar/, 2026-09-23]
- **Costos:**
  - API checkout: **4,9% + IVA** en crédito, débito y prepaga. [fuente: snippet ualabis.com.ar/apicheckout, 2026-09-23]
  - Link de pago: débito 2,9% + IVA, crédito 4,4% + IVA.
  - QR: 0% los 3 primeros meses (tramo gratuito del BCRA), después 0,8%.
  - Acreditación "en el acto".
  - [fuentes: https://www.ualabis.com.ar/qr y snippets de ualabis.com.ar, 2026-09-23]
  - La cifra del checkout (4,9%) aparece en una sola fuente; ver No confirmado.
- **Tipo:** **agregador**.

## 10. Otros revisados

- **Pago Nube (Tiendanube):** solo funciona **dentro de Tiendanube**. "Por el momento solo está disponible para recibir pagos", y la comisión depende del plan y del plazo (1, 7 o 14 días). [fuente: https://ayuda.tiendanube.com/es_AR/pago-nube-2/cuales-son-las-comisiones-de-pago-nube, 2026-09-23] **Descartado.**
- **BIND PSP (Banco Industrial):** es infraestructura white-label para **fintechs/PSP** (cobros con POS, botón de pago, QR interoperable, transferencias). No es para que un comercio conecte su cuenta. [fuentes: https://bind.com.ar/fintech/bind-psp y https://psp.bind.com.ar/developers, 2026-09-23] **Descartado** para Vereda.
- **Pomelo:** emisión y procesamiento de tarjetas para fintechs. No es adquirencia para comercios. [fuente: https://pomelo.la/blog/adquirencia-ecosistema-pagos, 2026-09-23] **Descartado.**
- **Cobro Express / Rapipago / Pago Fácil:** no encontré una API pública con webhook para comercios chicos. El cobro en efectivo llega vía agregadores: Mobbex y dLocal lo incluyen, y ePagos tiene API de código de barras (https://www.epagos.com.ar/desarrolladores.php). **No confirmado.**
- **MODO:** botón de pago para tiendas online, integrado vía el adquirente o gateway del comercio. [fuente: https://www.modo.com.ar/comercios/tiendas-online, 2026-09-23] Es un medio de pago, no una cuenta de cobro.

---

## Tabla resumen

| Proveedor | Tipo | Conexión cuenta comercio → nodo | Fee plataforma 0 posible | Costo comercio (online) | Acreditación | Alta | Webhook | Devol./contracargos | Encaje Vereda |
|---|---|---|---|---|---|---|---|---|---|
| **Mobbex** | Agregador (Essential) o gateway (números propios) | **Dev Connect (tipo OAuth)**: access token por comercio + api-key de la plataforma | Sí (sin `split`) | Déb 1,9%, créd 2,6% (+IVA) | Déb 2 d.h., créd 10–18 d.h., QR instantáneo | Online, días hábiles | Sí, por checkout (firma no documentada) | API; contracargos a cargo del comercio (T&C Agrupador) | **Alto**: única conexión delegada confirmada |
| **Payway** | Adquirente + gateway | Keys pública y privada del comercio cargadas en el nodo | Sí | 1% plataforma + déb 2%, créd 3% (monotrib. 0% déb.) | Déb 1 d.h., créd 5–18 d.h., QR instantáneo | Adhesión Payway, número de establecimiento | `notifications_url` (detalle no confirmado) | Refund total/parcial por API; contracargo del adquirente al comercio | Medio: sin OAuth, costo bajo |
| **Getnet** | Adquirente | Client ID/Secret vía ejecutivo, cargados en el nodo | Sí | Créd 2% (8 d.h.) a 7,28% (inmediata); déb 1–1,53%; QR 0,8% (+IVA) | Según plazo elegido; inmediata solo con cuenta Santander | Ejecutivo de ventas | Sí (URL + usuario/pass) | Chargeback API existe | Medio-bajo: alta manual |
| **Fiserv / Clover** | Adquirente | Link de pago sin API; Clover Ecommerce API solo en NA | n/a | Aranceles Posnet; link bonificado 12 meses | Déb 48 h, créd 10 d.h. | Ser comercio Posnet/Clover | No confirmado | No confirmado | **Bajo** |
| **dLocal / Go** | Agregador / MoR | API keys por cuenta (Go); "For Platforms" custodia fondos | Go: sí; Platforms: no aplica | Go internacional AR: tarjetas 3,49% (tarifario 2023) | 7 días al saldo + 48 h al banco | Online, 2 pasos KYC | Sí (doc Go) | Refund con fee < USD 10 | Bajo (orientado a cross-border) |
| **Stripe** | — | — | — | — | — | **AR no soportado** | — | — | **Nulo** |
| **Nave (Galicia)** | Probable agregador | Client ID/Secret/POS ID por mail | Sí | Transf./QR 0,8% + IVA (después de 3 meses) | Instantánea | Vía Nave/Galicia | Sí (plugin) | Devol. manual en dashboard | Medio |
| **viüMi (Macro)** | No confirmado | client_id/secret (JWT client_credentials) | Sí | No publicado | No publicado | Contacto viüMi | No confirmado | No confirmado | Bajo-medio |
| **Ualá Bis** | Agregador (PSP BCRA) | Credenciales que genera el comercio en su app | Sí | Checkout API 4,9% + IVA; link déb 2,9%, créd 4,4% (+IVA); QR 0,8% | Instantánea | App Ualá (autoservicio) | **Sí, `notification_url`** | No confirmado | **Alto**: autoservicio + webhook por orden |
| **Pago Nube** | Agregador cerrado | Solo Tiendanube | — | Según plan | 1/7/14 días | — | — | — | Nulo |
| **BIND PSP / Pomelo** | Infraestructura B2B | — | — | — | — | — | — | — | Nulo (son para fintechs) |

## Recomendación para Vereda (inferencia, no dato)

1. **Adaptador genérico "credenciales del comercio".** El comercio pega sus keys o client_id/secret en su nodo, cifradas en reposo. El nodo crea la orden con `external_reference = pedido_id` y `notification_url = nodo/webhooks/<proveedor>`. Sirve igual para Ualá Bis, Payway, Getnet, Nave y viüMi.
2. **Mobbex Dev Connect** es el único flujo "Conectar con…" (tipo OAuth) confirmado.
   - Requiere que **cada operador de nodo** tenga su propia api-key de desarrollador Mobbex. Esto está por confirmar.
3. **Nunca confiar en el webhook solo.** Al recibirlo, el nodo debe re-consultar el estado del pago por API con las credenciales del comercio. Varias docs no documentan firma.
4. **Descartar** Stripe, Pago Nube, BIND, Pomelo y dLocal For Platforms. Todos requieren custodia de fondos o no operan para comercios AR.

---

## No confirmado

- **Mobbex:**
  - Si Dev Connect permite crear checkouts **y** recibir webhooks por comercio sin que la plataforma sea partner aprobado (doc: https://mobbex.dev/dev-connect).
  - Requisitos para obtener una api-key de desarrollador.
  - Existencia de firma o HMAC en los webhooks.
  - Los T&C de Agrupador y de Gateway devolvieron "not found" al abrirlos. La cita sobre contracargos viene de un snippet de búsqueda.
- **Mobbex, costos:** la tabla de acreditación de los T&C (débito 3 d.h., crédito 13 d.h., prepaga 20 d.h.) viene de un snippet y contradice en parte al FAQ (débito 2 d.h., crédito 10–18 d.h.).
- **Payway:**
  - Formato, firma y reintentos de `notifications_url`.
  - Si un tercero puede operar con las keys del comercio sin figurar como agregador.
  - Cláusula de contracargos.
  - https://www.payway.com.ar/planes-precios falló por certificado.
- **Getnet:**
  - Si los aranceles de https://www.getnet.net/ar/aranceles aplican a Get Checkout online. Un comparador [secundaria] cita 2,29% débito y 3,79% crédito a 72 h para online.
  - Detalle de firma del webhook.
  - Si se requiere cuenta Santander para el alta.
- **Fiserv:** si existe una API e-commerce ("Posnet Gateway") con webhooks para comercios AR, y en qué condiciones.
- **dLocal Go:** tarifas y viabilidad para un comercio **argentino** que cobra en ARS a clientes argentinos. El tarifario publicado es de pagos internacionales (abril 2023). Un blog [secundaria] cita 2,99% o 3,49% + IVA.
- **Nave:** aranceles de débito y crédito online; tipo (agregador o adquirente); API de devoluciones.
- **viüMi:** webhooks, costos, acreditación, tipo.
- **Ualá Bis:**
  - El 4,9% + IVA del checkout API sale de un solo snippet.
  - Política de contracargos y devoluciones por API.
  - Requisitos (¿basta CUIL/monotributo?).
- **Cobro Express / Rapipago / Pago Fácil:** APIs públicas con webhook para comercios.
- **Mobbex vs comparadores:** comparapasarelas.com [secundaria] cita 2,09% débito y 3,59% crédito. No coincide con el plan Essential oficial (1,9% y 2,6% + IVA), que es el que se tomó.
