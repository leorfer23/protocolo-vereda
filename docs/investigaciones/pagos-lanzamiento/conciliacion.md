# Conciliación de transferencias por "centavos únicos por pedido"

Investigación de solo lectura, consultado **2026-09-25**. Sin cuentas, sin gasto, sin escribirle a nadie. No es asesoramiento legal.
Construye sobre `docs/investigaciones/cobros.md` §1 y `cobros/transferencia.md` §3–4: no repite lo que ya está ahí (universal links, Share Extension, OCR, webhooks MP), va a lo que pide el brief.
**(NC)** = no confirmado en fuente oficial. `[n]` = fuente en la lista final.

**Lo esencial en tres líneas.** El truco existe y está probado a escala (Indonesia lo usa hace más de diez años en todo el e-commerce, con 1–3 dígitos *sumados*). En Argentina conviene hacerlo **restando** 1–99 centavos: es un descuento, no choca con "el precio exhibido es el total final" (Res. 4/2025) ni con el art. 9 bis de la Ley 22.802. El monto es más robusto que el "motivo" de la transferencia (que no está normado y no llega igual a todos). Hoy no hay ninguna billetera que muestre la "solicitud de pago activa" del BCRA; a mediano plazo sí la reemplaza, pero la emite un aceptador regulado, no el nodo.

---

## 1. Cómo lo hacen otros

**Indonesia, "kode unik" (el caso más parecido).** Tokopedia, Bukalapak y cientos de tiendas suman al total un código de **1 a 3 dígitos** (Rp 1–999) cuando el comprador elige transferencia bancaria. Tokopedia: "si el total es Rp 100.000, genera un código de 3 dígitos… el monto a pagar queda en Rp 100.535; después de verificar, los Rp 535 vuelven al saldo Tokopedia" `[1]`. DomaiNesia lo define como "una variación de 1 a 3 dígitos que aparece en el total de pago" y aclara que desde 2022 lo renombró "administration fee" (Rp 1–1.000) `[2]`. Qué pasa cuando el comprador se equivoca: caso Bukalapak 2020, debía transferir Rp 50.904 y mandó Rp 50.094; la plata quedó "verificada por otra transacción" y no se devolvió `[3]`. Lecciones: (a) el rango de 3 dígitos aguanta ~1000 pedidos abiertos por cuenta receptora; (b) **sumar** obliga a devolver o justificar el extra (Tokopedia lo devuelve a saldo, Bukalapak no, y eso generó quejas); (c) un monto "casi igual" de otro pedido es el riesgo real: hay que evitar colisiones por cercanía, no solo por igualdad.

**Stripe (bank transfer / customer balance).** Concilia por (1) referencia en el memo, (2) si no hay, "el pedido abierto más viejo cuyo monto coincide exactamente", (3) combinaciones de hasta 5 facturas. De menos: la factura queda abierta hasta cubrir el total (o se configura un umbral de "write-off"). De más: aplica al pago abierto y el excedente queda en saldo del cliente; si no se concilia en 75 días lo devuelve `[4]`. Modelo de tolerancias listo para copiar.

**Pix (Brasil).** No usa centavos: el QR/"copia e cola" lleva un `txid` que el PSP del pagador "debe retransmitir intacto" y que el receptor usa para conciliar; en QR estático hasta 25 caracteres, en QR dinámico 26–35 `[5]`. Es lo que la solicitud de pago activa del BCRA promete para acá (§4).

**SEPA.** Referencia estructurada ISO 11649 ("RF" + 2 dígitos verificadores + hasta 21 caracteres, mod-97), pensada justamente para conciliar automáticamente; su uso depende del banco `[6]`. Argentina no tiene equivalente normado (§2).

**Cripto.** El patrón estándar es una dirección única por pedido, no un monto único `[7]`. El "monto único en satoshis" se usó en tiendas chicas pero no encontré una implementación conocida documentada. **(NC)**

**Boletos / Rapipago / Pago Fácil.** Conciliación por código de barras con número de referencia impreso; no aplican al caso (el nodo no puede emitir códigos de cobro sin ser aceptador, `legal.md` §1.4). No profundicé.

**¿Restar o sumar en Argentina? Restar.**
- **Res. 4/2025 (SIC, BO 17/01/2025)**, que reemplazó a la Res. 7/2002 de exhibición de precios: art. 2 a) precios en pesos; art. 2 b) "El precio exhibido corresponderá al importe total y final que deba abonar el consumidor"; art. 3 admite exhibición "en formato físico y/o digital". No dice nada de centavos ni de fracciones `[8]` `[9]`. **Sumar** centavos es cobrar más que el precio exhibido, salvo que el precio exhibido ya sea el monto con centavos (lo que rompe el catálogo). **Restar** es un descuento: el comprador paga menos que el total exhibido y nadie puede reclamar.
- **Ley 22.802 art. 9 bis (Ley 25.954, BO 03/12/2004)**: "diferencias menores a cinco (5) centavos… la diferencia será siempre a favor del consumidor" `[10]`. Está pensado para el vuelto en efectivo, pero marca el criterio; la Corte Suprema lo confirmó en agosto de 2026 (*ACYMA c/ Farmacia S.A.*): "el vuelto incompleto debe ser redondeado siempre a favor del consumidor" y que "la retención de centavos… [no] constituye una afectación trivial" `[11]` (fuente periodística, no leí el fallo) **(NC)**.
- Conclusión: restar es legal y simple; sumar es defendible solo si se muestra como cargo desde antes de confirmar, y aun así es la parte más quejada del modelo indonesio. Costo para el comercio: hasta $0,99 por pedido.

---

## 2. Qué trae una transferencia inmediata (Coelsa / Transferencias 3.0)

Texto ordenado "SNP – Transferencias – Normas complementarias", versión al 08/09/2026 (última Com. "A" 8477) `[12]`:
- **2.7**: "Cada transferencia inmediata tendrá un identificador único estandarizado entre los múltiples esquemas de pago". En la práctica es el **ID Coelsa, 22 caracteres alfanuméricos**, "generado automáticamente al realizar una transferencia" y usado por todas las entidades para rastrearla `[13]` (ayuda de Lemon, no BCRA).
- **2.4**: la base de cuentas que consultan los esquemas contiene "titulares", "CBU, CVU y alias", "moneda", "CUIT, CUIL, CDI u otros". Por eso el comprador ve el titular del comercio y el comercio ve nombre y CUIT/CUIL del ordenante.
- **2.5**: la receptora confirma o rechaza a la originante y esta notifica "en forma inmediata al cliente ordenante". **2.9**: la receptora "sólo podrá rechazar" por falla en la base de cuentas; **no existe rechazo por monto**: si el comprador transfiere mal, la plata entra igual.
- **Concepto / motivo**: el TO **no define** ningún campo libre de referencia ni su longitud (busqué "motivo", "concepto", "leyenda", "referencia" en el texto: solo aparecen como palabras comunes). Lo que existe es un "concepto" enumerado (varios, alquileres, cuotas, etc.) más una "descripción" libre cuya longitud varía por entidad: un medio cita 12 caracteres en un banco y "casi inexistente" en otros `[14]` **(NC)**. Que la descripción libre le llegue al receptor y con qué texto depende de cada app; en MP aparece en el comprobante como "motivo" **(NC)**.
- Datos que llegan por ID Coelsa en una API bancaria (ejemplo BDC Conecta, ya citado en `transferencia.md`): titular, CUIT, banco, alias, CBU del ordenante `[15]`.
- Plazo: la inmediata se acredita en línea; el "15 segundos" que citan medios para la A 8399 no lo encontré en el TO **(NC)**.

**Veredicto.** El "motivo" no sirve como referencia de pedido: no está normado, el comprador tiene que escribirlo a mano, se trunca y no todas las apps lo muestran al receptor. **El monto es lo único que viaja intacto en todo esquema** (el comprador lo pega y el sistema no lo puede alterar). El ID Coelsa sirve para *auditar* después (comprobante ↔ movimiento), no para identificar el pedido antes.

---

## 3. Cómo se entera el comercio sin abrir el home banking

- **Push de las billeteras.** Brubank, oficial: "podés recibir transferencias de quien quieras, enterarte cuándo llegó y cuándo fue vista" y "te avisamos de toda actividad que se haga en tu cuenta" `[16]`. MP: se configuran push/mail/SMS/WhatsApp desde "Comunicaciones" (ayuda MX; la AR devolvió 403) `[17]`; hay quejas públicas que muestran el push "fulano me transfirió dinero" `[18]` **(NC el texto exacto y si trae centavos)**. Ualá: la página oficial de transferencias solo dice "enviá y recibí plata… gratis y en el acto" `[19]`; el aviso existe según usuarios **(NC)**. Que el push traiga el monto **con centavos** hay que verificarlo app por app en un teléfono real **(NC)**; Android permite leer el texto completo de la notificación aunque el banner lo recorte.
- **Android: `NotificationListenerService`.** Permiso `BIND_NOTIFICATION_LISTENER_SERVICE`, el usuario lo activa a mano en Ajustes › Acceso a notificaciones (ya citado en `transferencia.md` §4). Política de Play: las páginas "Permissions and APIs that Access Sensitive Information" (vigente y preview) **no mencionan** el notification listener; rige la regla general: "sólo permisos… necesarios para implementar funciones actuales… promocionadas en la ficha", pedidos en contexto y con prominent disclosure `[20]` `[21]`. Play Protect sí lo trata como uno de cuatro permisos sensibles y avisa al instalar **apps sideloaded** (no las de Play): usos aceptados "relay a wearables, agregadores de notificaciones, launchers/widgets"; prohibidos "acceder al contenido sin consentimiento explícito" `[22]`. Riesgo: una app de comercio que lee avisos bancarios puede caer en revisión manual; mitiga: función opcional, activada por el comercio, filtrada a paquetes de billeteras/bancos, sin subir el texto crudo al nodo (solo monto, nombre, hora). Si el nodo es software libre y se distribuye por APK/F-Droid, el aviso de Play Protect es lo que verá el comercio.
- **iOS: no.** Sin API para leer notificaciones de otras apps (ya en `transferencia.md`).
- **Con Mercado Pago como cuenta receptora.** No hay tópico de webhook "transferencia recibida" (ya en `transferencia.md` §4). `GET /v1/payments/search` (OAuth del comercio) filtra por `range`/`begin_date`/`end_date`, `sort`, `criteria`, `external_reference`, y devuelve `id`, `status`, `transaction_amount`, `date_approved`, `payment_type_id`, `operation_type`, `payer` (nombre/identificación). Que las transferencias al CVU aparezcan ahí como `payment_type_id = account_money` / `operation_type = money_transfer` y disparen el webhook `payment` **lo afirma sólo un repo de terceros, que además usa exactamente el truco de centavos ($45.000 → $45.000,37)** `[23]` **(NC)**. Hoy no pude abrir la referencia oficial del endpoint (404/403 desde acá) **(NC)**. Lo oficial que sí existe: el reporte "Todas las transacciones" con `PAYMENT_METHOD_TYPE = bank_transfer` y `PAYER_NAME`, pero diario/semanal, no en tiempo real (ya citado) `[24]`.

---

## 4. Solicitudes de pago del BCRA: estado al 2026-09-25

- **Norma**: 3.2.4.2 (Com. "A" 8399, vigente 13/02/2026): la solicitud activa "es emitida por un potencial cliente receptor de los fondos –el comercio– hacia un… alias o CBU/CVU"; al aceptarla el consumidor "remite una instrucción de pago… con la información de monto y cuenta de destino… así como los identificadores que permitan su seguimiento". Bancos y PSPCP "deberán estar en condiciones de poner a consideración de sus clientes las solicitudes de pago activas que reciban". **2.10** (Com. "A" 8477, vigente 09/09/2026): "podrán ser utilizadas para transferencias inmediatas sin fines comerciales" `[12]`.
- **Implementación visible**: ninguna. Las novedades públicas de Coelsa en 2026 son pagos NFC interoperables (abril) y COELSA.PAY para empresas `[25]`; no encontré ninguna billetera o banco que anuncie "recibí una solicitud de pago y la acepto" ni un formato de emisión abierto. **(NC)** La 8477 lo que agrega es P2P ("pedir plata" a un alias entre personas), lo que sugiere que las billeteras podrían exponerlo a cualquier usuario, incluido un comercio chico, sin ser aceptador. **(NC)**
- **¿Reemplaza el truco?** A mediano plazo sí: la solicitud lleva monto, destino e "identificadores de seguimiento" (el txid argentino). Pero la solicitud *comercial* la emite un aceptador (PSP regulado + agente de recaudación) y llega por su API; el nodo nunca la va a emitir. El camino para Vereda cuando exista: (a) el comercio la emite desde su propia billetera/PSP y el nodo solo guarda el identificador; (b) o el comprador usa la variante P2P de su propia app. Hasta entonces, el monto único es lo único que funciona con **cualquier** banco y billetera sin permiso de nadie.

---

## 5. Diseño recomendado para Vereda

**Algoritmo de asignación.**
1. `monto_base` = total del pedido en pesos (entero o con centavos del catálogo). `ajuste_centavos` ∈ [1, 99], **se resta**: `monto_a_transferir = monto_base − ajuste/100`. Nunca terminar en `,00` (el comprador que redondea es el caso de ambigüedad).
2. Unicidad **por cuenta receptora del comercio** (alias/CVU) entre los cobros por transferencia `pendientes` cuya ventana no venció, y unicidad del **monto final**, no del ajuste (dos pedidos con bases distintas pueden caer en el mismo monto final si el catálogo ya trae centavos). Regla: los montos finales abiertos del mismo comercio difieren entre sí en al menos $0,02 y ninguno coincide con el `monto_base` redondeado de otro pedido abierto (cubre al que transfiere "$12.500 redondo").
3. Elegir el ajuste al azar entre los libres (no secuencial): un comercio de barrio raramente tiene >99 transferencias abiertas a la vez; si se agotan, ampliar a un segundo rango restando también $1–$9 (999 combinaciones) o pedir al comprador el comprobante como hoy. Al vencer la ventana o confirmarse el cobro, el monto se libera.
4. Ventana: la misma `vencimiento` del cobro pendiente que ya tiene la spec (p. ej. 30–60 min). Un monto liberado no se reasigna hasta pasadas 24 h para no confundir una transferencia tardía con un pedido nuevo.

**Campos para la spec** (objeto `cobro` con `medio = transferencia`): `monto_base`, `ajuste_centavos`, `monto_a_transferir` (lo único que el comprador ve grande y copia), `ventana_hasta`, `tolerancia` (ver abajo); en `POST /pedidos/{id}/transferencia`: `monto_declarado`, `ordenante_nombre`, `id_coelsa` (optativo); en la confirmación del comercio: `monto_recibido`, `ordenante_nombre_visto`, `origen_confirmacion ∈ {manual, notificacion_android, api_psp}`. Estados: `pendiente → declarada → confirmada | con_diferencia | vencida`.

**Tolerancias.** Transferencia **de más** (`monto_recibido ≥ monto_a_transferir`, típico: pagó el redondo): se acepta y se confirma; si hay dos pedidos abiertos con el mismo redondo, el nodo muestra ambos y el comercio elige por nombre del ordenante. **De menos**: queda `con_diferencia`; el comercio decide (aceptar, pedir el resto, cancelar) — igual que Stripe, que no cierra la factura hasta cubrirla salvo umbral configurado `[4]`. Nunca rechazar: la red no permite rechazar por monto (2.9) y la plata ya está en la cuenta del comercio.

**Confirmación en un toque.** La tarjeta del pedido muestra **"$12.499,63 · María G. · 14:07"**; el push de su billetera dice lo mismo; toca **"Ya vi la plata"**. Mejoras por plataforma: Android, con acceso a notificaciones activado por el comercio, la app detecta "Recibiste $12.499,63 de María G." y propone la confirmación con un toque (nunca confirma sola: el comercio sigue siendo quien afirma que cobró); MP conectado por OAuth, polling de `/v1/payments/search` cada 30–60 s durante la ventana y marca "vista por MP" **(NC hasta probar con una transferencia real)**.

**Exhibición al comprador.** Mostrar el total del pedido ($12.500) y debajo "Transferí exactamente **$12.499,63** — te descontamos $0,37 para reconocer tu pago". El monto grande, el copiable y el de la Live Activity es siempre el de centavos. Así el precio exhibido nunca es menor que lo pagado (Res. 4/2025 art. 2 b) `[8]`.

**Riesgos legales del nodo.** El nodo solo calcula un número y lo muestra: no ordena transferencias (no es iniciación 1.4.4), no genera QR ni links de cobro (no es aceptación 1.4.3), no recibe fondos ni los reparte (no PSPCP/agregador) — misma lectura que `legal.md` §1.4. El descuento lo otorga el comercio, no el nodo; conviene que la política "centavos únicos" sea una configuración del comercio y figure en su ficha. Datos: nombre del ordenante = dato personal del comprador que ya está en el pedido; en Android, lo leído de notificaciones no sale del teléfono más allá de monto/nombre/hora. Riesgo residual: un comercio que confía en el push y no verifica puede ser víctima de un comprobante trucho; por eso la confirmación siempre nombra al ordenante y el monto exacto.

---

## Datos (NC)

- Rango exacto y política actual de Tokopedia/Bukalapak (fuentes: blog oficial de Tokopedia vía resumen de búsqueda, DomaiNesia y una carta de lector; no leí un documento técnico).
- Contenido del fallo CSJN 2026 sobre redondeo: tomado de una nota periodística.
- Longitud y llegada al receptor del campo "descripción/motivo" por entidad; que el TO no lo norme lo verifiqué por búsqueda en el PDF.
- Texto exacto y centavos en los push de MP, Ualá, Brubank y bancos; MP AR ayuda devolvió 403.
- Campos y filtros de `GET /v1/payments/search` (la referencia oficial no abrió hoy) y que las transferencias al CVU aparezcan ahí o disparen el webhook `payment`: solo un repo de terceros `[23]`.
- Que ninguna billetera muestre hoy solicitudes de pago activas: ausencia de evidencia, no evidencia de ausencia.
- Política de Play sobre notification listener: no está en la lista de permisos restringidos; la revisión manual queda a criterio de Google.

## Fuentes (consultadas 2026-09-25)

1. Tokopedia, "Mengapa harus transfer sesuai kode unik" — https://www.tokopedia.com/blog/manfaat-kode-unik-untuk-keamanan-pembayaran/ (la página no cargó por timeout; datos del extracto de búsqueda)
2. DomaiNesia, "Pembayaran kode unik" — https://www.domainesia.com/berita/pembayaran-kode-unik/
3. Media Konsumen, "Salah kode unik transfer di Bukalapak, uang tidak kembali", 28/09/2020 — https://mediakonsumen.com/2020/09/28/surat-pembaca/salah-kode-unik-transfer-di-bukalapak-uang-tidak-kembali
4. Stripe Docs, "Bank transfer" (invoicing): reconciliation, under/overpayments — https://docs.stripe.com/invoicing/bank-transfer
5. BCB, "Manual de Padrões para Iniciação do Pix" v2.10.0, §2.6.2 y campo txid — https://www.bcb.gov.br/content/estabilidadefinanceira/pix/Regulamento_Pix/II_ManualdePadroesparaIniciacaodoPix.pdf
6. EPC, "Guidance on Creditor Reference ISO 11649" (EPC142-08) — https://www.europeanpaymentscouncil.eu/sites/default/files/KB/files/EPC142-08-EPC-Guidance-on-Creditor-Reference-ISO-Std.pdf ; Wikipedia "Creditor Reference" — https://en.wikipedia.org/wiki/Creditor_Reference
7. Bitcoin.org Developer Guide, "Payment processing" — https://developer.bitcoin.org/devguide/payment_processing.html
8. Res. 4/2025 SIC, texto — https://www.argentina.gob.ar/normativa/nacional/norma-408455/texto ; BO 17/01/2025 — https://www.boletinoficial.gob.ar/detalleAviso/primera/319787/20250117
9. Res. 7/2002 (abrogada por Res. 4/2025 art. 6) — https://servicios.infoleg.gob.ar/infolegInternet/verNorma.do?id=74899
10. Ley 25.954 (art. 9 bis Ley 22.802), texto — https://www.argentina.gob.ar/normativa/nacional/ley-25954-101627/texto
11. ElSello, "La Corte dictó un fallo que obliga a redondear los vueltos a favor del consumidor", 20/08/2026 — https://elsello.info/2026/08/20/la-corte-dicto-un-fallo-que-obliga-a-redondear-los-vueltos-a-favor-del-consumidor/
12. BCRA, TO "SNP – Transferencias – Normas complementarias" (última Com. "A" 8477) — https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-snp-tr-nc.pdf
13. Lemon, "¿Qué es Coelsa y el ID Coelsa?", 2023 — https://help.lemon.me/es/articles/6868460-que-es-coelsa-y-por-que-es-importante-el-id-coelsa
14. iProfesional, "Transferencia bancaria: concepto y descripción" — https://www.iprofesional.com/finanzas/390443-transferencia-bancaria-por-que-es-util-completar-los-items-sobre-concepto-y-descripcion (truncada; dato de 12 caracteres tomado del extracto)
15. BDC Conecta, "Coelsa additional data" — https://docs.bdcconecta.com/Transferencias/coelsa_aditional_data
16. Brubank, home — https://www.brubank.com/
17. Mercado Pago (MX), "¿Cómo configurar las comunicaciones?" — https://www.mercadopago.com.mx/ayuda/17222 (la versión AR devolvió 403)
18. TuQuejaSuma, queja sobre notificaciones de transferencias en MP — https://tuquejasuma.com/mercado-pago/reclamos/no-me-llega-la-plata-que-me-transfieren-pero-las-notificacion-si-me-llegan-pero
19. Ualá, "Transferencias" — https://www.uala.com.ar/transferencias
20. Google Play Console Help, "Permissions and APIs that Access Sensitive Information" — https://support.google.com/googleplay/android-developer/answer/16558241
21. Google Play Console Help, "Preview: Permissions and APIs that Access Sensitive Information" — https://support.google.com/googleplay/android-developer/answer/16909972
22. Google, "Developer Guidance for Google Play Protect Warnings" — https://developers.google.com/android/play-protect/warning-dev-guidance
23. GitHub 7b4wg2pgzp-eng/pagos (tercero: centavos únicos + webhook MP) — https://github.com/7b4wg2pgzp-eng/pagos
24. Mercado Pago Developers, reporte "Todas las transacciones", campos — https://www.mercadopago.com.ar/developers/es/docs/checkout-pro/additional-content/reports/account-money/report-fields
25. Ámbito, "Una nueva modalidad de pago para billeteras virtuales le compite al QR" (NFC Coelsa), 05/04/2026 — https://www.ambito.com/economia/una-nueva-modalidad-pago-billeteras-virtuales-le-compite-al-qr-n6262209 ; RoadShow, "Se lanzó COELSA.PAY" — https://www.roadshow.com.ar/se-lanzo-coelsa-pay-la-evolucion-inteligente-de-los-cobros-digitales-para-empresas-y-profesionales/
26. Android Developers, NotificationListenerService — https://developer.android.com/reference/android/service/notification/NotificationListenerService
