# Mercado Pago (Argentina): verificación en docs oficiales

Consulta: 2026-09-25. Fuentes públicas solamente (developers de MP, Centro de ayuda de MP, TyC publicados, registro del BCRA). No se crearon cuentas ni se hicieron pagos. Construye sobre `docs/investigaciones/cobros.md` y `cobros/pasarelas-1.md` §1 (2026-09-23): corrige y profundiza; no repite lo que ya estaba bien.

Convención: **(NC)** = no confirmado en fuente oficial. Las citas textuales van entre comillas; muchas páginas de developers sirven el markdown en inglés aunque la URL sea `/es/`, así que algunas citas quedan en inglés tal cual las devuelve el sitio.

Nota técnica útil para quien siga: casi todas las páginas de `developers` tienen una versión `.md` (agregar `.md` a la URL) y las páginas de ayuda de MP traen el artículo embebido en el HTML (hay que decodificar `<`). Con `curl` y un user-agent de navegador se leen; con fetch "pelado" dan 403/404.

---

## 1. Cobrar en nombre del comercio con fee 0 (OAuth, endpoints, scopes, tokens, qué registra el operador)

### 1.1 El modelo: token del vendedor + preferencia sin `marketplace_fee`

- El producto oficial para cobrar en nombre de terceros es OAuth con *authorization code*: "Authorization code: a flow based on redirection and should be used when credentials are to be used to access a resource on behalf of others". [MP · OAuth introducción](https://www.mercadopago.com.ar/developers/es/docs/security/oauth/introduction), 2026-09-25.
- El dinero va a la cuenta del vendedor porque el pago se crea con **su** `access_token`: `collector_id` "Es el usuario quien recibe el dinero. Por ejemplo - Un usuario (payer) compra un celular a través del marketplace. El identificador de la tienda/vendedor para recibir el pago es el collector_id." [MP · Referencia Obtener pago](https://www.mercadopago.com.ar/developers/es/reference/online-payments/checkout-api-payments/get-payment/get), 2026-09-25.
- Split 1:1 (marketplace): "To perform the integration, you will need to follow the usual integration flow of the chosen checkout, necessarily using an access token for each seller, obtained through OAuth" y "use the `public_key` of your integrator account in the frontend and insert the seller's `access_token` (obtained in step 1) in the backend or in the request header". [MP · Integrar checkout en Split 1:1](https://www.mercadopago.com.ar/developers/es/docs/split-payments/split-1-1/integration-configuration/integrate-marketplace), 2026-09-25.

### 1.2 Fee 0: confirmado, por omisión y también explícito

Esto estaba **(NC)** en `pasarelas-1.md` §1.2. Ahora hay texto oficial:

- Referencia de `POST /checkout/preferences`, campo `marketplace_fee`: "Marketplace's fee charged by application owner. It is a fixed amount and **its default value is 0 in local currency**. This property can only be sent if a valid marketplace has been defined as well, otherwise the request will fail." [MP · Referencia Crear preferencia](https://www.mercadopago.com.ar/developers/es/reference/online-payments/checkout-pro-preferences/create-preference/post), 2026-09-25.
- Campo `marketplace`: "Origin of the payment. This is an alphanumeric field whose **default value is NONE**. If the collector has their own marketplace, this is where the credentials to identify it are sent. As the marketplace is associated to the Application ID, the marketplace credentials must correspond to the credentials used to create the preference. Using the wrong credentials will result in an error." [misma referencia]
- Los ejemplos de request oficiales (PHP, Node, curl) de esa misma referencia mandan `"marketplace_fee": 0` explícito, así que el 0 explícito también está avalado por la doc. [misma referencia]
- Doc de marketplace (Checkout Pro): "The Mercado Pago commission is deducted from the amount received by the seller. In other words, the Mercado Pago commission is deducted first and the Marketplace commission is deducted from the remaining amount." [MP · Cómo integrar checkout en marketplace](https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-preferences/how-tos/integrate-marketplace), 2026-09-25.

**Cuál de las dos usar (recomendación):** omitir `marketplace_fee` y `marketplace` (queda `NONE`). Así la preferencia es un cobro normal del vendedor, creado con su token; el 100 % menos la comisión de MP se acredita en la cuenta del vendedor y el operador del nodo no aparece en el flujo de fondos. Mandar `marketplace_fee: 0` obliga a mandar además un `marketplace` válido asociado al App ID del operador; funciona, pero no aporta nada y ata el pago al "marketplace" del operador.

- `sponsor_id`: "Este campo está deprecado y ya no se usa." [MP · Referencia Obtener pago](https://www.mercadopago.com.ar/developers/es/reference/online-payments/checkout-api-payments/get-payment/get), 2026-09-25.
- `integrator_id`: es del programa de partners (<dev>program), opcional: "Unique number that identifies you as a member of the <dev>program automatically generated after your first successful certification"; la certificación es "100% free and online" y da "extra benefits". No es un requisito para operar. [MP · Certificaciones](https://www.mercadopago.com.ar/developers/es/docs/checkout-api-payments/additional-content/certifications), 2026-09-25.

### 1.3 OAuth: flujo, endpoints, scopes, vida de los tokens

**URL de autorización** (el comercio la abre en su navegador y se loguea en MP):

```
https://auth.mercadopago.com/authorization?client_id=APP_ID&response_type=code&platform_id=mp&state=RANDOM_ID&redirect_uri=https://…
```

- `state`: "an identifier that is unique for each attempt and does not include sensitive information". `redirect_uri`: "Add the reported URL in the 'Redirect URLs' field of your application. Make sure that the redirect_uri is a static URL". Parámetros extra van en `state`, no en la `redirect_uri`. [MP · Obtener Access Token](https://www.mercadopago.com.ar/developers/es/docs/security/oauth/creation), 2026-09-25.
- Con PKCE (opcional, recomendado): se agregan `code_challenge` y `code_challenge_method` (`S256` o `Plain`) a la URL; `code_verifier` de 43 a 128 caracteres. Se habilita en "Application details → Edit → enable the use of the authorization code flow with PKCE". [misma fuente]

**Canje del código:** `POST https://api.mercadopago.com/oauth/token` con `client_id`, `client_secret`, `code`, `grant_type=authorization_code`, `redirect_uri` (y `code_verifier` si hay PKCE). "`redirect_uri` … Required only when grant_type=authorization_code." `test_token: true` genera credenciales de sandbox. [MP · Referencia POST /oauth/token](https://www.mercadopago.com.ar/developers/es/reference/authentication/oauth/_oauth_token/post), 2026-09-25.

**Respuesta** (ejemplo oficial):

```json
{ "access_token": "APP_USR-…", "token_type": "bearer", "expires_in": 15552000,
  "scope": "read write offline_access", "user_id": 241983636,
  "refresh_token": "TG-…", "public_key": "APP_USR-…", "live_mode": true }
```

- `expires_in`: "Fixed access_token expiration time expressed in seconds. By default, the expiration time is 180 days (15552000 seconds)." `user_id`: "unique number that identifies the Mercado Pago seller". `scope`: "By default, the scopes associated with the token are the ones determined when creating the original token and configuring the application." [misma referencia]

**Vigencias:**

| Cosa | Vida | Fuente |
|---|---|---|
| `authorization_code` | "duration of 10 minutes and single-use" | [OAuth introducción](https://www.mercadopago.com.ar/developers/es/docs/security/oauth/introduction) |
| `access_token` (authorization code) | "valid for 180 days (6 months)" | [Obtener Access Token](https://www.mercadopago.com.ar/developers/es/docs/security/oauth/creation) |
| `refresh_token` | "duration of 6 months and can be reused" | [OAuth introducción](https://www.mercadopago.com.ar/developers/es/docs/security/oauth/introduction) |
| `access_token` (client_credentials) | "valid for 6 hours" (solo recursos propios de la app) | [Obtener Access Token](https://www.mercadopago.com.ar/developers/es/docs/security/oauth/creation) |

**Renovación:** `POST /oauth/token` con `grant_type=refresh_token`, `client_id`, `client_secret`, `refresh_token`. Condición: "This flow can only be used if the application return the `scope` parameter indicating the value `offline_access` and the vendor has previously authorized this action". **Rotación confirmada en doc oficial** (antes era NC de un blog): "every time you refresh the `access_token`, the `refresh_token` will also be refreshed, so you will need to store it again." Y "The Access Token received through the endpoint is valid for 180 days, after which the entire authorization flow must be reconfigured." [MP · Renovar Access Token](https://www.mercadopago.com.ar/developers/es/docs/security/oauth/renewal), 2026-09-25.

Lectura práctica: renovar antes de los 180 días (por ejemplo cada 150) y guardar el nuevo par de forma atómica; si se vence el access token sin haber refrescado, hay que pedirle al comercio que autorice de nuevo.

**Invalidación:** expiración; cambio de contraseña del vendedor ("the seller can revoke all your credentials, including associated tokens"); revocación de la autorización; limpieza de credenciales por fraude; limpieza de sesión; borrado de la aplicación. "You can receive webhook notifications every time a seller authorizes or deauthorizes your application" (tópico `mp-connect`). [MP · Gestionar Access Token](https://www.mercadopago.com.ar/developers/es/docs/security/oauth/management), 2026-09-25.

**Buenas prácticas oficiales:** mandar todo en el body (no query params), no agregar headers ni params de más, usar `state`, `redirect_uri` estática. [MP · Buenas prácticas OAuth](https://www.mercadopago.com.ar/developers/es/docs/security/oauth/best-practices), 2026-09-25.

### 1.4 Qué registra el operador del nodo ("Tus integraciones")

Cada operador crea **una aplicación** en su propia cuenta MP (persona física alcanza; el panel pide loguearse con una cuenta MP). Pasos oficiales del panel:

1. Ingresar a Mercado Pago Developers con la cuenta MP → "Create in the integration panel" (o "Your integrations → Create application").
2. "Choose a solution to integrate": Checkout Pro (o Checkout API, Point, QR, o plataforma de e-commerce).
3. Nombre de la aplicación; aceptar Privacidad y TyC → "Create application". [MP · Panel del desarrollador](https://www.mercadopago.com.ar/developers/es/docs/your-integrations/dashboard), 2026-09-25.
4. En "Detalles de aplicación → Editar":
   - "Payment Solution to be Integrated": Online payments → producto → "Optionally, you can select the integration model(s)" (acá aparece vendedor / marketplace).
   - "Redirect URL: URL (in https) where you want to receive the authorization code when your integration is set up as a marketplace or performed through the flow Authorization code by OAuth. Make sure that is a static URL."
   - PKCE: casilla para exigir `code_challenge`.
   - "Application permissions: Options for accessing your application, including **read**, **offline access** and **write**. By default, your application is created with all permissions enabled". [MP · Detalles de aplicación](https://www.mercadopago.com.ar/developers/es/docs/your-integrations/application-details), 2026-09-25.
5. Activar credenciales de producción de la app: "Industry" + "Website (required)" + TyC + reCAPTCHA. Ahí aparecen Public Key/Access Token y **Client ID/Client Secret**. [MP · Credenciales](https://www.mercadopago.com.ar/developers/es/docs/your-integrations/credentials), 2026-09-25.
6. Webhooks → Configurar notificaciones → URL prod y test → Guardar: genera la clave secreta de la app (ver §3).

**¿Aprobación, certificación o KYC del operador?**
- No hay un paso de aprobación de MP para crear la app ni para usar OAuth: la doc de requisitos de Split 1:1 lista solo "Mercado Pago Seller Account … KYC 6 level", tener la app de MP instalada, OAuth, integración con Checkout Pro/API, credenciales y cuentas de prueba. "The 1:N model is available only to sellers with an advised portfolio who are in contact with the Mercado Pago commercial team." [MP · Requisitos Split 1:1](https://www.mercadopago.com.ar/developers/es/docs/split-payments/split-1-1/prerequisites), 2026-09-25.
- El "KYC 6" figura como requisito de la **cuenta vendedora** para Split. Qué es exactamente "nivel 6" no aparece en la ayuda pública **(NC)**. Con fee 0 y sin `marketplace`, la preferencia es un cobro común del vendedor y no está claro que aplique este requisito **(NC)**.
- La "medición de calidad" de la integración es un puntaje mensual con recomendaciones, no una puerta: "you will receive a score indicating how secure and aligned your application's configuration is". [Detalles de aplicación](https://www.mercadopago.com.ar/developers/es/docs/your-integrations/application-details)
- Lo que sí exige MP al operador es la **URL de sitio** para activar credenciales de producción (campo obligatorio). Para un nodo autoalojado, la URL pública del nodo sirve.

### 1.5 Camino B (sin app del operador): el comercio pega su propio token

Sigue vigente y documentado: "Share credentials … up to a maximum of 10 times", y "Use OAuth to manage third-party credentials" como recomendación de seguridad. [Credenciales](https://www.mercadopago.com.ar/developers/es/docs/your-integrations/credentials). Con el token propio del comercio, las notificaciones y la firma son las de **la app del comercio** (ver §3.5).

### 1.6 Detalle relevante de Split 1:1

"Keep in mind that the Split Payments 1:1 solution allows for payments using available balance between Mercado Pago accounts. Transfers from external financial institutions are not permitted." [Integrar checkout en Split 1:1](https://www.mercadopago.com.ar/developers/es/docs/split-payments/split-1-1/integration-configuration/integrate-marketplace). Otra razón para **no** declarar `marketplace` cuando el fee es 0: el cobro común del vendedor no tiene esa restricción.

---

## 2. Alta del comercio, KYC, contracargos, devoluciones por API

### 2.1 Alta

- Abrir cuenta es gratis y arranca con el documento: "Para empezar, ingresá un DNI o un CUIT. El documento determinará quién será titular de la cuenta, podés ser vos o tu negocio." [MP · Registro](https://www.mercadopago.com.ar/hub/registration/landing), 2026-09-25.
- Los TyC dicen que MP "es Sujeto Obligado ante la Unidad de Información Financiera" y que "se reserva el derecho de solicitar comprobantes y/o información adicional a efectos de corroborar la veracidad de la información entregada". [MP · Términos y condiciones](https://www.mercadopago.com.ar/ayuda/terminos-y-condiciones_299), última modificación 17/07/2026, consultado 2026-09-25.
- Tiempo de alta y pasos de validación de identidad (selfie, DNI): no hay página pública legible con el detalle **(NC)**. Para el comercio que ya tiene cuenta (la mayoría), el alta en Vereda es: tocar "Conectar", loguearse en MP, aceptar permisos. Nada más.
- Requisito extra si el comercio quiere usar el camino B (token propio): activar credenciales de producción con rubro y **URL de sitio** (obligatoria). [Credenciales](https://www.mercadopago.com.ar/developers/es/docs/your-integrations/credentials)

### 2.2 Devoluciones por API

- Endpoint: `POST https://api.mercadopago.com/v1/payments/{id}/refunds`. "Crear reembolsos parciales/totales para un pago específico. Si el campo de suma ha sido completado, creará un reembolso parcial, en caso contrario, creará un reembolso total." Body: `amount` — "Monto de reembolso. Si esta propiedad (monto) es removida del body, creará un reembolso total." [MP · Referencia Crear reembolso](https://www.mercadopago.com.ar/developers/es/reference/online-payments/checkout-api-payments/create-refund/post), 2026-09-25.
- Header `X-Idempotency-Key`: marcado **required** en la referencia; error `4292 Header-X-Idempotency-Key-can't-be-null`. Descripción: "This feature allows you to safely retry requests without the risk of accidentally performing the same action more than once … We suggest using a UUID". [misma referencia]. Es obligatorio desde 2023. [MP · Noticia idempotencia](https://www.mercadopago.com.ar/developers/en/news/2023/01/04/Idempotency-key-usage-will-be-mandatory)
- Reglas: "Refunds can be issued within **180 days** after the payment approval"; "It is necessary to have sufficient balance available in your account to perform the refund; otherwise, the transaction will be rejected"; tarjeta de crédito → al resumen, otros medios → a la cuenta del pagador. Cancelación solo con `pending` o `in_process`; "Payments automatically expire after 30 days without confirmation". [MP · Devoluciones y cancelaciones (Checkout Pro)](https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-preferences/additional-settings/refunds-and-cancellations), 2026-09-25.
- Errores útiles de la referencia: `3024` (la transacción no admite parcial), `4293` (estado inválido para reembolsar), `4296` (intentos múltiples sobre el mismo cargo). [Referencia Crear reembolso]
- Estados del reembolso (`status`): `approved`, `in_process`, … [misma referencia]
- Se hace con el **token del vendedor** (el mismo con el que se creó el pago) y sale del saldo del vendedor. Con fee 0 el operador no pone nada; si el vendedor no tiene saldo, MP rechaza la devolución.

### 2.3 Contracargos: quién absorbe

- Mecánica: "During the chargeback resolution period, the disputed amount remains on hold in the seller's account until the process is completed." [MP · Contracargos](https://www.mercadopago.com.ar/developers/es/docs/checkout-api-orders/payment-management/chargebacks/introduction), 2026-09-25. Aviso por webhook `topic_chargebacks_wh` ("Opening of chargebacks, status changes, and modifications related to the release of funds") y consulta `GET /v1/chargebacks/[ID]`. [MP · Webhooks](https://www.mercadopago.com.ar/developers/es/docs/your-integrations/notifications/webhooks)
- TyC (17/07/2026): "En el caso de que un Usuario Vendedor haya recibido un pago y quien realizó el pago o el titular del medio de pago utilizado realizase una cancelación, anulación, contracargo, desconocimiento o reversión…" MP puede retener y "estará facultado para exigir el repago de esas operaciones". [TyC](https://www.mercadopago.com.ar/ayuda/terminos-y-condiciones_299)
- **Programa de Protección al Vendedor (PPV)**: "tiene por objeto cubrir parcial o totalmente a todo Usuario Vendedor que haya vendido y debidamente entregado un **bien tangible** y, no obstante, haya recibido el contracargo por el desconocimiento de pago". Excluye "Bienes intangibles. Servicios. Venta, alquiler y reservas automóviles, motos e inmuebles. Pagos hechos por medio de envíos o ingresos de dinero efectuados a través de Mercado Pago. Pagos realizados a través de televentas. Gift card o cupones de canje." Documentación "dentro de los siete días corridos desde que sea solicitada". [MP · PPV](https://www.mercadopago.com.ar/ayuda/602), 2026-09-25.
- Requisitos: "Venta de producto físico", "Monto cobrado correcto", "Comprobante de entrega … tenés 7 días de corrido"; para entrega propia: comprobante con "Número de operación y título del producto. Fecha de entrega. Nombre completo, DNI y firma de la persona que recibe." "Capturas de conversaciones en redes sociales o de historiales de entregas hechas por transportistas de apps no se aceptan como comprobantes." [MP · Requisitos PPV](https://www.mercadopago.com.ar/ayuda/294), 2026-09-25.
- Para QR y Link de pago (no Point): "Retenemos el dinero de este cargo e intentamos validar la venta. Si lo logramos, verás el monto reintegrado en tu cuenta." [Centro de vendedores · Contracargos](https://vendedores.mercadolibre.com.ar/nota/contracargos-con-point-link-de-pago-y-checkout-web-tus-cobros-siempre-protegidos), 2026-09-25.
- **Conclusión:** el contracargo lo absorbe el **vendedor** (se retiene de su cuenta), salvo que el PPV lo cubra; el nodo no toca el flujo. Quién responde en Split 1:1 con `marketplace_fee > 0` sigue sin texto oficial **(NC)**; con fee 0 y sin `marketplace` no hay parte del operador que retener. Nota para Vereda: como transferencias/dinero en cuenta no son tarjeta, no hay contracargo bancario; el riesgo de contracargo es solo de los pagos con tarjeta.
- Split: "In case of a refund, the amount due to the final customer will be divided and subtracted from the seller's account and the Marketplace's account, in a proportional way"; "the Marketplace cannot issue a full refund if the seller does not have sufficient funds". [Integrar checkout en Split 1:1](https://www.mercadopago.com.ar/developers/es/docs/split-payments/split-1-1/integration-configuration/integrate-marketplace)

---

## 3. Webhook al nodo, re-consulta, estados, Checkout web por redirección

### 3.1 Checkout Pro por redirección (sin SDK)

- Se crea la preferencia (`POST /checkout/preferences`, token del vendedor) y se abre `init_point`: "URL generada automáticamente para abrir el Checkout." (`sandbox_init_point` para pruebas). `items` es el único bloque obligatorio. [Referencia Crear preferencia](https://www.mercadopago.com.ar/developers/es/reference/online-payments/checkout-pro-preferences/create-preference/post), 2026-09-25.
- `back_urls`: "Return URLs to the seller's site, either automatically ('auto_return') or through the 'Return to site' button, depending on the payment status. **The use of the protocol ('https') in the URL is mandatory.** URLs with HTTP protocol (without 's') are automatically discarded by the API" → `success` ("URL de retorno ante pago aprobado"), `pending`, `failure`. [misma referencia]
- `auto_return`: "En el caso de estar especificado, el comprador será redirigido automáticamente al sitio del vendedor después de que la compra sea aprobada con tarjeta de crédito." Valor `approved`. [misma referencia]. La doc de redirección agrega que la redirección automática es "de hasta 40 segundos" y no se puede personalizar, y que no se pueden usar `localhost` / `127.0.0.1`. [MP · Redirección](https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/checkout-customization/user-interface/redirection), 2026-09-25.
- **Qué vuelve en la query de la `back_url`:** `payment_id`, `status` (approved/pending/rejected), `external_reference`, `merchant_order_id`, `collection_id`, `collection_status`, `payment_type`, `preference_id`, `site_id`, `processing_mode`, `merchant_account_id`. [misma doc de redirección]
- `external_reference`: "This field must be a maximum of 64 characters and may only contain numbers, letters, hyphens (-), and underscores (_)". Sirve para `pedido_id`. [Referencia Crear preferencia]
- `notification_url`: "Notifications URL available to receive notifications of events related to Payment. The maximum number of characters allowed … is 248 characters. The use of the protocol ('https') in the URL is mandatory. Important: this URL is not validated by the systems, therefore it is the integrator's responsibility to ensure its validity". [misma referencia]
- Vencimiento: `expires` (booleano) + `expiration_date_from` / `expiration_date_to` en formato `yyyy-MM-dd'T'HH:mm:ssz`; la respuesta trae `preference_expired`. [misma referencia]
- Extras útiles: `binary_mode` ("los pagos sólo pueden resultar aprobados o rechazados", sin `in_process`) y `statement_descriptor` (hasta 13 caracteres en el resumen de tarjeta). [misma referencia]

**iOS sin SDK:** la doc oficial de Checkout Pro para iOS abre la URL de la preferencia con `SFSafariViewController` (`import SafariServices`) y vuelve a la app con deep link: "Use Deep Links by setting `back_urls` and `auto_return`"; el ejemplo registra el esquema `iosapp` en `Info.plist` y recibe `iosapp://congrat/success` en `.onOpenURL`. No hay SDK nativo involucrado. [MP · Checkout Pro iOS (Swift)](https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/integrate-checkout-pro/mobile/ios/swift), 2026-09-25. Como `back_urls` exige `https`, para Vereda conviene usar **link universal** `https://…` del nodo/app (que iOS abre en la app) en vez de un esquema propio; el ejemplo oficial con `iosapp://` contradice la regla "https obligatorio" de la referencia, así que si se quiere esquema propio hay que probarlo **(NC)**.

**Pruebas:** "Test credentials are only available for Checkout API and Checkout Bricks integrations"; para Checkout Pro se prueba con las **credenciales de producción de una cuenta de prueba** (usuarios de prueba, tarjetas de prueba `APRO`, `OTHE`, `CONT`, etc.). "Test payments, created with test credentials, will not send notifications." [Credenciales](https://www.mercadopago.com.ar/developers/es/docs/your-integrations/credentials) · [MP · Compras de prueba](https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-preferences/integration-test/test-purchases) · [Webhooks](https://www.mercadopago.com.ar/developers/es/docs/your-integrations/notifications/webhooks)

### 3.2 Webhook: dónde se configura y tópicos

Fuente de toda esta sección salvo indicación: [MP · Webhooks](https://www.mercadopago.com.ar/developers/es/docs/your-integrations/notifications/webhooks), 2026-09-25.

- Dos formas: "Configuration through Your integrations" (por aplicación, con firma) y "Configuration during payment creation" (`notification_url` por preferencia). "The URLs configured during payment creation will take precedence over those configured through Your integrations."
- Tópicos relevantes para Checkout Pro: `payment` ("Creation and update of payments"), `topic_merchant_order_wh` ("Creation, closure, or expiration of commercial orders"), `topic_chargebacks_wh`, `topic_claims_integration_wh`, `stop_delivery_op_wh` (alertas de fraude, **sin reintentos**: "If you do not respond … the notification will be lost and will not be resent" [MP · Info adicional](https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-preferences/additional-content/notifications/additional-info)), `mp-connect` ("Linking and unlinking of accounts connected via OAuth").
- Al guardar: "This will generate a unique **secret signature** for your application … the generated signature does not have an expiration date, and its periodic renewal is not mandatory but highly recommended. Simply click the Reset button".
- "If you need to identify multiple accounts, you can add the parameter `?cliente=(sellersname)` to the endpoint URL to identify the sellers." (La app del operador recibe notificaciones de varias cuentas vendedoras.)
- Las notificaciones de QR "cannot be verified using the secret signature".

### 3.3 Firma: `x-signature` + `x-request-id`, HMAC-SHA256

- Header `x-signature` con formato `ts=<ms>,v1=<hex>`: "divide the header content by the `,` character … The value for the `ts` prefix is the notification timestamp (in milliseconds) and `v1` is the encrypted key."
- Manifest (template oficial): `id:[data.id_url];request-id:[x-request-id_header];ts:[ts_header];`
  - `[data.id_url]` = `data.id` recibido en los **query params** de la URL. "If `data.id` is returned with uppercase alphanumeric characters, convert it to lowercase before using it in the manifest."
  - "If any of the values (`data.id`, `x-request-id`) are not present in the received notification, you must remove them from the manifest before computing the HMAC."
- "compute an HMAC with the SHA256 hash function in hexadecimal base, using the secret key as the key and the template with the values as the message", comparar con `v1`; opcionalmente usar `ts` como tolerancia de retraso.
- La clave: "select the application in Your integrations, click Webhooks > Configure notification, and reveal the generated key". Los SDK oficiales traen la verificación HMAC.

Ejemplo (pseudocódigo, no código de producción):

```
manifest = "id:" + lower(query.data.id) + ";request-id:" + headers["x-request-id"] + ";ts:" + ts + ";"
ok = hex(hmac_sha256(secret, manifest)) == v1
```

### 3.4 Payload, respuesta, reintentos, idempotencia, re-consulta

- Body (tópico `payment`): `id` (Notification ID), `live_mode`, `type` (`payment`), `date_created`, `user_id` ("Seller identifier"), `api_version`, `action` (`payment.created` / `payment.updated`), `data.id` ("ID of the payment, merchant_order, or claim"). En otros tópicos el doc describe `id` como "Exclusive identifier of the event, prevents duplicate messages". [Webhooks] · [Info adicional](https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-preferences/additional-content/notifications/additional-info)
- Respuesta esperada: "return an HTTP STATUS 200 (OK) or 201 (CREATED)". Ventana: "The waiting time for confirmation of receipt of notifications is **22 seconds**."
- Reintentos: "the system will understand that the notification was not received and will **retry sending every 15 minutes** until a response is received. After the third attempt, the interval will be extended, but the attempts will continue." No publican tope de intentos ni ventana total **(NC)**.
- Re-consulta: "After responding to the notification and confirming its receipt, you can obtain the complete information of the notified resource" → `GET https://api.mercadopago.com/v1/payments/[ID]` (tópico `payment`), `GET https://api.mercadopago.com/merchant_orders/[ID]` (`topic_merchant_order_wh`), `GET /v1/chargebacks/[ID]`. Se consulta con el **token del vendedor** (dueño del pago).
- Desduplicación práctica: un mismo `data.id` (id del pago) llega varias veces (`payment.created`, `payment.updated`, y reintentos). Clave de idempotencia recomendada: (`data.id`, `action`) o directamente el `id` de la notificación, y en todos los casos **el estado que manda es el de la re-consulta**, no el del aviso.
- Panel: "Notifications dashboard" con estado de entrega, evento, fecha, "Trigger ID", y el JSON del request, para recuperar avisos perdidos.

### 3.5 ¿De quién es la clave secreta cuando el pago se crea con el token del vendedor (OAuth)?

Lo que dice la doc, literal:
- La clave se genera **por aplicación** en "Tus integraciones" y se compara "with the key provided for your application in Your integrations". [Webhooks]
- La app recibe avisos de varias cuentas (`?cliente=`), el payload trae `user_id` = "Seller identifier", y el tópico `mp-connect` avisa a la app cuando un vendedor la autoriza o desautoriza. [Webhooks] · [Gestionar Access Token](https://www.mercadopago.com.ar/developers/es/docs/security/oauth/management)
- El `access_token` OAuth es `APP_USR-<app_id>-…`: lleva el id de la app del operador. [Referencia POST /oauth/token]

Conclusión: para pagos creados con tokens OAuth obtenidos por la app del operador, la notificación llega a la `notification_url` de la preferencia (o a la URL configurada en la app del operador) firmada con la **clave secreta de la app del operador**; el vendedor no tiene ni necesita una app. Una frase que lo diga con esas palabras no aparece en la doc **(NC literal; alta confianza por construcción)**. En el camino B (token propio del comercio), la app es la del comercio y la clave secreta es la suya: el comercio tendría que pegar también esa clave en el nodo.

### 3.6 Estados de pago (oficial, referencia "Obtener pago")

| `status` | Descripción oficial |
|---|---|
| `pending` | "El usuario aún no ha completado el proceso de pago" |
| `approved` | "El pago ha sido aprobado y acreditado con éxito." |
| `authorized` | "El pago ha sido autorizado pero aún no se ha capturado." |
| `in_process` | "El pago está en proceso de revisión." |
| `in_mediation` | "El usuario ha iniciado una disputa." |
| `rejected` | "El pago fue rechazado (el usuario puede intentar pagar nuevamente)." |
| `cancelled` | "El pago fue cancelado por alguna de las partes o caducó." |
| `refunded` | "El pago fue reembolsado al usuario." |
| `charged_back` | "Se realizó un contracargo en la tarjeta de crédito del comprador." |

`status_detail` trae el motivo (`accredited`, `partially_refunded`, `pending_review_manual`, `cc_rejected_*`…). `money_release_date`: "Fecha en que se liquida el pago y se pone a disposición el dinero en la cuenta de Mercado Pago del Collector". [Referencia Obtener pago](https://www.mercadopago.com.ar/developers/es/reference/online-payments/checkout-api-payments/get-payment/get), 2026-09-25.

Regla para el nodo: marcar `confirmado` solo con `status = approved` en la re-consulta; `pending`/`in_process` queda pendiente; `refunded`/`charged_back`/`in_mediation` generan los eventos informativos ya previstos en `cobros.md`.

---

## 4. Comisiones y plazos 2026 (sin IVA) y riesgo BCRA

### 4.1 Link de pago / Checkout (online), oficial, por provincia

Tabla oficial del Centro de ayuda, **"Costos vigentes a partir del 6 de marzo de 2026"**, "Estos costos no incluyen IVA o retenciones", "Todos los medios de pago (tarjeta de crédito, débito y prepaga, efectivo, Cuotas sin Tarjeta, dinero en Mercado Pago)". La provincia es la del **domicilio registrado del vendedor**. [MP · ¿Cuánto cuesta recibir pagos con Link de pago?](https://www.mercadopago.com.ar/ayuda/cuanto-cuesta-recibir-pagos_33392), 2026-09-25.

| Provincia del vendedor | Al instante | 10 días | 18 días | 35 días |
|---|---|---|---|---|
| Buenos Aires · Chubut · Entre Ríos · Córdoba | 6,60 % | 4,61 % | 3,56 % | 1,56 % |
| La Rioja | 6,49 % | 4,53 % | 3,50 % | 1,54 % |
| Catamarca · Formosa · Mendoza | 6,46 % | 4,51 % | 3,48 % | 1,53 % |
| Santa Fe | 6,42 % | 4,48 % | 3,46 % | 1,52 % |
| Río Negro | 6,39 % | 4,46 % | 3,44 % | 1,51 % |
| CABA · Corrientes · La Pampa · Misiones · Neuquén · Salta · San Luis · Tierra del Fuego · Tucumán · Jujuy | 6,29 % | 4,39 % | 3,39 % | 1,49 % |
| Chaco · San Juan · Santa Cruz · Santiago del Estero | 6,19 % | 4,32 % | 3,34 % | 1,47 % |

"Para las tarjetas de crédito extranjeras y tarjeta Sucrédito, el costo se incrementará un 3%." [misma fuente]. La página de producto "Checkout" muestra los mismos valores base (6,29 / 4,39 / 3,39 / 1,49 % + IVA). [MP · Checkout](https://www.mercadopago.com.ar/herramientas-para-vender/check-out), 2026-09-25.

Esto corrige `pasarelas-1.md`: el ajuste provincial (PBA 6,60 %) ya no es NC, es oficial y con fecha.

### 4.2 QR (oficial, página de producto; sin desglose provincial)

| Medio | Al instante | Con plazo |
|---|---|---|
| Dinero en cuenta / otras billeteras y bancos | 0,8 % + IVA | — |
| Débito | 1,35 % + IVA | 0,85 % a 2 días |
| Crédito | 5,99 % + IVA | 4,19 % a 10 días |
| Cuotas sin Tarjeta | 1,35 % + IVA | — |

[MP · Cobrar con QR](https://www.mercadopago.com.ar/herramientas-para-vender/cobrar-con-qr), 2026-09-25. La página de ayuda de costos por medio de cobro (`ayuda/33403`) no expone el artículo en el HTML; el desglose provincial de QR y Point queda **(NC)**.

### 4.3 Plazos de acreditación

Los elige el vendedor (al instante, 10, 18 o 35 días) desde "Costos y cuotas"; el costo baja con el plazo. [MP · Costos por cobro](https://www.mercadopago.com.ar/ayuda/recibir-pagos-costos_220), 2026-09-25. En la API, `money_release_date` indica cuándo se libera. [Referencia Obtener pago]

### 4.4 Retenciones e impuestos

Sin cambios respecto de `pasarelas-1.md` §1.8: siguen siendo fuentes secundarias **(NC)**. La tabla oficial de costos aclara que no incluye "IVA o retenciones".

### 4.5 BCRA: quién es quién

**Registro oficial del BCRA** (datos vivos del endpoint que alimenta la nómina pública; consultado 2026-09-25):

| Tipo de PSP (BCRA) | Entidad | CUIT | Registro |
|---|---|---|---|
| PSP que ofrece **Cuentas de Pago** (PSPCP) | MERCADOLIBRE S.R.L. ("MERCADO PAGO") | 30-70308853-4 | código 33535; "habilitadoOperaComoServicio: No" |
| **Agregador** | MERCADOLIBRE S.R.L. ("MERCADO PAGO") | 30-70308853-4 | código 33535 |
| **Adquirente** | MERCADO PAGO SERVICIOS DE PROCESAMIENTO S.R.L. | 30-71699949-8 | código 34575 |
| Iniciador | no figura Mercado Libre / Mercado Pago (5 inscriptos) | — | — |

Fuente: [BCRA · Registro de PSP, resultados por tipo](https://www.bcra.gob.ar/en/payment-service-provider-registration-results-by-type/?tipoPSP=1) (PSPCP = `tipoPSP=1`, iniciadores = 2, adquirentes = 6, agregadores = 7; la página carga los datos de `https://www.bcra.gob.ar/api/endpoints/proveedores-psp.php?tipoPSP=N`). Totales al 2026-09-25: 233 PSPCP, 5 iniciadores, 15 adquirentes, 92 agregadores. Manual del registro: [BCRA](https://www.bcra.gob.ar/Pdfs/SistemasFinancierosYdePagos/Manual-de-Usuario-Registro-de-proveedores-de-servicios-de-pago.pdf).

- TyC de MP: "Mercado Pago ofrece servicios de pago y no se encuentra autorizado a operar como entidad financiera por el Banco Central de la República Argentina … Los fondos depositados en la cuenta de pago no constituyen depósitos en una entidad financiera". Y "Mercado Pago es una unidad de negocios de MercadoLibre S.R.L." (CUIT 30-70308853-4). [TyC](https://www.mercadopago.com.ar/ayuda/terminos-y-condiciones_299), 17/07/2026.
- El texto ordenado "Proveedores de servicios de pago" (última Com. "A" 8454) está en [BCRA · t-snp-psp.pdf](https://www.bcra.gob.ar/Pdfs/Texord/t-snp-psp.pdf); no se pudo extraer el texto en esta sesión (sin `pdftotext`) **(NC literal)**. Lectura de encuadre según `cobros/legal.md`.

**Encuadre del operador del nodo con este modelo (fee 0, token del vendedor):**
- Los fondos van del pagador a la cuenta de pago del **vendedor** en MP (`collector_id` = vendedor). El operador nunca es `collector`, no cobra `marketplace_fee`, no tiene saldo de terceros ni ordena transferencias. No hay cuenta de pago del operador involucrada, así que no ofrece cuentas de pago (PSPCP), no agrega ni adquiere (eso es MP, ya inscripto) y no inicia pagos desde la cuenta del comprador (el comprador paga en el checkout de MP). Con esta lectura el nodo queda como **nada** ante el BCRA: es un integrador de software del vendedor.
- El único riesgo regulatorio que aparece es reputacional/contractual: el token del vendedor permite crear cobros y devoluciones; hay que cifrarlo y ofrecer revocación (ya está en `cobros.md` §5). Es lectura de normas y docs, no dictamen legal (ver `legal.md`).

---

## 5. Transferencias entrantes al CVU: ¿webhook o API?

- **Lo oficial que existe:** en la API de pagos, `operation_type` admite `money_transfer` = "Transferencia de fondos entre dos usuarios." y `account_fund` = "Depósito de dinero en la cuenta del usuario." [Referencia Obtener pago](https://www.mercadopago.com.ar/developers/es/reference/online-payments/checkout-api-payments/get-payment/get), 2026-09-25. `GET /v1/payments/search` acepta `operation_type` y `payment_type_id` como filtros (aparecen en el ejemplo curl de la referencia, sin descripción), más `range`/`begin_date`/`end_date` ("NOW-30DAYS", "NOW"), `sort`, `criteria`, `external_reference`, `limit`, `offset`. [MP · Referencia Buscar pagos](https://www.mercadopago.com.ar/developers/es/reference/online-payments/checkout-api-payments/search-payments/get), 2026-09-25.
- **Lo que NO dice la doc:** que una transferencia recibida en el CVU/alias del vendedor (desde otro banco o billetera) aparezca en `/v1/payments/search` con el token del vendedor, ni que dispare el tópico `payment`. Ninguna página de developers habla de "transferencia recibida". **(NC)**
- **Terceros (no oficial):** un repo público que concilia señas por transferencia afirma: "las transferencias que te llegan directo al alias/CVU generalmente sí generan un 'pago' (`payment_type_id: account_money`) y disparan este mismo webhook … Pero conviene comprobarlo apenas tengas el access token: hacete una transferencia de prueba de un monto raro (ej $1,23)". [GitHub · 7b4wg2pgzp-eng/pagos README](https://github.com/7b4wg2pgzp-eng/pagos), 2026-09-25. **(NC)**. Es exactamente lo que ya sugería `cobros.md` §1: probar con una transferencia real antes de prometerlo.
- **Reporte oficial de dinero en cuenta** ("Account money report", CSV con `TRANSACTION_TYPE` SETTLEMENT/REFUND/CHARGEBACK/DISPUTE/WITHDRAWAL… y `SETTLEMENT_NET_AMOUNT`): es la herramienta oficial de conciliación por lote; no confirma si lista transferencias entrantes por CVU como fila propia **(NC)**. [MP · Uso del reporte](https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-preferences/additional-content/reports/account-money/how-to-use), 2026-09-25.
- **CVU o referencia por cobro:** no existe en la API pública; el CVU es uno por cuenta: "Cada Cuenta Mercado Pago cuenta con una Clave Virtual Uniforme ('CVU') asociada … En su Cuenta Mercado Pago el Usuario sólo puede recibir transferencias o pagos a través de las herramientas habilitadas". [TyC](https://www.mercadopago.com.ar/ayuda/terminos-y-condiciones_299). La conciliación por "centavos únicos" sigue siendo el mecanismo viable, y depende del punto anterior (NC).
- **QR interoperable a nombre del comercio con aviso:** sí existe vía API de Orders (QR dinámico/estático, tópico `orders`), pero es el QR de MP y el aviso llega por el webhook de la app; el QR no verifica firma ("QR Code notifications cannot be verified using the secret signature"). [Webhooks]. Ya cubierto en `pasarelas-1.md` §1.3; nada nuevo oficial sobre el pago desde otras billeteras al QR de MP más allá de "solo con dinero en cuenta".

---

## Qué cambió respecto de `cobros.md` / `pasarelas-1.md`

1. **Fee 0 confirmado en doc oficial** (era NC): `marketplace_fee` "default value is 0" y solo se puede mandar junto a un `marketplace` válido; `marketplace` "default value is NONE". Recomendación: omitir ambos. Los ejemplos oficiales mandan `marketplace_fee: 0`.
2. **Rotación del `refresh_token` confirmada en doc oficial** (era NC de un blog): "every time you refresh the access_token, the refresh_token will also be refreshed". Access token 180 días; renovación exige scope `offline_access`.
3. **Costos online por provincia, oficiales y con fecha** (era NC de prensa): tabla del Centro de ayuda "vigentes a partir del 6 de marzo de 2026", sin IVA; PBA/Córdoba 6,60 % → 1,56 %; CABA 6,29 % → 1,49 %; +3 % tarjetas extranjeras.
4. **Lista oficial de estados de pago** (la página daba 404): 9 estados con descripción, en la referencia "Obtener pago".
5. **BCRA, nuevo:** MercadoLibre S.R.L. figura como **PSPCP y Agregador**; Mercado Pago Servicios de Procesamiento S.R.L. como **Adquirente**. Datos vivos del registro oficial.
6. **Webhook:** confirmado ventana de 22 s, reintentos cada 15 min con intervalo creciente tras el 3.º, sin tope publicado; manifest `id;request-id;ts` con `data.id` en minúsculas; clave secreta **por aplicación**, sin vencimiento; `user_id` = vendedor; `?cliente=` para múltiples cuentas; `mp-connect` para alta/baja del vendedor. Que la firma sea la de la app del operador en pagos OAuth sigue sin frase literal, pero la construcción lo confirma.
7. **`sponsor_id` está deprecado** (la spec no debe usarlo). `integrator_id` es del programa de partners, opcional.
8. **Split 1:1 solo permite pagos con saldo entre cuentas MP** ("Transfers from external financial institutions are not permitted"): otra razón para no declarar `marketplace` con fee 0.
9. **Contracargos:** ahora con TyC (17/07/2026) y PPV oficial: lo absorbe el vendedor salvo cobertura del PPV (bienes tangibles entregados, comprobante en 7 días corridos). En Split con fee > 0 sigue NC.
10. **iOS sin SDK confirmado** (SFSafariViewController + deep link) y regla `https` obligatoria en `back_urls`; parámetros de vuelta enumerados.
11. **Transferencias entrantes:** sigue NC; se suma que la API tiene `operation_type = money_transfer` documentado, y una afirmación de terceros de que sí disparan el webhook `payment` con `account_money`. Hay que probarlo.
12. **Devoluciones:** `X-Idempotency-Key` es obligatorio (error 4292); plazo 180 días; saldo requerido. Sin novedades de fondo.

---

## Datos (NC)

- Qué es "KYC nivel 6" y si aplica cuando el fee es 0 y no se declara `marketplace`.
- Frase literal de que los pagos creados con token OAuth se notifican a la app del operador y se firman con su clave (la construcción lo confirma; no hay oración que lo diga).
- Tope de reintentos y ventana total de reintentos del webhook (solo "cada 15 min, intervalo creciente tras el 3.º, siguen").
- Que un esquema propio (`iosapp://`) funcione en `back_urls` pese a la regla "https obligatorio" (el ejemplo oficial lo usa).
- Quién responde el contracargo en Split 1:1 con `marketplace_fee > 0`.
- Tiempo y pasos exactos de validación de identidad al abrir cuenta MP.
- Desglose provincial de costos para QR y Point (la página `ayuda/33403` no expone el artículo).
- Retenciones (SIRTAC, percepción de IVA): siguen solo en fuentes secundarias.
- Transferencias al CVU: si aparecen en `/v1/payments/search` y si disparan el tópico `payment` (solo un repo de terceros lo afirma). Si el reporte de dinero en cuenta las lista.
- Texto literal del régimen de PSP del BCRA (PDF no extraído en esta sesión).

---

## Fuentes (consultadas el 2026-09-25)

Mercado Pago developers (docs):
- OAuth introducción: https://www.mercadopago.com.ar/developers/es/docs/security/oauth/introduction
- OAuth obtener token (auth code, PKCE, client credentials): https://www.mercadopago.com.ar/developers/es/docs/security/oauth/creation
- OAuth renovar token: https://www.mercadopago.com.ar/developers/es/docs/security/oauth/renewal
- OAuth gestionar/invalidar: https://www.mercadopago.com.ar/developers/es/docs/security/oauth/management
- OAuth buenas prácticas: https://www.mercadopago.com.ar/developers/es/docs/security/oauth/best-practices
- Panel del desarrollador (crear app): https://www.mercadopago.com.ar/developers/es/docs/your-integrations/dashboard
- Detalles de aplicación (redirect URL, PKCE, permisos): https://www.mercadopago.com.ar/developers/es/docs/your-integrations/application-details
- Credenciales (activar producción, compartir): https://www.mercadopago.com.ar/developers/es/docs/your-integrations/credentials
- Webhooks: https://www.mercadopago.com.ar/developers/es/docs/your-integrations/notifications/webhooks
- Información adicional de notificaciones: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-preferences/additional-content/notifications/additional-info
- Split 1:1 requisitos: https://www.mercadopago.com.ar/developers/es/docs/split-payments/split-1-1/prerequisites
- Split 1:1 integrar checkout: https://www.mercadopago.com.ar/developers/es/docs/split-payments/split-1-1/integration-configuration/integrate-marketplace
- Checkout Pro marketplace: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-preferences/how-tos/integrate-marketplace
- Checkout Pro redirección (back_urls, auto_return, parámetros de vuelta): https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/checkout-customization/user-interface/redirection
- Checkout Pro iOS Swift: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/integrate-checkout-pro/mobile/ios/swift
- Checkout Pro compras de prueba: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-preferences/integration-test/test-purchases
- Devoluciones y cancelaciones: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-preferences/additional-settings/refunds-and-cancellations
- Contracargos (intro): https://www.mercadopago.com.ar/developers/es/docs/checkout-api-orders/payment-management/chargebacks/introduction
- Certificaciones / Integrator ID: https://www.mercadopago.com.ar/developers/es/docs/checkout-api-payments/additional-content/certifications
- Reporte de dinero en cuenta: https://www.mercadopago.com.ar/developers/es/docs/checkout-pro-preferences/additional-content/reports/account-money/how-to-use

Mercado Pago developers (referencia de API):
- POST /oauth/token: https://www.mercadopago.com.ar/developers/es/reference/authentication/oauth/_oauth_token/post
- POST /checkout/preferences: https://www.mercadopago.com.ar/developers/es/reference/online-payments/checkout-pro-preferences/create-preference/post
- GET /v1/payments/{id}: https://www.mercadopago.com.ar/developers/es/reference/online-payments/checkout-api-payments/get-payment/get
- GET /v1/payments/search: https://www.mercadopago.com.ar/developers/es/reference/online-payments/checkout-api-payments/search-payments/get
- POST /v1/payments/{id}/refunds: https://www.mercadopago.com.ar/developers/es/reference/online-payments/checkout-api-payments/create-refund/post
- Noticia idempotencia obligatoria (2023-01-04): https://www.mercadopago.com.ar/developers/en/news/2023/01/04/Idempotency-key-usage-will-be-mandatory

Mercado Pago (ayuda, producto, TyC):
- Costos Link de pago por provincia (vigentes 06/03/2026): https://www.mercadopago.com.ar/ayuda/cuanto-cuesta-recibir-pagos_33392
- Costos por cobro (índice): https://www.mercadopago.com.ar/ayuda/recibir-pagos-costos_220
- Checkout (producto): https://www.mercadopago.com.ar/herramientas-para-vender/check-out
- QR (producto): https://www.mercadopago.com.ar/herramientas-para-vender/cobrar-con-qr
- Programa de Protección al Vendedor (términos): https://www.mercadopago.com.ar/ayuda/602
- Requisitos del PPV: https://www.mercadopago.com.ar/ayuda/294
- Recibí un contracargo: https://www.mercadopago.com.ar/ayuda/30229
- Contracargos con Point, Link de pago y Checkout (Centro de vendedores): https://vendedores.mercadolibre.com.ar/nota/contracargos-con-point-link-de-pago-y-checkout-web-tus-cobros-siempre-protegidos
- Términos y condiciones (17/07/2026): https://www.mercadopago.com.ar/ayuda/terminos-y-condiciones_299
- Registro de cuenta: https://www.mercadopago.com.ar/hub/registration/landing

BCRA:
- Registro de PSP, resultados por tipo (PSPCP): https://www.bcra.gob.ar/en/payment-service-provider-registration-results-by-type/?tipoPSP=1 (datos: https://www.bcra.gob.ar/api/endpoints/proveedores-psp.php?tipoPSP=1; adquirentes `tipoPSP=6`, agregadores `tipoPSP=7`, iniciadores `tipoPSP=2`)
- Texto ordenado PSP: https://www.bcra.gob.ar/Pdfs/Texord/t-snp-psp.pdf
- Manual del registro: https://www.bcra.gob.ar/Pdfs/SistemasFinancierosYdePagos/Manual-de-Usuario-Registro-de-proveedores-de-servicios-de-pago.pdf

Terceros (marcados NC):
- README repo "pagos" (conciliación de transferencias por webhook): https://github.com/7b4wg2pgzp-eng/pagos

---

## Resumen

1. Cobrar en nombre del comercio con fee 0 está avalado por la doc oficial: preferencia de Checkout Pro creada con el `access_token` OAuth del vendedor, sin `marketplace_fee` (default 0) ni `marketplace` (default NONE); el operador solo registra una app gratuita con redirect URL https, sin aprobación ni certificación.
2. Tokens: código 10 min, access token 180 días, refresh token 6 meses y rota en cada renovación (confirmado oficialmente); revocable por el vendedor, con aviso `mp-connect`.
3. Webhook firmado por aplicación (`x-signature` ts/v1, HMAC-SHA256 del manifest `id;request-id;ts`), 22 s para responder 200, reintentos cada 15 min, y re-consulta obligatoria con `GET /v1/payments/{id}`; Checkout Pro funciona por redirección pura (SFSafariViewController + back_urls https) sin SDK.
4. Costos online oficiales vigentes desde 06/03/2026, sin IVA: CABA 6,29 % al instante a 1,49 % a 35 días, PBA/Córdoba 6,60 % a 1,56 %; devoluciones por API con `X-Idempotency-Key` hasta 180 días; contracargos los absorbe el vendedor salvo PPV; MercadoLibre S.R.L. es PSPCP y agregador inscripto en el BCRA y el nodo con fee 0 no entra en ninguna figura.
5. Transferencias al CVU siguen sin doc oficial: existe `operation_type = money_transfer` en la API, pero que aparezcan en `payments/search` o disparen el webhook solo lo afirma un repo de terceros; hay que probarlo con una transferencia real antes de prometer conciliación automática.
