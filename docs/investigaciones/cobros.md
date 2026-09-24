# Cómo cobra un comercio en Vereda (Argentina)

Investigación del 2026-09-23. Solo fuentes públicas: sin cuentas, sin credenciales, sin escribirle a nadie.
Es una investigación, no una norma de la spec. No es asesoramiento legal ni contable.

Cada dato lleva su fuente y su fecha en los anexos:

- [`cobros/transferencia.md`](cobros/transferencia.md): transferir desde el mismo teléfono, BCRA, comprobante, confirmación.
- [`cobros/pasarelas-1.md`](cobros/pasarelas-1.md): Mercado Pago, MODO, Ualá Bis, Naranja X.
- [`cobros/pasarelas-2.md`](cobros/pasarelas-2.md): Mobbex, Payway, Getnet, Fiserv, dLocal, Stripe, Nave, viüMi y otros.
- [`cobros/legal.md`](cobros/legal.md): BCRA/PSP, ARCA e Ingresos Brutos, consumidor, UIF, datos personales.

Todo lo que dice **(NC)** no está confirmado en una fuente oficial.

Los principios no cambian: Vereda nunca toca la plata, el cobro va directo a la cuenta del comercio, no hay comisión, y el efectivo es un diferencial.

---

## 1. Transferencia desde el mismo teléfono

### Qué hay hoy de verdad

- **No existe un link oficial** que abra Mercado Pago, MODO, Ualá, Naranja X, Brubank, Personal Pay, Cuenta DNI ni ningún banco con el alias y el monto ya cargados.
  - Revisamos los archivos públicos con los que iOS decide qué links abren cada app.
  - Mercado Pago tiene rutas `/money-transfer*` y `/money-request*`. MODO tiene `/send-modo*` y `/collect-modo*`. Naranja X y Brubank aceptan cualquier ruta de su dominio.
  - Ninguna tiene parámetros documentados. Usarlas sería ingeniería inversa que puede romperse cualquier día. **(NC)**
- **El QR interoperable no se puede usar como link.** Ninguna norma define un link que abra cualquier billetera, y iOS no tiene selector de billetera: cada link abre la app de su dominio.
  - Además, generar un QR de cobro es la función de "aceptador". Exige ser una entidad regulada por el BCRA y agente de recaudación.
  - Si el nodo generara QR propios, podría quedar encuadrado como PSP (`legal.md` §1.4).
- **La norma ya prevé lo ideal, pero todavía no llegó a las apps.** El BCRA creó la **"solicitud de pago activa"** (Com. "A" 8399, vigente desde el 13/02/2026). El comercio la emite al alias del comprador con el monto, y el banco o la billetera del comprador se la muestra para aceptar.
  - Los bancos y billeteras "deberán estar en condiciones" de mostrarla, pero no encontramos ninguna app que lo haga todavía. **(NC)**
  - La emite un aceptador regulado, o sea el PSP del comercio, nunca el nodo.
  - La Com. "A" 8477 (09/09/2026) la extiende a usos no comerciales.
- **El link de pago de Mercado Pago sí abre la app en el mismo teléfono**, con el monto cargado. Pero no es una transferencia: es un cobro de MP con tarjeta o dinero en cuenta, con comisión de MP. Entra en la sección de pasarelas (§3).

Conclusión: hoy lo más cómodo sin depender de nadie es **copiar el alias, abrir la app que la persona elige y tener el monto siempre a la vista**. La vuelta del comprobante y la confirmación del comercio se pueden hacer mucho más cómodas que hoy.

### Flujo recomendado (comprador, iPhone)

1. **Elige "Transferencia"** al confirmar el carrito. Nace el cobro `pendiente` con alias, titular, monto, referencia y vencimiento (ya está en la spec).
2. **Ve una pantalla con tres cosas:** el monto grande, el titular ("tu banco te tiene que mostrar a Juan Pérez") y un botón **"Copiar alias y abrir mi banco"**.
   - La primera vez elige su app de entre las que tiene instaladas: MP, MODO, Ualá, Naranja X, Brubank o su banco. La app la recuerda.
   - El toque copia el alias y abre esa app en su inicio, por link universal. No hace falta parámetro ni permiso de nadie.
3. **Mientras está en su banco, arriba ve el recordatorio.** Vereda muestra una **Live Activity** en la Dynamic Island y en la pantalla bloqueada: "Transferí $12.500 a lahuerta.mp · Juan Pérez · vence 14:15".
   - Así no tiene que volver a Vereda para acordarse del monto ni del titular.
   - Si toca la Live Activity, vuelve a Vereda y el monto queda copiado para pegar.
   - Esto es propio de iOS y no depende de ninguna billetera.
4. **Transfiere.** Su banco le muestra el titular real antes de confirmar. Eso ya está previsto en `identidad-y-verificacion.md`.
5. **Manda el comprobante de una de tres formas:**
   - **a) Compartir.** En la pantalla de éxito del banco toca "Compartir comprobante" y elige **Vereda**. Una Share Extension recibe la imagen, el PDF o el texto.
     - Con Vision (OCR en el teléfono) lee el monto, la fecha y hora, el destino (alias/CVU), el nombre de quien paga, el número de operación y el ID Coelsa (22 caracteres).
     - Lo compara con el pedido pendiente ("coincide: $12.500 a lahuerta.mp").
   - **b) Captura.** Saca una captura y al volver a Vereda la app le ofrece usarla. Hace la misma lectura.
   - **c) A mano.** Toca "Ya transferí", con el número de operación optativo.
   - Qué comparte cada app (PDF, imagen o texto) hay que probarlo en un iPhone real. **(NC)**
6. **Al volver a Vereda** (con la app en primer plano después de haber abierto el banco), la pantalla ya dice "¿Ya transferiste?". Pregunta si el titular coincidía (`titular_coincide`) y declara la transferencia (`POST /pedidos/{id}/transferencia`).
   - **La imagen nunca sale del teléfono.** Al nodo le llegan solo los datos leídos, porque el nodo no guarda archivos.

### Flujo recomendado (comercio, sin entrar al home banking)

El nodo nunca ve la plata y no puede confirmar por el comercio. Lo que sí puede es que confirmar sea **un toque con toda la información a la vista**:

1. **Pedido "por confirmar" en la app del comercio** con todo lo que declaró el comprador: monto, nombre de quien pagó (leído del comprobante), hora, número de operación e ID Coelsa, y si el OCR coincidió.
   - El comercio compara con el aviso "Recibiste $12.500 de María G." que ya le llega a su teléfono desde su billetera o banco, y toca **"Ya vi la plata"**.
   - No necesita abrir el home banking: alcanza con la notificación que ya recibe.
2. **Política del comercio** (nueva, configurable y pública en su ficha): **"empezar a preparar con el comprobante"**.
   - Si el OCR coincide en monto y destino, el pedido puede pasar a preparación antes de la confirmación. El cobro sigue `pendiente` hasta que el comercio confirma.
   - Es decisión del comercio. La spec propone un default (esperar la confirmación) y no obliga.
3. **Confirmación automática opcional si el comercio cobra en Mercado Pago.**
   - Con su cuenta conectada (§3), el nodo buscaría la transferencia entrante en `/v1/payments/search` o recibiría el webhook `payment`, y la marcaría "vista por MP".
   - **(NC):** que las transferencias al CVU disparen ese aviso lo dice solo un repo público. Hay que probarlo con una transferencia real antes de prometerlo.
4. **Android (futuro):** una app de comercio en Android puede leer las notificaciones "Recibiste $X" de cualquier billetera, con permiso que el comercio activa en Ajustes, y proponer la confirmación sola. **En iOS no es posible**: no hay API para leer notificaciones de otras apps.
5. **Truco de centavos (decisión de Leo).** Descontar unos centavos únicos por pedido ($12.499,63) haría que cada transferencia se identifique sola por el monto. Es muy útil para confirmar en lote. Como contra, el precio "no redondo" puede confundir y el comercio absorbe menos de $1.

---

## 2. Efectivo

No hace falta nada nuevo: `en_mano`, `cobrado_en_mano` al entregar, rendición firmada del repartidor al comercio, y retiro con código.

Hay un hueco chico: **"¿Con cuánto pagás?"**. Hoy la spec no tiene cómo decirle al repartidor que lleve cambio.
- Propuesta: un campo optativo `paga_con` (monto) en el pago en efectivo, visible para quien cobra en mano.
- Es barato y le ahorra al repartidor el "no tengo cambio" en la puerta.

---

## 3. Pasarela: tarjeta, débito y QR en la cuenta del propio comercio

### Comparativa

Costos de lista del 2026-09-23, **sin IVA**; el detalle está en los anexos.

| Proveedor | Cómo se conecta la cuenta del comercio | Fee de plataforma 0 | Costo para el comercio | Acreditación | Alta | Aviso "pagado" al nodo | Devoluciones / contracargos | Encaje |
|---|---|---|---|---|---|---|---|---|
| **Mercado Pago** | **OAuth** (el comercio autoriza; refresh token de 6 meses) o su propio token | Sí: se omite `marketplace_fee` (opcional según la doc; "0 explícito" NC) | Online: 6,29% al momento · 4,39% 10 d · 3,39% 18 d · 1,49% 35 d. QR: 0,8% dinero en cuenta · 1,35% débito · 5,99% crédito | Al momento a 35 d, lo elige el comercio | Cuenta MP (la mayoría ya la tiene); KYC nivel 6 para split | Webhook **firmado** (HMAC `x-signature`), con reintentos | Devolución por API, total o parcial, ≤180 d. El contracargo lo absorbe el vendedor | **Alto** |
| **Ualá Bis** | El comercio genera sus credenciales en la app y las carga en el nodo | Sí (no existe fee) | Checkout 4,9% cualquier medio (una sola fuente); QR 0,8% (0% los primeros 3 meses) | Instantánea | Autoservicio en la app, persona física o jurídica, 24–48 h | Webhook por orden, **sin firma** (hay que re-consultar) | Solo devolución total, 24 h a 30 d. Contracargo al comercio | **Alto-medio** |
| **Mobbex** | **Dev Connect** (tipo OAuth): el comercio se loguea y el nodo recibe su token | Sí (sin `split`) | Débito 1,9%, crédito 2,6% | Débito 2 d hábiles, crédito 10–18 d hábiles, QR al instante | Online, "unos días hábiles" | Webhook por checkout; firma no documentada | Por API. Contracargo al comercio (TyC, snippet) | **Alto-medio** (NC: si cada nodo necesita ser partner aprobado) |
| **MODO** | Usuario y contraseña por comercio; requiere gateway (Payway/Fiserv/Getnet/Line) | Sí | MODO 0%; paga el arancel del gateway (Payway: débito 2%, crédito 3%) | Según el gateway | Pesada: Payway + inscripción en IIBB + formulario (48 h) | Webhook **firmado** (JWS) | API; contracargo vía el adquirente | Medio |
| **Payway** | Claves del comercio cargadas en el nodo | Sí | 1% de plataforma + débito 2%, crédito 3% (débito 0% monotributo) | Débito 1 d hábil, crédito 5–18 d hábiles | Adhesión y número de establecimiento | `notifications_url` (formato y firma NC) | Total o parcial por API | Medio |
| **Nave (Galicia)** | Client ID/Secret pedidos por mail | Sí | Transferencia/QR 0,8% después de 3 meses; tarjeta NC | Instantánea | Por Galicia | Sí (plugin) | Devolución manual | Medio |
| **Getnet** | Credenciales por ejecutivo de ventas | Sí | Crédito 2% (8 d hábiles) a 7,28% (inmediata); débito 1–1,53%; QR 0,8% | Según plazo; inmediata solo con cuenta Santander | Ejecutivo de ventas | Sí (usuario y contraseña) | Hay API de contracargos | Medio-bajo |
| **viüMi (Macro)** | client_id/secret | Sí | No publicado | NC | Contacto comercial | NC | NC | Bajo-medio |
| **Naranja X** | NC (portal caído el 2026-09-23) | NC | Crédito 1,8% + financiación; dinero en cuenta 0,8% (NC) | En el día / 2 / 14 / 60 d (NC) | NC | NC | NC | Pendiente |
| **Fiserv / Clover** | Link de pago sin API; la API e-commerce de Clover es solo para Norteamérica | — | Aranceles Posnet | Débito 48 h, crédito 10 d hábiles | Ser comercio Posnet/Clover | NC | NC | Bajo |
| **dLocal** | Keys por cuenta; "For Platforms" custodia fondos | — | Tarifario internacional | 7 d + 48 h | KYC en 2 pasos | Sí | Devolución con fee | Bajo (cobros desde el exterior) |
| **Stripe** | — | — | — | — | **No abre cuentas en Argentina** | — | — | Nulo |
| Pago Nube, BIND PSP, Pomelo | Solo Tiendanube / infraestructura para fintechs | — | — | — | — | — | — | Nulo |

Transversal a todos:

- **El contracargo siempre lo absorbe el comercio** (o su adquirente) en todos los casos confirmados. Con fee 0, Vereda no pone plata en una devolución de MP.
- **Nunca confiar solo en el webhook.** El nodo re-consulta el pago por API con las credenciales del comercio antes de marcarlo pagado. Varios proveedores no firman sus avisos.
- **iOS:** el checkout web del proveedor se abre en `SFSafariViewController` y vuelve por link universal. MODO abre por deep link. No hace falta SDK nativo ni tocar datos de tarjeta, así que PCI queda fuera.
- **App Store:** son bienes físicos, así que no aplica la compra dentro de la app de Apple (guideline 3.1.3(e)). **(NC)**

### Recomendación: cuál primero

1. **Mercado Pago primero.** Es el único con OAuth oficial y webhook firmado, y además cubre online, QR y Point. La mayoría de los comercios ya tiene cuenta: el alta es "tocá Conectar". El comercio elige el plazo y paga la comisión de MP; Vereda no cobra nada.
   - **Tensión con la marca:** MP es del grupo al que Vereda se opone.
   - Mi lectura: es la cuenta del comercio, no la de Vereda. Detrás de la interfaz no es más que un proveedor. La app nunca lo nombra como "el" medio: el comercio lo elige.
   - **Decisión de Leo.**
2. **Ualá Bis segundo.** Alta autoservicio, acreditación instantánea, sin concepto de fee. Es la alternativa no-MP para quien no quiere MP. Contra: es caro en tarjeta (4,9%) y el webhook no tiene firma.
3. **Mobbex tercero**, si confirma que Dev Connect no exige aprobar a cada operador de nodo como partner. Es el más barato en tarjeta de los que se conectan en un clic.
4. **Adaptador genérico "credenciales del comercio"** para Payway, Nave, Getnet y MODO, a demanda. Todos se integran igual: credenciales, orden con `external_reference = pedido_id` y aviso al nodo.

**Detalle del modelo descentralizado.** OAuth necesita una "app" registrada en el proveedor. En Vereda no hay empresa central, así que **cada operador de nodo registra la suya**. Es un paso del operador, no del comercio. La alternativa universal, sin app del operador, es que el comercio pegue su propio token. La spec admite las dos: `conexion: oauth | credenciales`.

---

## 4. Qué cambia, por partes

### Spec (protocolo-vereda)

| Cambio | Tamaño |
|---|---|
| `pago.transferencia.comprobante` pasa de texto libre a un objeto optativo: `operacion`, `coelsa_id`, `monto_leido`, `pagador_nombre` (lo ve solo el comercio), `destino_coincide`, `leido_en`. Se sigue aceptando el texto actual. | Chico |
| `paga_con` optativo en el pago en efectivo | Chico |
| Política del comercio `preparar_con_comprobante` (bool, pública en la ficha, default `false`) | Chico |
| `pago.confirmado_por`: `comercio` \| `psp` (aviso verificado del proveedor) \| `repartidor`. Deja claro quién vio la plata. | Chico |
| **Cobradores del comercio.** `privado.cuenta_cobro` pasa a una lista `cobradores[]`: `{tipo: transferencia\|psp, proveedor: "<id libre>", metodos: [tarjeta, qr_interoperable, …], conexion: oauth\|credenciales, estado: conectado\|vencido\|revocado, referencia}`.<br>• Los ids de proveedor son strings libres, con una tabla orientativa en docs, sin enum cerrado: la spec no se ata a nadie.<br>• La ficha pública sigue mostrando solo `medios_cobro`. | Mediano |
| `POST/DELETE /comercios/{id}/cobradores` (conectar y desconectar) y las herramientas MCP equivalentes para el agente del comercio. `link_pago`, `psp` y `psp_referencia` ya existen en `pago.json`. | Mediano |
| Doc `docs/cobro-con-psp.md`. Reglas:<br>• el nodo crea el cobro en la cuenta del comercio;<br>• solo marca pagado después de re-consultar al proveedor;<br>• nunca guarda datos de tarjeta;<br>• devoluciones con `concepto: devolucion`;<br>• el contracargo es entre el comercio y su proveedor. | Mediano |
| Eventos `pago.reembolsado` y `pago.contracargo` (informativos) | Chico |

### Nodo (vereda-nodo)

| Cambio | Tamaño |
|---|---|
| Aceptar y validar el comprobante estructurado; mostrárselo al comercio y no a otros | Chico |
| `paga_con` y `preparar_con_comprobante` | Chico |
| Interfaz `Cobrador` (crear cobro, consultar, reembolsar, verificar aviso) más el registro de cobradores del comercio | Mediano |
| Adaptador **Mercado Pago**: OAuth del operador, refresh con rotación atómica, preferencia de Checkout Pro y orden QR, webhook firmado → re-consulta → `confirmado`, devoluciones | Grande |
| Secretos del comercio **cifrados en reposo**, con el mínimo de permisos y revocables desde la app | Mediano |
| Adaptador Ualá Bis (credenciales + re-consulta, porque no firma) | Mediano |
| Probar con una transferencia real si MP avisa las transferencias entrantes al CVU | Chico (prueba) |

### App iOS (vereda-app)

Pantallas, flujos y copy los decide Leo; lo que sigue es qué hace falta, no cómo se ve.

| Cambio | Tamaño |
|---|---|
| Pantalla de transferencia: monto, titular, "Copiar alias y abrir mi banco", elección de app recordada, volver con "¿Ya transferiste?" | Chico |
| **Live Activity** con monto, alias, titular y vencimiento mientras el cobro está pendiente | Mediano |
| **Share Extension** + lectura del comprobante con Vision en el teléfono; la captura como alternativa | Mediano |
| Comercio: lista "por confirmar" con los datos del comprobante y "Ya vi la plata" en un toque | Chico |
| Comercio: "Conectar Mercado Pago" (`ASWebAuthenticationSession`) y estado del cobrador | Mediano |
| Comprador: pagar con tarjeta en el checkout del proveedor (`SFSafariViewController` + link universal de vuelta) | Mediano |

Orden sugerido: primero lo **chico de transferencia** (spec, nodo y app), porque mejora lo que ya existe sin depender de nadie. Después Share Extension y Live Activity. La pasarela va después, y **solo cuando Leo decida el primer proveedor**.

---

## 5. Riesgos

- **Legales (`legal.md`).** Con el modelo actual (efectivo, transferencia al alias, PSP del comercio con fee 0), ni el proyecto ni el operador quedarían registrados en el BCRA, ni serían sujetos obligados ante la UIF ni agentes de Ingresos Brutos. Es **lectura de las normas, sin dictamen oficial**.
  - Líneas rojas: **no generar QR ni links de pago propios** (podría ser "aceptación"), **no ordenar transferencias desde la cuenta del comprador** ("iniciación") y **nunca cobrar y repartir** (PSP, UIF, agente de IIBB y responsabilidad solidaria).
- **Comisión = responsabilidad.** En *Almirón* (CNCom Sala B, 13/03/2026), Mercado Libre respondió solidariamente porque cobraba comisión y procesaba el pago. En *Juárez* (Sala D, 18/06/2024) no respondió porque solo alojaba el aviso. Fee 0 y "el comercio es el proveedor" en los términos del nodo ponen a Vereda del lado *Juárez*.
- **Aportes al operador.** Si retribuyen un servicio, pueden ser ingresos gravados (monotributo, factura, IIBB) y sufrir retenciones en su cuenta. Lo tiene que ver un contador.
- **Tokens en el nodo.** Un token OAuth permite crear cobros y devoluciones en la cuenta del comercio. Si se filtra, el daño es real: cifrar, permisos mínimos, revocación desde la app y aviso al comercio.
- **Ingeniería inversa de links.** Usar rutas no documentadas de las billeteras para precargar el monto puede romperse sin aviso. No lo recomiendo.
- **Fraude de comprobante.** Una captura se falsifica fácil. Por eso el comprobante nunca confirma: solo el comercio (o el aviso verificado del proveedor) confirma. `preparar_con_comprobante` es un riesgo que elige el comercio.
- **Dependencia y marca.** Empezar por MP da adopción inmediata a costa de coherencia de marca. Mitigación: interfaz neutra y un segundo proveedor pronto.
- **Datos sin confirmar** que pueden cambiar la recomendación:
  - si MP acepta fee 0 de forma explícita en Split;
  - si Mobbex exige aprobar a cada operador como partner;
  - Naranja X completo;
  - qué comparte cada billetera al tocar "Compartir comprobante".

**Consultas profesionales antes de la pasarela real:**
- abogado fintech: opinión escrita sobre "alias + OAuth + webhook";
- abogado de consumo: términos del nodo;
- contador: aportes al operador.

---

## 6. Recomendación para Leo

1. **Transferencia hoy:** no hay forma oficial de abrir el banco con el monto cargado. Lo más cómodo es "copiar alias y abrir tu banco" más el recordatorio del monto arriba de la pantalla mientras transfiere. El comprobante vuelve compartiéndolo a Vereda, que lo lee solo en el teléfono.
2. **Para el comercio:** confirmar es un toque, con nombre, monto y número de operación a la vista para compararlos con el aviso que ya le llega del banco. Además, si quiere, puede empezar a preparar con el comprobante.
3. **Pasarela:** Mercado Pago primero (OAuth, aviso firmado, la mayoría ya lo tiene), con Ualá Bis como alternativa no-MP. Vereda no cobra nada y los contracargos son del comercio con su proveedor. Tenés que decidir si MP va primero por la tensión de marca.
4. **Líneas rojas legales:** nunca QR ni links de pago propios, nunca ordenar transferencias, nunca tocar plata. Así el nodo queda fuera de BCRA, UIF y agente de impuestos. Antes de la pasarela real, conviene una opinión escrita de un abogado.
5. **Efectivo:** está completo. Solo falta "¿con cuánto pagás?" para que el repartidor lleve cambio.
