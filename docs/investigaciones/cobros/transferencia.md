# Vereda: pago por transferencia desde el mismo iPhone

Investigación de solo lectura, fecha de consulta: **2026-09-23** (salvo que se indique otra fecha de publicación).
Convención: `[fuente: URL, fecha]`. "consultado" = fecha en que se leyó la página. "pub." = fecha de publicación o vigencia.
Método para universal links: se descargaron los archivos públicos `/.well-known/apple-app-site-association` (AASA). Son los que iOS usa para decidir qué URLs `https://` abren una app. Que una ruta aparezca en el AASA **no** significa que esté documentada ni que acepte parámetros de alias o monto.

---

## 1. ¿Se puede abrir cada app con alias/CVU y monto precargados?

### Resumen por app

| App | Oficial y documentado (alias + monto) | Universal links en el AASA (no documentados) | Conclusión |
|---|---|---|---|
| Mercado Pago | **No existe** para transferir a un alias/CVU. Lo que sí existe es Checkout Pro / Link de pago (preferencia con monto, cobra en la cuenta MP del vendedor) | `www.mercadopago.com.ar`: `/money-transfer*`, `/money-request*`, `/mla/checkout/v2/requestmoney/pay/*`, `/instore*`, `/s/*`, `/open-banking/user-consents/app/debin/accounts/cb*`… `mpago.la` y `mpago.li`: **todas las rutas (`*`)** | Transferencia precargada: no documentada. Link de pago o preferencia con monto: documentado, abre la app MP |
| MODO | **No** para transferencias. El "botón de pago" o SDK de ecommerce es con **tarjeta** y a través de un gateway (Decidir, Getnet, etc.) | `www.modo.com.ar`: `/pago-modo*`, `/pago-ecommerce-modo*`, `/send-modo*`, `/collect-modo*`, `/qr-personal-modo*` | Precarga de alias o monto: no documentada. Ecommerce: solo tarjetas vía gateway |
| Ualá | No se encontró | `www.uala.com.ar`: solo `/email_validation` | No existe (públicamente) |
| Naranja X | No se encontró | `app.naranjax.com`: **todas las rutas (`/*`)** para `com.tarjetanaranja.ncuenta` | Hay dominio de universal links, pero las rutas y parámetros son desconocidos |
| Brubank | No se encontró | `brubank.com`: `/app/*` | Rutas y parámetros desconocidos |
| Personal Pay | No se encontró | No hay AASA (404) | No existe (públicamente) |
| Cuenta DNI | No se encontró | No se pudo obtener el AASA (el dominio no respondió) | No confirmado |
| Galicia | No se encontró | 404 en `galicia.ar` y en `onlinebanking.bancogalicia.com.ar` | No existe (públicamente) |
| Santander | No se encontró | Sin respuesta | No confirmado |
| BBVA | No se encontró | `go.bbva.com.ar`: solo login, beneficios y tarjetas | No existe para transferencias |
| Macro | No se encontró | `www.macro.com.ar`: `/consent/callback*`, `/individuos/welcome*` | No existe para transferencias. El `consent/callback` sugiere un flujo de consentimiento OAuth (pull), pero no está confirmado |
| BNA / BNA+ | No se encontró | No hay AASA (redirige a una página de error) | No existe (públicamente) |

Fuentes del AASA (todas consultadas el 2026-09-23):
- Mercado Pago [fuente: https://www.mercadopago.com.ar/.well-known/apple-app-site-association, consultado 2026-09-23]
- mpago.la [fuente: https://mpago.la/.well-known/apple-app-site-association, consultado 2026-09-23]
- mpago.li [fuente: https://mpago.li/.well-known/apple-app-site-association, consultado 2026-09-23]
- MODO [fuente: https://www.modo.com.ar/.well-known/apple-app-site-association, consultado 2026-09-23]
- Ualá [fuente: https://www.uala.com.ar/.well-known/apple-app-site-association, consultado 2026-09-23]
- Naranja X [fuente: https://app.naranjax.com/.well-known/apple-app-site-association, consultado 2026-09-23]
- Brubank [fuente: https://brubank.com/.well-known/apple-app-site-association, consultado 2026-09-23]
- BBVA [fuente: https://go.bbva.com.ar/apple-app-site-association, consultado 2026-09-23]
- Macro [fuente: https://www.macro.com.ar/.well-known/apple-app-site-association, consultado 2026-09-23]

### Mercado Pago, en detalle
- Checkout Pro en Argentina acepta tarjetas de crédito y débito, Rapipago, Pago Fácil, dinero en cuenta MP y Cuotas sin Tarjeta. **No incluye transferencia bancaria** [fuente: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/overview, consultado 2026-09-23].
- La tabla oficial de medios de pago de Argentina tampoco incluye `bank_transfer` ni DEBIN: tiene `account_money`, `credit_card`, `debit_card`, `prepaid_card`, `ticket` y `digital_currency` [fuente: https://www.mercadopago.com.ar/developers/en/docs/sales-processing/payment-methods, consultado 2026-09-23].
- En iOS, la guía oficial abre el `init_point` en `SFSafariViewController` y vuelve a la app con `back_urls` (deep link). No documenta el salto a la app de MP [fuente: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/mobile-integration/swift, consultado 2026-09-23]. Abrir `mpago.la/...` con `UIApplication.open` sí debería abrir la app, porque ese dominio reclama `*` en su AASA. Es una inferencia sin probar.
- OAuth permite operar a nombre del vendedor, por ejemplo crear preferencias con su access token [fuente: https://www.mercadopago.com.ar/developers/es/docs/security/oauth/introduction, consultado 2026-09-23]. La plata cae en la cuenta MP del comercio y **Vereda no la toca**. Pero es un cobro MP con comisión MP, no una transferencia al alias.
- Link de pago (manual, desde la app del vendedor): el comprador paga con tarjeta, débito, efectivo o dinero en MP [fuente: https://www.mercadopago.com.ar/herramientas-para-vender/link-de-pago, consultado 2026-09-23].
- "Pedir dinero" (P2P, link por WhatsApp): quien no tiene MP "puede transferir con cualquier medio de pago". Según la nota, la función apunta a gastos personales, no a cobros comerciales [fuente: https://www.ambito.com/informacion-general/mercado-pago-como-juntar-dinero-mis-contactos-whatsapp-n5783473, pub. 2023-08-03].
- No se encontró ningún esquema `mercadopago://` documentado para transferir.

### MODO, en detalle
- Ecommerce: el comprador "paga desde la app de su banco con tarjeta de débito o crédito". El comercio necesita cuenta en Decidir, Posnet Gateway, Getnet o Line Payments, más el plugin o SDK [fuente: https://www.modo.com.ar/blog/como-aceptar-modo-en-tu-tienda-online, consultado 2026-09-23].
- Desde el celular "se abrirá la aplicación para realizar el pago" [fuente: https://ayuda.tiendanube.com/es_ES/preguntas-frecuentes-pago-nube/cobrar-con-qr-de-modo-o-app-bancaria-a-traves-de-pago-nube, actualizado 2026-04-30].
- Documentación del SDK: https://merchants.modo.com.ar/docs. Es una SPA; no se pudo leer el formato del deeplink.
- "Pedir" P2P: crear pedido → monto → cuenta destino → "Compartir link" [fuente: resultado de búsqueda sobre https://ayuda.modo.com.ar/support/solutions/articles/66000085109, consultado 2026-09-23; la URL hoy redirige a https://modo.com.ar/ayuda/preguntas-frecuentes/].

---

## 2. Marco BCRA

### Transferencias 3.0 y Pago con Transferencia (PCT)
- Com. "A" 7153 aprobó Transferencias 3.0, vigente desde el 7/12/2020. Com. "A" 7175 publicó los textos ordenados. La fase 2 venció el 29/11/2021. Com. "A" 7462 (2022) creó el Registro de billeteras digitales interoperables y Com. "A" 7463 trata el fraude [fuente: https://www.bcra.gob.ar/archivos/Pdfs/Medios_pago/T3.0-PCT-Reglamento-operativo-Integracion-participantes.pdf, consultado 2026-09-23].
- QR interoperable completo: "pay by reading any QR code with any electronic wallet or banking app" [fuente: https://www.bcra.gob.ar/en/news/3-0-transfers-the-implementation-of-the-interoperable-qr-code-payment-system-is-complete/, pub. 2021-11-29].
- **Quién puede generar un QR PCT.** Un *aceptador* tiene que ser PSP, entidad financiera o empresa supervisada por el BCRA, y además **agente de recaudación de impuestos** (punto 4.1.3) [fuente: mismo PDF del reglamento de integración, consultado 2026-09-23]. **Vereda no puede ser aceptador** sin volverse una entidad regulada.
- El texto ordenado vigente de "SNP – Transferencias – Normas Complementarias" es del 08/09/2026, con Com. "A" 8477 como última comunicación incorporada [fuente: https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-snp-tr-nc.pdf, consultado 2026-09-23]. Puntos clave:
  - 3.2.1.2: "El PCT tiene dos variantes… iniciado por el aceptador y solicitud de pago, que podrá ser activa o pasiva".
  - **3.2.4.2, solicitud de pago activa (es el Request-to-Pay argentino):** "son emitidas por un potencial cliente receptor de los fondos –el comercio– hacia un identificador de una cuenta específica, tal como un alias o una CBU/CVU. Al aceptar esta solicitud… el consumidor remite una instrucción de pago… con la información de monto y cuenta de destino". "Las entidades financieras y los PSPCP deberán estar en condiciones de poner a consideración de sus clientes las solicitudes de pago activas que reciban" (Com. "A" 8399, vigente desde 13/02/2026).
  - 3.2.4.3, solicitud pasiva: el QR del aceptador según los estándares BCRA y CIMPRA.
  - 3.2.4.5: quien lee QR debe leer cualquier QR de solicitud pasiva "sin discriminación".
  - 4.2: la IEP (Interfaz Estandarizada de Pagos) debe definir la "Solicitud de pago con transferencia, activa, incluyendo interacción con código QR" y adoptar ISO 20022 de forma gradual.
  - 2.10 (Com. "A" 8477, vigente desde 09/09/2026): "Las solicitudes de pago… podrán ser utilizadas para transferencias inmediatas sin fines comerciales".
  - 3.4: transferencias pull (pedidos de fondos) con consentimiento **OAuth2** explícito. En la variante "entre cuentas de un mismo titular" también se admite consentimiento tácito.
  - 1.5.x: las interfaces al cliente **no deben usar los términos DEBIN/CREDIN** para las transferencias pull o push.
  - 1.5.5.11: un administrador no puede habilitar QR de un aceptador si no constató que lo leen **todas** las billeteras interoperables registradas.
- Com. "A" 8399 [fuente: https://www.bcra.gob.ar/archivos/Pdfs/comytexord/A8399.pdf, pub. 2026-02-12]. Resumen oficial [fuente: https://www.argentina.gob.ar/normativa/nacional/norma-424124, consultado 2026-09-23].
- Com. "A" 8477 [fuente: https://www.bcra.gob.ar/archivos/Pdfs/comytexord/A8477.pdf, pub. 2026-09-08].

### "Cobro con transferencia" (reemplaza al DEBIN recurrente)
- Com. "A" 8406 aprueba el "cobro con transferencia" como **única modalidad habilitada para cobros recurrentes**. Rige desde el 31/08/26 para préstamos; para otros cobros, el BCRA todavía no comunicó la fecha. Solo lo pueden contratar **personas jurídicas**, a través de aceptadores habilitados ("no pudiendo ser… ofrecido por intermediarios"), con consentimiento OAuth2 [fuente: https://www.bcra.gob.ar/archivos/Pdfs/comytexord/A8406.pdf, pub. 2026-03-02].

### ¿El QR interoperable funciona como link en el mismo teléfono?
- La norma habla de QR y de solicitudes activas "incluyendo interacción con código QR". **No se encontró** ninguna norma que defina un link universal `https://` interoperable que cualquier billetera abra.
- En iOS no existe un selector de billetera para universal links: cada dominio apunta a las apps que declara en su AASA. Apple recomienda universal links en lugar de esquemas propios ("Use universal links instead of custom URL schemes to define links that are uniquely associated with your website") [fuente: https://developer.apple.com/documentation/xcode/defining-a-custom-url-scheme-for-your-app, consultado 2026-09-23].
- `canOpenURL` exige declarar los esquemas en `LSApplicationQueriesSchemes`. El máximo es 50 entradas (iOS 15+) y **25 para apps linkeadas con iOS 27+** [fuente: https://developer.apple.com/documentation/uikit/uiapplication/canopenurl(_:), consultado 2026-09-23].
- Con iOS 15+ se puede mantener presionado un QR dentro de una foto o captura. Una fuente secundaria afirma que en QR de pago aparecen accesos a apps bancarias [fuente: https://www.qrcodechimp.com/scan-qr-code-from-picture/, consultado 2026-09-23]. **No confirmado para QR EMVCo argentinos.**

---

## 3. Cómo vuelve el comprobante a Vereda

- **Share Extension:** `NSExtensionActivationRule` define qué tipos acepta. Las claves oficiales incluyen `SupportsImageWithMaxCount`, `SupportsFileWithMaxCount` (para PDF), `SupportsText`, `SupportsWebURLWithMaxCount` y `SupportsAttachmentsWithMaxCount` [fuente: https://developer.apple.com/documentation/bundleresources/information-property-list/nsextension/nsextensionattributes/nsextensionactivationrule, consultado 2026-09-23]. Conviene declarar imagen, archivo y texto, porque cada app comparte algo distinto.
- **Formato que comparte cada app:** hay tutoriales de MP que muestran cómo compartir el comprobante [fuente: https://www.youtube.com/watch?v=T-pjB9JCr3Y, consultado 2026-09-23] y hay comprobantes MP en PDF circulando [fuente: https://www.scribd.com/document/628368179/COMPROBANTE-TRANSFERENCIA-MERCADO-PAGO, consultado 2026-09-23]. **Qué formato comparte exactamente cada app (PDF, imagen o texto) queda NO confirmado** y hay que probarlo en un dispositivo.
- **OCR on-device:** `VNRecognizeTextRequest` está disponible desde iOS 13 y admite fijar idiomas con `recognitionLanguages` [fuente: https://developer.apple.com/documentation/vision/vnrecognizetextrequest, consultado 2026-09-23]. `RecognizeDocumentsRequest` (iOS 26+) extrae la estructura de documentos, "like receipts", incluidas tablas [fuente: https://developer.apple.com/documentation/vision/recognizedocumentsrequest, consultado 2026-09-23].
- **ID Coelsa:** "código alfanumérico de 22 caracteres que se genera automáticamente al realizar una transferencia" y sirve para rastrearla entre entidades [fuente: https://help.lemon.me/es/articles/6868460-que-es-coelsa-y-por-que-es-importante-el-id-coelsa, pub. 2023-04-09]. MP tiene una página de ayuda al respecto (devolvió 403 al consultarla) [fuente: https://www.mercadopago.com.ar/ayuda/25527, consultado 2026-09-23]. Santander explica cómo obtenerlo (timeout al consultarla) [fuente: https://ayuda.santander.com.ar/AXP6FW83JO-1/article/W79RE9AURN-como-conseguir-id-coelsa-caso-necesitarlo/, consultado 2026-09-23].
- La norma exige un "identificador único estandarizado" por transferencia inmediata, válido entre esquemas (punto 2.7) [fuente: https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-snp-tr-nc.pdf, consultado 2026-09-23].
- **Campos que devuelve una consulta por ID Coelsa** (ejemplo de API bancaria): id de 22 caracteres; comprador con titular, CUIT, banco, alias, CBU y endpoint (p. ej. "MP"). Esta API requiere ser cliente del banco y usar mTLS + VPN + token [fuente: https://docs.bdcconecta.com/Transferencias/coelsa_aditional_data, consultado 2026-09-23].
- **Campos típicos de un comprobante** (monto, fecha y hora, nombre y CUIT/CUIL del origen, CBU/CVU o alias de destino, entidad, número de operación, ID Coelsa): se infieren de las fuentes anteriores. **No hay un formato normado** y cada app varía, así que queda **NO confirmado** app por app.

---

## 4. Cómo confirma el comercio que le llegó la plata

- **Webhooks de MP:** los tópicos oficiales son `payment`, `orders`, `subscription_*`, `mp-connect`, `wallet_connect`, chargebacks, claims, Point, etc. **No hay un tópico de "transferencia recibida al CVU"** [fuente: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/additional-content/notifications/webhooks, consultado 2026-09-23].
- **Práctica no oficial:** un repo público afirma que las transferencias al alias/CVU "generalmente sí generan un 'pago' (`payment_type_id: account_money`) y disparan este mismo webhook". También recomienda verificarlo con una transferencia real y deja `/v1/payments/search` como respaldo [fuente: https://github.com/7b4wg2pgzp-eng/pagos, consultado 2026-09-23]. **NO confirmado oficialmente.**
- **Reporte "Todas las transacciones" de MP** (API, OAuth del comercio): incluye `PAYMENT_METHOD_TYPE = bank_transfer` y `PAYER_NAME` / `PAYER_ID_TYPE`, que están disponibles "cuando se reciban pagos con código QR, transferencias". La frecuencia programable es `daily`, `weekly` o `monthly`, así que **no es tiempo real** [fuente: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/additional-content/reports/account-money/report-fields, consultado 2026-09-23] [fuente: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/additional-content/reports/account-money/api, consultado 2026-09-23].
- **Leer notificaciones de otras apps:**
  - **Android sí puede.** `NotificationListenerService` recibe las notificaciones que publica cualquier app, con el permiso `BIND_NOTIFICATION_LISTENER_SERVICE` y activación manual del usuario en Ajustes [fuente: https://developer.android.com/reference/android/service/notification/NotificationListenerService, consultado 2026-09-23].
  - **iOS no.** La API solo devuelve "your app's delivered notifications" [fuente: https://developer.apple.com/documentation/usernotifications/unusernotificationcenter/getdeliverednotifications(completionhandler:), consultado 2026-09-23]. No existe un equivalente público a NotificationListener. Esto se infiere de la ausencia de API; Apple no lo prohíbe con una frase explícita.
- **Ualá Bis API Checkout:** tiene webhooks por orden (POST, reintentos hasta 3 veces). No encontré notificación de dinero entrante al CVU fuera de las órdenes [fuente: https://developers.ualabis.com.ar/v2/orders/create/webhook, consultado 2026-09-23].
- **Cuenta DNI Comercios:** app de cobro con QR y transferencia, arancel del 0,8%. No se encontró API pública [fuente: https://www.bancoprovincia.com.ar/cuentadni/contenidos/cdniComercios, consultado 2026-09-23].
- **Open banking o finanzas abiertas:** el Decreto 353/2025 crea el Sistema de Finanzas Abiertas con el BCRA como autoridad. "A 2026, el BCRA todavía no publicó los estándares técnicos… ni el cronograma" [fuente: https://www.fiskil.com/es/open-finance-tracker/argentina, consultado 2026-09-23]. Es una fuente secundaria. **No hay APIs abiertas de cuentas utilizables hoy.**
- **BaaS con CVU y webhooks** (ejemplo BDC Conecta): existen APIs con cuentas y subcuentas CVU, webhooks, movimientos y consulta por ID Coelsa. Requieren ser cliente institucional (mTLS + VPN) [fuente: https://docs.bdcconecta.com/Transferencias/coelsa_aditional_data, consultado 2026-09-23]. Sería el comercio, no Vereda, quien tendría que abrir esa cuenta.
- **Mails de aviso de acreditación:** no se investigaron a fondo, así que queda **NO confirmado** qué billeteras mandan mail por cada transferencia recibida.

---

## Qué funciona hoy en iOS de verdad

1. **Mostrar y copiar alias/CVU y monto** (`UIPasteboard`), más un botón que abra la app elegida por su universal link o home. El comprador pega los datos a mano. Funciona con todas las apps y no depende de nadie.
2. **Si el comercio usa Mercado Pago:** Vereda, con OAuth del comercio, crea una preferencia de Checkout Pro con el monto. El link `init_point` o `mpago.la` abre MP en el mismo teléfono y el webhook `payment` confirma el pago en tiempo real. La plata va a la cuenta MP del comercio y Vereda no la toca. Pero **no es transferencia** (dinero en cuenta o tarjeta) y MP cobra comisión.
3. **Share Extension** que acepte imagen, PDF y texto, más **OCR on-device con Vision** para extraer monto, fecha, destino, número de operación e ID Coelsa del comprobante. Como alternativa: una captura de pantalla importada desde la galería.
4. **Confirmación del comercio con MP:** webhook `payment` o polling de `/v1/payments/search` con OAuth. Para transferencias al CVU no está garantizado por la documentación; hay que probarlo con una transferencia real. Como respaldo, el reporte diario "Todas las transacciones".
5. **Android (comercio):** `NotificationListenerService` puede leer los avisos "Recibiste $X" de cualquier billetera. En iOS es imposible.

## No confirmado

- Parámetros de `mercadopago.com.ar/money-transfer*` y `/money-request*`: las rutas existen en el AASA, pero no se sabe si aceptan alias o monto por URL.
- Rutas y parámetros de `modo.com.ar/send-modo*`, `/collect-modo*` y `/pago-modo*`, de `app.naranjax.com/*` y de `brubank.com/app/*`.
- Si alguna billetera ya muestra al usuario las **solicitudes de pago activas** (3.2.4.2) y si hay un formato de link o QR para emitirlas desde fuera de un aceptador. La norma dice que deben estar "en condiciones", pero no hay evidencia de implementación visible.
- Cómo se ve el formato EMVCo del QR argentino como texto, y si alguna app lo abre desde un link o desde una foto en el mismo teléfono.
- Qué comparte cada app al tocar "Compartir comprobante" (PDF, imagen o texto) y qué campos trae cada una.
- Si las transferencias entrantes al CVU de MP disparan el webhook `payment` (lo afirma solo un repo público).
- Que Cuenta DNI, Santander y BNA+ no tengan universal links: sus dominios no respondieron o dieron error, lo que no prueba que no existan.
- Comisiones de Link de pago o Checkout Pro de MP (la página de ayuda devolvió 403 o se renderiza con JS).
- Mails de acreditación por billetera.
