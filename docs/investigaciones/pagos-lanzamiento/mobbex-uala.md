# Mobbex y Ualá Bis como alternativa rápida a Mercado Pago

Chequeo rápido del 2026-09-25 (≈40 min), solo fuentes públicas. Construye sobre `docs/investigaciones/cobros.md` y sus anexos `cobros/pasarelas-1.md` (Ualá Bis §3) y `cobros/pasarelas-2.md` (Mobbex §1). Todo dato lleva link; lo que no apareció va **(NC)**. Fecha de consulta de todas las fuentes: 2026-09-25.

---

## A. Mobbex

### 1. Cobrar en nombre del comercio (Dev Connect)

- **Modelo.** La API siempre pide dos headers: `x-api-key` ("clave API de su aplicación") y `x-access-token` ("token de acceso a la entidad"). La *aplicación* es del integrador (el operador del nodo); la *entidad* es el comercio. [https://mobbex.dev/primeros-pasos]
- **Cómo consigue el operador su `x-api-key`.** Entra al **Portal de Desarrolladores** (`mobbex.com/devportal`) "con las credenciales del comercio" (o sea, necesita un usuario/consola Mobbex propia), toca "+", completa **Nombre, Descripción y URL de tu Aplicación** y obtiene la API key. Es autoservicio: la doc no menciona ninguna aprobación de Mobbex sobre la app. [https://ayuda.mobbex.com/credenciales-para-integracion-a-traves-de-api] [https://mobbex.dev/en-first-steps]
  - Crear el usuario es inmediato ("al hacer clic en registrarse el usuario ya estará creado"). Si además hace falta que la *entidad* del operador esté validada (alta de comercio, "unos días hábiles") para poder crear una app: **(NC)**. [https://ayuda.mobbex.com/crear-usuarios]
  - No hay figura de "partner" ni "desarrollador aprobado" en la doc. **(NC)** que no exista un filtro no documentado.
- **Dev Connect (el "Conectar con Mobbex").** Tres pasos, solo con `x-api-key` (sin access token del comercio, porque todavía no lo tenés):
  1. `POST https://api.mobbex.com/p/developer/connect` body `{"return_url": "..."}` → `{ "data": { "id": "oZWpdzX7y", "url": "https://mobbex.com/p/developer/connect/oZWpdzX7y" } }`.
  2. Redirigís al comercio a esa `url`; se loguea en Mobbex y vuelve a `return_url` con `connectStatus=done` (o `cancelled`).
  3. `GET https://api.mobbex.com/p/developer/connect/{id}/credentials` → `access_token` del comercio + `entity { name, tax_id, logo }`.
  [https://mobbex.dev/dev-connect] — SDK Node: `devConnect.create({return_url})` / `devConnect.get(id)` [https://github.com/mobbexco/nodejs]
- **Alternativa manual** (sin Dev Connect): el integrador pide "Solicitar acceso" por CUIT del comercio y el comercio toca "Autorizar" en su consola → "Ver credenciales". [https://ayuda.mobbex.com/credenciales-para-integracion-a-traves-de-api]
- **Fee de plataforma 0:** por omisión. No existe campo de fee; el cobro se crea en la entidad del comercio y va entero a su cuenta. Solo si se manda `split` se reparte. [https://mobbex.dev/checkout]
- **Vida del token / refresh / revocación:** **no documentado (NC)**. El access token de entidad parece estático (el comercio lo ve en su consola y puede revocar la app desde "APP/E-Commerce"; el detalle de revocación **NC**).
- **KYC del operador:** ninguno documentado más allá de tener usuario Mobbex. **(NC)** si Mobbex valida la entidad del operador aunque no cobre.

### 2. Alta del comercio, contracargos, devoluciones

- **Alta:** "El alta de cuenta lleva unos días hábiles según validación". Requisitos exactos no publicados; los TyC piden "datos verificables: domicilio, email, teléfono y cualquier otra información que Mobbex requiera… para prevención de fraude". **(NC)** si acepta monotributista/persona física sin más. [https://www.mobbex.com/faq/] [snippet de https://ayuda.mobbex.com/es/terminos-y-condiciones — la página devolvió 404 al abrirla]
- **Contracargos:** los absorbe el comercio. TyC Agrupador (actualizado 13/03/2025, snippet): cuando hubo liquidación de una operación luego contracargada o devuelta, el comercio "autoriza a Mobbex a debitar de futuras liquidaciones" y no recupera retenciones ni fee. FAQ: "Perdés el monto original, pagás el fee del procesador". [snippet https://ayuda.mobbex.com/terminos-y-condiciones-de-mobbex-agrupador (404 al abrir)] [https://www.mobbex.com/faq/]
- **Devoluciones por API:**
  - Total: `GET https://api.mobbex.com/p/operations/{ID}/refund`.
  - Parcial (o total con opciones): `POST …/operations/{ID}/refund` body `{ "total": 123.45 }`. **Parcial solo a partir del día siguiente.**
  - Mismo día → webhook `601` (cancelada); día siguiente o después → `602` (devuelta); parcial → `605` / `200`.
  - **No admiten devolución:** QR interoperable, DEBIN, efectivo, Pix, Binance.
  [https://mobbex.dev/devoluciones]

### 3. Webhook, re-consulta, estados, checkout por redirección

- **Checkout:** `POST https://api.mobbex.com/p/checkout` con `total`, `description`, `currency: "ars"`, `reference` (**única**, no admite dos pagos con la misma), `customer {email, name, identification}`, opcionales `return_url`, `webhook`, `timeout` (default 60 min), `test: true`. Responde `id` y `url` = `https://mobbex.com/p/checkout/v2/{id}`. Es 100% web: se abre en `SFSafariViewController` y no requiere SDK. [https://mobbex.dev/checkout]
- **Vuelta:** `return_url?status=200&type=card&transactionid=…`; cancelado → `status=0&type=none`. Acepta cualquier URL (universal link) **(NC explícito: la doc no restringe el esquema)**. [https://mobbex.dev/checkout]
- **Webhook:** POST JSON `{ type: "checkout", data: { payment: { id, status: {code, text}, total, … }, entity, customer, checkout: {uid, reference} } }` a la URL del campo `webhook`. Exige TLS ≥ 1.2.
  - **Firma: no existe** (ni HMAC ni secreto). → siempre re-consultar.
  - **Reintentos: no documentados (NC).** **Id de evento: no hay**; usar `data.payment.id` + `reference` como idempotencia.
  [https://mobbex.dev/webhooks]
- **Re-consulta:** `GET https://api.mobbex.com/p/operations/{uid}` (o `?ref=` por referencia) y listado `GET /p/entity/operations?page=0&reference=…`. [https://mobbex.dev/consulta-de-operaciones-y-childs]
- **Estados** (código numérico): 1 pendiente · 2 en espera · 3 autorizada · 100 en revisión · **200 paga** · 201 aceptada · 210 retenida · 300 acreditado · 301 liquidado · 400 declinada · 401 expirada · 402 abandonada · 403 fallida · 410–419 rechazos · 600 cancelación en proceso · 601 cancelada · 602 devuelta · 605 parcialmente devuelta · 610 cancelada por operatoria inválida. Regla práctica: **≥200 y <300 = pagado**; 300–302 = plata ya liquidada. [https://mobbex.dev/codigos-de-estado]
- **Sandbox público sin cuenta: sí.** Credenciales de prueba en la doc: `x-api-key zJ8LFTBX6Ba8D611e9io13fDZAwj0QmKO1Hn1yIj`, `x-access-token d31f0721-2f85-44e7-bcc6-15e19d1a53cc` (entidad "Demo Mobbex", user `demo@mobbex.com`, PIN 0000). También `test: true` con credenciales productivas. QR interoperable y Pix **no aparecen en modo test**. [https://mobbex.dev/primeros-pasos] [https://mobbex.dev/listado-de-medios-de-pago]

### 4. Comisiones 2026, plazos, BCRA

- **Plan Essential (sin alta ni mínimos), por transacción aprobada:** débito **1,9% + IVA**, crédito y prepagas **2,6% + IVA**, suscripciones 3,9% + IVA. QR interoperable **0,8% + IVA** (snippet TyC Agrupador; **NC** en página de planes). Transferencia/DEBIN/efectivo: no publicado **(NC)**. Enterprise: a medida, mínimo $70.000.000/mes. [https://www.mobbex.com/planes/] [snippet https://ayuda.mobbex.com/terminos-y-condiciones-de-mobbex-agrupador]
- **Acreditación:** débito 2 días hábiles, crédito 10–18 días hábiles "según la entidad financiera"; QR al instante. Sin opción de elegir plazo vs. tasa. [https://www.mobbex.com/faq/]
- **BCRA:** Mobbex Argentina S.R.L. (CUIT 30-71512358-0) se define como **PSP en función "Agrupador"** ("procesamiento integral electrónico de pagos con tarjetas…"), "no autorizado a operar como entidad financiera". **No es PSPCP** (no ofrece cuentas de pago: liquida a la cuenta bancaria que designa el comercio). Número de inscripción en el registro BCRA: **(NC)** (el registro no es consultable por fetch). [snippets https://ayuda.mobbex.com/es/terminos-y-condiciones y https://www.mobbex.com/terminos — ambos 404 al abrir] [https://www.bcra.gob.ar/SistemasFinancierosYdePagos/Proveedores-servicios-de-pago-ofrecen-cuentas-de-pago.asp]
- **¿El integrador tiene que ser PSP/agregador?** No en la doc: con Dev Connect cada comercio es la entidad Mobbex de su propio cobro y el operador solo tiene una "aplicación". El modelo con `split` sí traslada al "originador" la prevención de fraude, pero Vereda no lo usa. [https://mobbex.dev/dev-connect] [https://ayuda.mobbex.com/modalidad-con-split-de-pagos]

### 5. Transferencias y QR

- Dentro del checkout Mobbex hay **DEBIN** (`arg.debin`), **QR interoperable** (`arg.qr`), QR Prisma, efectivo (Rapipago, Pago Fácil, Cobro Express, Pago Mis Cuentas) y billeteras. Se avisan por el **mismo webhook del checkout** (inferencia: es un medio más del checkout; **NC explícito**). [https://mobbex.dev/listado-de-medios-de-pago]
- **Transferencia entrante a un CVU del comercio: no aplica.** Mobbex no da CVU ni cuenta de pago; liquida a la cuenta bancaria del comercio. No hay API de "transferencias recibidas". **(NC: no existe, según todo lo leído)**
- QR interoperable a nombre del comercio con aviso: sí, pero solo como medio dentro de un checkout (no un QR estático propio del comercio vía API) **(NC)**, sin modo test y **sin devolución por API**. [https://mobbex.dev/devoluciones]

---

## B. Ualá Bis

### 1. Cobrar en nombre del comercio (credenciales del comercio)

- **No hay OAuth ni concepto de "aplicación" del integrador.** El comercio genera sus propias credenciales de **test y producción** en la app: **Ualá Bis → Cobros online → API** (`username`, `client_id`, `client_secret_id`). Las carga en el nodo. Nada que registrar para el operador, cero aprobación, cero KYC del operador. [https://developers.ualabis.com.ar/v2/ambientes]
- **Token:** `POST https://auth.developers.ar.ua.la/v2/api/auth/token` con `{username, client_id, client_secret_id, grant_type: "client_credentials"}` → Bearer, `expires_in: 86400` (24 h). No hay refresh: se vuelve a pedir. Stage: `https://auth.stage.developers.ar.ua.la/v2/api`. [https://developers.ualabis.com.ar/v2/authentication/create]
- **Fee de plataforma 0:** por construcción; no existe split ni fee. Todo va a la cuenta Ualá del comercio.
- **Sandbox público sin cuenta: no.** Las credenciales de test se ven dentro de la app (hace falta cuenta Ualá con Ualá Bis) y "son privadas, no se deben compartir". Tarjeta de prueba en "Credenciales de prueba → Ver datos de tarjeta de prueba". [https://developers.ualabis.com.ar/v2/ambientes]

### 2. Alta, contracargos, devoluciones

- **Alta:** autoservicio desde la app de Ualá (persona física) o empresas.ualabis.com.ar (jurídica). Ya usuario Ualá: **~24 h** para habilitar cobros; nuevo: **~48 h**. Personas jurídicas: estatuto, acta de autoridades, libro de acciones, balance, constancia de inscripción; "lista en 24 h hábiles". Persona física: requisitos exactos (CUIL, condición fiscal) **(NC)** — el instructivo PDF oficial no fue legible. [https://ayuda.tiendanube.com/es_ES/uala/preguntas-frecuentes-sobre-uala-bis, act. 2026-02-11] [https://www.uala.com.ar/empresas] [https://empresas.ualabis.com.ar/documents/Instructivo%20crear%20cuenta%20Ual%C3%A1.pdf]
- **Contracargos:** al comercio. TyC: "Ualá trasladará al Usuario la responsabilidad por la transacción cuestionada… debitará el monto de la Cuenta del Usuario y/o saldos futuros". [https://assets.ctfassets.net/t5yal6u1wvnw/1EsrWh7PHBXHsiLdMpJShT/c6985c60a366656085b5e09d66af3052/_05.05.23__-_TyC_UalaBis.docx.pdf, 2023-05-05]
- **Devoluciones por API (v2):** `POST https://checkout.developers.ar.ua.la/v2/api/orders/{uuid}/refund` body `{ "amount": "…", "notification_url": "…" }` → `{ "status": "INITIATED" }`. Condiciones: orden `APPROVED`, sin devolución en curso, **menos de 90 días** desde el pago, creada con API Checkout v2. Resultado por webhook `REFUNDED` / `NOT_REFUNDED`. **Parcial: `amount` es obligatorio y la doc no lo restringe al total, pero tampoco dice "parcial" (NC)**; Tiendanube (otro canal) sigue diciendo "solo total, 24 h a 30 días". [https://developers.ualabis.com.ar/v2/refunds/create] [https://developers.ualabis.com.ar/v2/refunds/create/webhook]

### 3. Webhook, re-consulta, estados, checkout por redirección

- **Checkout:** `POST https://checkout.developers.ar.ua.la/v2/api/checkout` con `amount` (**string en centavos**, mín. `"2500"`, máx. `"999999900"`), `description`, `callback_success`, `callback_fail`, `notification_url`, `external_reference`. Responde `uuid`, `status: "PENDING"`, `links.checkout_link`. Web pura → `SFSafariViewController`. Vencimiento del link y parámetros que agrega a los callbacks: **(NC)**. [https://developers.ualabis.com.ar/v2/orders/create]
- **Webhook:** POST a `notification_url` con `{ uuid, external_reference, status, created_date, api_version }`. **Sin firma.** Responder **200**; si no, **hasta 3 reintentos más (4 intentos en total)**, intervalo **(NC)**. Sin id de evento: idempotencia por `uuid` + `status`. [https://developers.ualabis.com.ar/v2/orders/create/webhook]
- **Re-consulta:** `GET /v2/api/orders/{uuid}` → `status`, `amount`, `external_reference`, `customer`, `changelog` (historial de estados), `commissions` y `taxes` (solo en `APPROVED`). También `GET /v2/api/orders` (find). [https://developers.ualabis.com.ar/v2/orders/get]
- **Estados:** `PENDING` → `PROCESSED` (cobrado, pendiente de desembolso) → `APPROVED` (plata en la cuenta Ualá) · `REJECTED` · `REFUNDED`. Marcar pagado en `APPROVED` (o `PROCESSED` si el comercio acepta el riesgo). [https://developers.ualabis.com.ar/v2/orders/get]
- **v1 se depreca el 2026-12-31** → integrar directo v2. [https://developers.ualabis.com.ar/]

### 4. Comisiones 2026, plazos, BCRA

| Producto | Comisión (sin IVA) | Fuente |
|---|---|---|
| API Checkout / link de pago | **4,9%** crédito, débito y prepaga | [https://www.ualabis.com.ar/link-de-pago] [https://ayuda.tiendanube.com/es_ES/uala/preguntas-frecuentes-sobre-uala-bis] |
| QR interoperable, dinero en cuenta | **0% los primeros 3 meses, 0,8% después** | [https://www.ualabis.com.ar/qr] |
| QR con tarjeta | débito 2,9%, crédito/prepaga 4,9% | [https://www.ualabis.com.ar/qr] |

- **Acreditación:** "al instante" en la cuenta Ualá, sin opción de plazo. [https://ayuda.tiendanube.com/es_ES/uala/preguntas-frecuentes-sobre-uala-bis]
- **BCRA:** Alau Tecnología S.A.U. (CUIT 30-71542170-0) es **PSPCP inscripto N.º 33.549** en el Registro de PSP, billetera interoperable N.º 36.504 y proveedor no financiero de crédito N.º 55.329; "no está autorizado por el BCRA para operar como entidad financiera". [https://www.uala.com.ar/legales] [https://www.ualabis.com.ar/preguntas-frecuentes]
- **¿El integrador tiene que ser PSP/agregador?** No: no existe figura de integrador. El nodo solo llama la API con las credenciales del comercio; ante Ualá el comercio es el único usuario. Que los TyC permitan cargar esas credenciales en software de un tercero sigue **(NC)** (la cláusula "claves intransferibles" habla de la clave de la cuenta).

### 5. Transferencias y QR

- La API de Cobros Online v2 **solo cubre órdenes de checkout**: no hay endpoint ni webhook de transferencias entrantes al CVU/alias de la cuenta Ualá ni API de QR. [índice v2: https://developers.ualabis.com.ar/v2]
- QR interoperable a nombre del comercio: se genera desde la app, con aviso push en la app; **sin API ni webhook** (NC que exista privado). [https://www.ualabis.com.ar/qr]
- Conciliar transferencias por monto con centavos: **imposible por API** hoy. Queda el flujo manual de `cobros.md` §1.

---

## Qué cambió respecto de cobros.md

1. **Mobbex Dev Connect no exige partner ni aprobación de Mobbex** en la doc: el operador crea una "aplicación" autoservicio en el devportal y con solo `x-api-key` lanza el connect. Lo que sí necesita es **una cuenta/usuario Mobbex propia** (si esa entidad tiene que pasar el alta de "días hábiles" para poder crear la app: NC). Sube de "Alto-medio (NC)" a **Alto-medio confirmado**.
2. **Mobbex sí devuelve parcial por API** (`POST /operations/{id}/refund` con `total`, desde el día siguiente), pero **no** para QR interoperable, DEBIN ni efectivo. cobros.md decía solo "por API".
3. **Mobbex: sandbox público** con credenciales publicadas en la doc; Ualá Bis **no** (hace falta cuenta).
4. **Mobbex webhook: confirmado sin firma y sin reintentos documentados** (antes "firma no documentada").
5. **Ualá Bis devoluciones:** la API v2 admite hasta **90 días** (no 30) y `amount` obligatorio (parcial: NC). El "solo total, 24 h–30 d" venía de Tiendanube, otro canal.
6. **Ualá Bis reintentos:** 4 intentos en total (antes "hasta 3 más", mismo dato, precisado).
7. **Ualá Bis: PSPCP N.º 33.549 confirmado** en legales de Ualá. Mobbex: PSP "Agrupador", no PSPCP, número NC.
8. **Ualá Bis QR con tarjeta** tiene tasas distintas (2,9%/4,9%) del 0,8% de dinero en cuenta: cobros.md decía "QR 0,8%" sin distinguir.
9. **Estados Mobbex** son numéricos (200 = paga, 300 = acreditado…), no `approved/rejected`; la spec del adaptador tiene que mapearlos.

## Datos (NC)

- Mobbex: vida/revocación del access token de Dev Connect; reintentos del webhook; si crear una app en devportal exige entidad ya validada; requisitos de alta (monotributo/persona física); comisión de transferencia/DEBIN/efectivo; texto completo de los TyC (404 en las dos URLs); número de registro BCRA; si el webhook cubre QR/DEBIN igual que tarjeta (inferido).
- Ualá Bis: devolución parcial; vencimiento del `checkout_link`; parámetros que agrega a `callback_success/fail`; intervalo entre reintentos; requisitos exactos para persona física; cláusula TyC sobre credenciales API en software de terceros; versión 2026 de los TyC de Ualá Bis (solo se leyó la de 2023).

## Fuentes (consultadas 2026-09-25)

- https://mobbex.dev/dev-connect
- https://mobbex.dev/checkout
- https://mobbex.dev/webhooks
- https://mobbex.dev/primeros-pasos · https://mobbex.dev/en-first-steps
- https://mobbex.dev/devoluciones
- https://mobbex.dev/consulta-de-operaciones-y-childs
- https://mobbex.dev/codigos-de-estado
- https://mobbex.dev/listado-de-medios-de-pago
- https://ayuda.mobbex.com/credenciales-para-integracion-a-traves-de-api
- https://ayuda.mobbex.com/crear-usuarios
- https://ayuda.mobbex.com/terminos-y-condiciones-de-mobbex-agrupador (404; snippets de buscador, TyC act. 2025-03-13)
- https://ayuda.mobbex.com/es/terminos-y-condiciones · https://www.mobbex.com/terminos (404; snippets)
- https://www.mobbex.com/planes/ · https://www.mobbex.com/faq/
- https://github.com/mobbexco/nodejs
- https://developers.ualabis.com.ar/ · /v2 · /v2/ambientes
- https://developers.ualabis.com.ar/v2/authentication/create
- https://developers.ualabis.com.ar/v2/orders/create · /v2/orders/get · /v2/orders/create/webhook
- https://developers.ualabis.com.ar/v2/refunds/create · /v2/refunds/create/webhook
- https://www.ualabis.com.ar/link-de-pago · /qr · /apicheckout · /preguntas-frecuentes
- https://www.uala.com.ar/legales · https://www.uala.com.ar/empresas
- https://ayuda.tiendanube.com/es_ES/uala/preguntas-frecuentes-sobre-uala-bis (act. 2026-02-11)
- TyC Ualá Bis 2023-05-05: https://assets.ctfassets.net/t5yal6u1wvnw/1EsrWh7PHBXHsiLdMpJShT/c6985c60a366656085b5e09d66af3052/_05.05.23__-_TyC_UalaBis.docx.pdf
- BCRA registro PSP: https://www.bcra.gob.ar/SistemasFinancierosYdePagos/Proveedores-servicios-de-pago-ofrecen-cuentas-de-pago.asp

---

## Veredicto (MVP en 3 días)

1. **Ualá Bis es la alternativa rápida a MP.** Es la única sin nada que registrar para el operador: el comercio genera `client_id/secret` en su app, el nodo pide un token de 24 h, crea el checkout con `external_reference = pedido_id` y `notification_url`, y confirma con `GET /orders/{uuid}` en `APPROVED`. Son 4 endpoints y ninguna decisión pendiente.
2. **Mobbex es mejor producto** (Dev Connect tipo OAuth, 1,9%/2,6% vs 4,9%, más medios: DEBIN, QR, efectivo, devolución parcial), pero exige que **cada operador de nodo tenga cuenta Mobbex y una app** y tiene puntos NC (vida del token, reintentos, si la entidad del operador debe estar validada). Con alta de "días hábiles", no cierra en 3 días.
3. Los dos van **sin firma de webhook** y con re-consulta obligatoria; los dos dejan contracargos en el comercio y no exigen que el integrador sea PSP.
4. Costo: Ualá Bis es cara en tarjeta (4,9%) pero acredita al instante y con QR/dinero en cuenta 0,8%; el comercio elige.
5. Recomendación: **lanzar el 28/09 con MP + Ualá Bis** (mismo adaptador "credenciales del comercio"), y Mobbex como tercer proveedor cuando un operador confirme el alta de su app.
