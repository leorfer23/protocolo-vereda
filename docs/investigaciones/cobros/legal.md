# Vereda y los pagos: marco legal argentino (investigación)

> Investigación pública de solo lectura, 2026-09-23. **No es asesoramiento legal ni contable.**
> Formato: cada dato lleva `[fuente: URL, fecha de la norma / fecha consultada]`. "Consultado 2026-09-23" = fecha en que se leyó la fuente.
> ✅ = lo leí en el texto de la norma oficial · 🟡 = lo tomé de un estudio jurídico o medio especializado, sin leer el texto oficial · ❓ = es inferencia mía o quedó sin confirmar.

Supuestos del modelo Vereda: (a) el proyecto es software libre, sin persona jurídica; (b) un "nodo" lo puede operar cualquiera, sea persona humana o jurídica; (c) ni Vereda ni el nodo reciben, retienen ni liquidan fondos del comprador; (d) el nodo guarda como mucho el alias del comercio, que no es un dato privado porque se le muestra al comprador para transferir; (e) cuando se sume el PSP, será la cuenta propia del comercio conectada por OAuth, con fee de plataforma 0, y el nodo solo recibe el webhook "pagado".

---

## 1. BCRA: Proveedores de Servicios de Pago (PSP)

### 1.1 Texto vigente
- El texto ordenado (TO) "Proveedores de servicios de pago" vigente tiene como **última comunicación incorporada la "A" 8454 (14/07/2026)**. Esa comunicación incorpora lo dispuesto por las Com. "A" 8411 y "A" 8432 (30/04/2026). ✅ [fuente: https://www.bcra.gob.ar/archivos/Pdfs/Texord/t-snp-psp.pdf, TO al 14/07/2026, consultado 2026-09-23] [fuente: https://www.bcra.gob.ar/archivos/Pdfs/comytexord/A8454.pdf, 14/07/2026]
- **Com. "A" 6859 (09/01/2020)** creó la figura. Desde ahí se consideran PSP las "personas jurídicas que, sin ser entidades financieras, cumplan al menos una función dentro de un esquema de pago minorista […] tal como ofrecer cuentas de pago". También exige que el 100% de los fondos de los clientes esté depositado en cuentas a la vista. ✅ [fuente: https://www.bcra.gob.ar/archivos/Pdfs/comytexord/A6859.pdf, 09/01/2020]
- **Com. "A" 7328 (12/07/2021)** permitió cuentas de pago con más de un titular. Para billeteras fijó exigencias de conocimiento del cliente (KYC), de que la cuenta vinculada sea del mismo titular y de autenticación en dos pasos (2FA). 🟡 [fuente: https://blogdelcontador.com.ar/comunicacion-bcra-a-7328-2021/, 2021; https://www.marval.com/publicacion/nuevas-medidas-del-banco-central-buscan-reforzar-la-seguridad-en-pagos-electronicos-14025?lang=en]
- **Com. "A" 8432 (30/04/2026, vigencia 06/05/2026)** hizo tres cosas. Creó el "PSPCP como Servicio": cuentas de pago que se ofrecen a los clientes de un tercero a través de la interfaz de ese tercero. Endureció las exclusiones vinculadas a UIF y RePET. Y habilitó la baja de oficio por 180 días de inactividad. El plazo de adecuación vence el 03/08/2026. ✅ para el texto de 1.4.1.1 · 🟡 para plazos y vigencia [fuente: https://www.bcra.gob.ar/archivos/Pdfs/comytexord/A8432.pdf, 30/04/2026; https://allende.com/fintech/el-banco-central-introduce-nuevas-regulaciones-sobre-proveedores-de-servicios-de-pago-05-14-2026/, 14/05/2026]

### 1.2 Definiciones (TO, sección 1) ✅ [fuente: t-snp-psp.pdf, TO al 14/07/2026]
- **1.2.1 PSP**: "personas jurídicas que, sin ser entidades financieras, cumplan al menos una función dentro de un esquema de pago minorista".
- **1.2.2 Esquema de pago**: reglas que hacen funcionar un instrumento de pago "cuando intervienen al menos tres partes: un ordenante, un receptor y uno o más entidades financieras o PSP".
- **1.4 Funciones**:
  - 1.4.1 provisión de cuentas (PSPCP), con su variante 1.4.1.1 "PSPCP como Servicio";
  - 1.4.2 administración (1.4.2.2 administrador QR);
  - **1.4.3 aceptación**: "adherir comercios a esquemas de pago con transferencia. Comprende […] facilitar los mecanismos para iniciar los pagos, transmitir la información de la orden de pago al administrador […] y […] confirmar las operaciones";
  - **1.4.4 iniciación**: "remitir una instrucción de pago válida a petición de un cliente ordenante al proveedor de una cuenta […] o emisor de instrumento de pago";
  - 1.4.5 redes de cajeros; 1.4.6 redes de transferencias;
  - **1.4.7 adquirencia**: adherir comercios a esquemas con tarjetas;
  - **1.4.8 agregación o subadquirencia**: "proporcionar a los comercios el acceso a esquemas de pago que el agregador ha contratado con uno o más adquirentes, usando […] el número identificador (ID de comercio) del agregador […], que actúa como cliente receptor de los fondos";
  - 1.4.9 cobranza extrabancaria.
- **2.1 Registro obligatorio** ante la SEFyC para quienes cumplan las funciones 1.4.1, 1.4.2.2, 1.4.3, **1.4.4 "sólo si prestarán el servicio de billetera digital"**, 1.4.5, 1.4.6, 1.4.7, 1.4.8 y 1.4.9. La inscripción se tramita con clave fiscal de la **persona jurídica** en ARCA (2.2), y el objeto social tiene que prever explícitamente la actividad de pagos (2.2.1).
- **1.5 Sanciones**: arts. 41 y 42 de la Ley de Entidades Financieras.

### 1.3 Agregadores, facilitadores e iniciadores: qué número corresponde a qué
- Los **agregadores/subadquirentes** (1.4.8) y los **aceptadores** (1.4.3) entraron con la **Com. "A" 7769 (18/05/2023)**, que exigió inscribirse antes de empezar a operar, o antes del 01/10/2023 si ya operaban. ✅ [fuente: https://www.bcra.gob.ar/archivos/Pdfs/comytexord/A7769.pdf, 18/05/2023; BO: https://www.boletinoficial.gob.ar/detalleAviso/primera/288315/20230614]
- ⚠️ **La Com. "A" 7825 no trata sobre agregadores.** Es del 24/08/2023 y obliga a los PSPCP a trasladar a sus clientes el rendimiento de los fondos. 🟡 [fuente: https://www.bcra.gob.ar/Pdfs/comytexord/A7825.pdf; BO: https://www.boletinoficial.gob.ar/detalleAviso/primera/293055/20230829, 29/08/2023]
- La figura del **iniciador existe**: es la función 1.4.4, y las comunicaciones la mencionan como "PSP que cumplen la función de iniciación" o "PSI". Nace con la **Com. "A" 7462 (24/02/2022)**, que también define "billetera digital" y crea el Registro de billeteras digitales interoperables. ✅ [fuente: https://www.bcra.gob.ar/archivos/Pdfs/comytexord/A7462.pdf, 24/02/2022]
- ⚠️ **La Com. "A" 7516 (19/05/2022) no trata sobre iniciadores.** Es una norma de "Exterior y cambios" (posiciones NCM). ✅ [fuente: https://www.bcra.gob.ar/archivos/Pdfs/comytexord/A7516.pdf, 19/05/2022]
- La palabra "facilitador" no aparece en el TO como figura regulada. La que corresponde es "agregador". ✅ (búsqueda en el texto del TO)

### 1.4 ¿Tiene que registrarse Vereda o un nodo?
| Conducta del software | Función del TO | ¿Registro? |
|---|---|---|
| Mostrar el alias/CVU del comercio para que el comprador transfiera desde su propio banco o billetera | Ninguna: el nodo no remite instrucciones a ninguna cuenta ni adhiere comercios a un esquema | ❓ **No**, por lectura directa de 1.2.1 y 1.4 |
| Redirigir al checkout del **PSP del propio comercio** (OAuth, sin fee) | La adhesión del comercio la hace el PSP (MP es aceptador, adquirente o agregador). El nodo no es "cliente receptor de fondos" | ❓ **No**, con los mismos reparos. Hay que evitar ser el que "adhiere comercios" en nombre propio |
| Recibir un webhook "pagado" | Recibir una notificación no es transmitir una orden de pago ni confirmar la operación ante el esquema | ❓ **No** |
| Generar QR interoperables propios o links de pago propios | Puede encuadrar en **1.4.3 aceptación** ("facilitar los mecanismos para iniciar los pagos") | ⚠️ Riesgo: **sí** |
| Ordenar la transferencia desde la cuenta del comprador (open banking o API bancaria) | **1.4.4 iniciación**. Solo se registra si además presta el servicio de billetera digital | ⚠️ Zona gris |
| Cobrar en una cuenta propia y después repartir | **1.4.8 agregación** con tarjeta, o PSPCP; y con transferencias, posible intermediación no autorizada | 🔴 **Sí** |

- Dato estructural: el PSP se define como **persona jurídica** (1.2.1) y el registro exige estatuto y CUIT de persona jurídica (2.2). Un proyecto sin personería, o un nodo operado por una persona humana, **no puede** ser PSP. Eso no da permiso para hacer funciones de PSP: significa que, si alguna vez hiciera falta, sería imposible cumplir. ✅ texto / ❓ consecuencia.

---

## 2. Impuestos

### 2.1 Nacional (ARCA)
- **RG 4622/2019 (BO 30/10/2019)**: régimen de retención de IVA y Ganancias para "sujetos que administren servicios electrónicos de pagos y/o cobranzas por cuenta y orden de terceros". 🟡 [fuente: https://www.boletinoficial.gob.ar/detalleAviso/primera/220221/20191030, 30/10/2019]
- **La RG 5554/2024 (20/08/2024) derogó** las RG 140/1998, 4011/2017 y 4622/2019, con efecto desde el **01/09/2024**. Hoy no hay retención nacional de IVA ni de Ganancias sobre cobros electrónicos. ✅ [fuente: https://servicioscf.afip.gob.ar/publico/sitio/contenido/novedad/ver.aspx?id=4255, 20/08/2024]
- **RG 2616/2009**: ❓ **no la verifiqué.** Según lo que recuerdo, es un régimen de retención de IVA y Ganancias a sujetos que no acreditan su inscripción, que se aplica en operaciones con "no categorizados". No me consta que tenga una disposición para marketplaces. Hay que confirmarlo con un contador.
- IVA sobre servicios digitales (Ley 27.430, prestadores del exterior): **no aplica** a Vereda si el servicio se presta desde el país y sin cobro. ❓
- **Donaciones**: la **RG 3166/2011** crea un régimen de información para donantes y donatarios que, según entiendo, está pensado para entidades exentas. 🟡 [fuente: https://www.afip.gob.ar/orgSocCiv/beneficios-impositivos/regimen-de-informacion-de-donaciones.asp]

### 2.2 Ingresos Brutos: regímenes para plataformas
- **SIRTAC** (Comisión Arbitral, **RG CA 2/2019**; hoy dentro del ordenamiento de la RG CA 18/2022) retiene IIBB sobre las liquidaciones de tarjetas y las de "**concentradores y/o agrupadores de pago (Administradores de Sistemas de Pagos)**". 🟡 [fuente: https://www.ca.gob.ar/sirtac, consultado 2026-09-23]
- **PBA (ARBA) RN 28/2022 (BO 07/12/2022)** adhirió al SIRTAC. Obliga a retener a quienes hacen "recaudaciones, rendiciones periódicas y/o liquidaciones correspondientes a sistemas de pago mediante concentradores y/o agrupadores de pago". Para operaciones por "plataformas online […] aplicaciones" fija una alícuota del 3% a los sujetos que no están en el padrón. 🟡 (resumen del CPCEPBA) [fuente: https://www.arba.gov.ar/Intranet/Legislacion/Normas/Resoluciones/2022/Res028-22.pdf, 07/12/2022; resumen: https://www.cpba.com.ar/noticias/item/download/2808_5487aeeefbfe748b91de107c2ad31e27, 06/10/2023]
- **PBA RN 25/2025 (BO 08/09/2025, aplica desde 01/11/2025)**: régimen **SIRCUPA** sobre acreditaciones en cuentas de pago de PSPCP. El agente es el **PSP**. 🟡 [fuente: https://www.arba.gov.ar/Intranet/Legislacion/Normas/Resoluciones/2025/Res025-2025.pdf; https://bruchoufunes.com/arba-establece-nuevo-regimen-de-recaudacion-sobre-cuentas-de-pago/]
- **SIRCREB**: recauda IIBB sobre acreditaciones en cuentas bancarias. El agente es el banco, no la plataforma. ❓ No lo verifiqué en esta sesión.
- **CABA (AGIP) Res. 352/AGIP/2022**, Anexo I, Sección VI "Plataformas de pagos", **art. 91**: están obligados a retener "quienes prestan servicios tendientes a facilitar la gestión, administración o procesamiento de pagos, **a fin de recibir o efectuar pagos por cuenta y orden de terceros**", por plataformas, apps o interfaces. El art. 92 obliga a inscribirse a quien encuadre aunque no esté en el Anexo III. El art. 95 define "operaciones reiteradas" como más de 25 por mes y más de $100.000 (texto según Res. 148/AGIP/2026, vigente desde 01/05/2026). El art. 97 excluye de la base las **propinas** identificadas (DNU 731/2024). El art. 76 inc. b excluye como sujetos pasibles a los propios administradores de pagos. ✅ [fuente: https://boletinoficialpdf.buenosaires.gob.ar/util/imagen.php?idn=633050&idf=1, Res. del 22/11/2022 con textos modificados a 2026, consultado 2026-09-23; ficha: https://www.agip.gob.ar/normativa/resoluciones/2022/agip/resolucion-n-352agip-2022]

**¿Un marketplace que NO cobra ni intermedia fondos queda designado agente?**
- En CABA la condición es "recibir o efectuar pagos por cuenta y orden de terceros". Si el nodo no toca fondos, no encuadra en el art. 91 ✅. El que retiene es el PSP del comercio, por ejemplo MP.
- En PBA y SIRTAC el agente es quien liquida o rinde fondos, es decir, concentradores, agrupadores y PSPCP. El nodo no liquida nada. ❓ Por lectura directa: **no queda designado**.
- ❓ **No encontré** ningún régimen vigente, ni en CABA ni en PBA, que designe agente a un marketplace **solo por publicar ofertas** sin intervenir en el cobro. Sí existen regímenes de **información** en algunas provincias. No los relevé en detalle y los dejo como pendientes (ver "No confirmado").
- Modelo "PSP con split y fee": el fee lo acredita el PSP (MP `marketplace_fee` / `application_fee`) en la cuenta de la plataforma. Los fondos del comercio los liquida MP, no la plataforma. 🟡 [fuente: https://www.mercadopago.com.ar/developers/en/docs/split-payments/integration-configuration/create-configuration, consultado 2026-09-23]. Aun así, la plataforma pasa a tener **ingresos gravados** propios (IIBB, Ganancias e IVA según su categoría) y queda más cerca de la "cadena de comercialización" (ver §3).

### 2.3 El operador del nodo que recibe aportes
- Si el aporte es una **donación real** (sin contraprestación, sin habitualidad ni fin de lucro), en principio no está gravado. Si **retribuye un servicio** (mantener el nodo), puede tratarse como ingreso por servicios: **monotributo** (o régimen general), **factura electrónica** e IIBB en la provincia. Hay zonas grises; por ejemplo, agradecer públicamente a quien aporta puede leerse como contraprestación. 🟡 [fuente: https://ar.andersen.com/bajo-la-lupa-que-impuestos-deben-pagar-los-influencers-por-publicidad-canjes-y-cafecitos-prensa-el-economista/; https://www.lanacion.com.ar/economia/influencers-y-streamers-que-impuestos-se-pagan-por-los-ingresos-que-genera-la-actividad-nid09122024/, 09/12/2024]
- Hay un riesgo práctico. Si los aportes entran a una **cuenta de pago** (MP, Ualá) o a un banco, pueden sufrir retenciones de SIRCUPA o SIRCREB, o activar perfiles de habitualidad (en CABA, más de 25 operaciones y más de $100.000 por mes, art. 95) si el operador no está inscripto en IIBB. ❓ Esto aplica a la plataforma de pagos, no a Vereda, pero le pega al operador.

---

## 3. Defensa del consumidor y responsabilidad de la plataforma

- **Ley 24.240, art. 40**: si el daño resulta del vicio o riesgo de la cosa o de la prestación del servicio, responden de forma solidaria y objetiva "el productor, el fabricante, el importador, el distribuidor, el proveedor, el vendedor y quien haya puesto su marca" y el transportista. 🟡 texto de memoria, sin releer [fuente: https://servicios.infoleg.gob.ar/infolegInternet/anexos/0-4999/638/texact.htm]
- **Jurisprudencia**: el criterio que se repite es **"rol activo" frente a "hosting neutral"**.
  - *Almirón, Omar A. c/ Mercado Libre SRL y otros*, **CNCom Sala B, 13/03/2026**: ML **responde de forma solidaria** porque promovió el contrato, cobró por Mercado Pago, entregó por Mercado Envíos, ofrecía "Compra Protegida" y se quedó con **~13% de comisión**. 🟡 [fuente: https://aldiaargentina.microjuris.com/2026/04/27/fallos-compra-online-fallida-mercado-libre-responde-solidariamente-por-un-tv-defectuoso-vendido-en-su-plataforma-junto-al-vendedor-y-fabricante-por-no-considerarlo-un-simple-intermediario-confir/, 27/04/2026]
  - *Juárez c/ Mercado Libre SRL*, **CNCom Sala D, 18/06/2024** (MJ-JU-M-152787-AR): ML **no responde** en clasificados de autos, porque solo había un botón "Preguntar", no se podía cerrar la venta en el sitio y la negociación siguió por mail. La responsabilidad nace si la plataforma participa en la negociación, cobra comisión por transacción o controla el cobro. 🟡 [fuente: https://aldiaargentina.microjuris.com/2025/01/07/fallos-comercio-electronico-mercado-libre-no-debe-responder-por-incumplimiento-contractual-si-solo-pudo-comportarse-con-relacion-a-la-oferta-de-venta-del-automotor-que-intereso-al-actor-como-un-simp/, 07/01/2025]
  - En sede administrativa, CABA: *Mercado Libre SRL c/ DGDyPC* (2018), "ML no es ajeno a la relación de consumo". 🟡 [fuente: https://ijudicial.gob.ar/2018/mercado-libre-no-es-ajeno-a-la-relacion-de-consumo-ni-a-la-ley-de-defensa-del-consumidor/]
  - Lo que sale de esto para Vereda ❓: sin comisión, sin cobro, sin logística propia y sin garantía, Vereda queda del lado "Juárez". Pero si el nodo **arma el pedido y el checkout**, eso lo acerca a "promover el contrato". Conviene documentarlo en los términos: el comercio es el proveedor, el nodo es solo un canal técnico.
- **Res. SCI 424/2020 (BO 05/10/2020)**: exige un "**botón de arrepentimiento**" visible, sin registro previo, que permita revocar la compra en 10 días corridos (art. 34 de la LDC y art. 1110 del CCyC). ✅ [fuente: https://servicios.infoleg.gob.ar/infolegInternet/anexos/340000-344999/342869/norma.htm; BO: https://www.boletinoficial.gob.ar/detalleAviso/primera/235729/20201005, 05/10/2020]. ❓ Según el art. 1116 inc. b del CCyC, la revocación **no procede** para bienes que "puedan deteriorarse con rapidez" (comida). Aun así, el botón sería exigible para el resto de los rubros. La pregunta de quién tiene que ponerlo (el comercio o el nodo) queda para el abogado.
- **Ley 25.065 de Tarjetas de Crédito** (sanc. 07/12/1998): el art. 26 permite al titular **cuestionar el resumen dentro de 30 días**, el art. 27 obliga al emisor a responder en 15 días (60 si la operación es del exterior), el art. 28 le impide suspender la tarjeta mientras dure el reclamo y el art. 29 regula el procedimiento. El art. 37 fija las obligaciones del comercio (verificar identidad, pedir autorización, no recargar el precio). 🟡 [fuente: https://servicios.infoleg.gob.ar/infolegInternet/anexos/55000-59999/55556/texact.htm, consultado 2026-09-23]
  - ❓ El contracargo le pega al **comercio**, que es el cliente del adquirente o agregador (MP). El nodo no es parte. Con transferencias inmediatas no hay contracargo: el reclamo se canaliza por el marco BCRA de transferencias y el de fraude.

---

## 4. Prevención de lavado (UIF)
- La **Ley 27.739 (BO 15/03/2024)** reemplazó el art. 20 de la Ley 25.246. El inc. 5 dice: "Los emisores, operadores y proveedores de servicios de cobros y/o pagos". 🟡 [fuente: https://servicios.infoleg.gob.ar/infolegInternet/anexos/60000-64999/62977/texact.htm, consultado 2026-09-23]
- La **Res. UIF 200/2024 (19/12/2024)** reglamenta a los sujetos obligados: emisores de tarjetas; cobranza extrabancaria; **PSPCP, aceptadores, adquirentes y agregadores**; proveedores no financieros de crédito. **Excluye a los PSP iniciadores** cuando solo remiten una instrucción de pago válida. 🟡 [fuente: https://allende.com/bancario/nueva-reglamentacion-de-la-uif-aplicable-a-proveedores-de-servicios-de-cobros-y-o-pagos-12-20-2024/, 20/12/2024; https://trivia.consejo.org.ar/ficha/523494-resolucion_uif_2002024]
- **Nodo que no toca fondos**: no encuadra en ninguna de esas categorías. ❓ No sería sujeto obligado. Sí lo son el PSP del comercio y el banco.

---

## 5. Datos personales (Ley 25.326)
- **Ley 25.326** (sanc. 04/10/2000). Las obligaciones que importan acá: consentimiento e información (arts. 5-6), seguridad y confidencialidad (arts. 9-10), inscripción de las bases en el registro de la AAIP (art. 21) y derechos de acceso, rectificación y supresión (arts. 14-16). 🟡 [fuente: https://servicios.infoleg.gob.ar/infolegInternet/anexos/60000-64999/64790/texact.htm]. Medidas de seguridad recomendadas: **Res. AAIP 47/2018**. ❓ No la verifiqué.
- ❓ El **alias** de un comercio que es **persona humana** es un dato personal: identifica a una persona y el banco muestra el titular al transferir. Aun así, es un dato que el propio titular publica para cobrar, y no es un dato sensible. Si el nodo **no guarda CBU completo, tarjetas ni tokens de pago**, **no queda alcanzado por PCI-DSS** y el riesgo baja mucho. Los **tokens OAuth** del PSP del comercio **sí son credenciales críticas**: guardarlos cifrados, con el mínimo de permisos y con rotación (MP los da con validez de 6 meses). 🟡 [fuente: https://www.mercadopago.com.ar/developers/en/docs/split-payments/integration-configuration/create-configuration]
- Los datos del comprador (nombre, dirección, teléfono para la entrega) son datos personales comunes. El nodo es "responsable de la base": necesita política de privacidad, finalidad acotada y plazo de borrado. ❓

---

## 6. Tabla final: modelo de cobro × obligaciones

> Leyenda: **P** = Vereda (proyecto de software libre, sin personería) · **N** = operador del nodo · **C** = comercio. Todo lo de la tabla es **inferencia** a partir de las fuentes citadas arriba (❓ salvo donde el propio texto lo dice).

| Modelo | P (proyecto) | N (operador del nodo) | C (comercio) |
|---|---|---|---|
| **Efectivo** | Nada regulatorio. Licencia y disclaimers | Sin BCRA/UIF/agente IIBB. Consumidor: rol de canal. Datos: Ley 25.326 por los datos de comprador y comercio | Factura (monotributo o RI), IIBB, LDC completa como proveedor, precios y seguridad del producto |
| **Transferencia directa al alias/CVU del comercio** | Igual | Igual. No generar QR ni links propios (evita 1.4.3 aceptación). Guardar solo el alias | Lo anterior + SIRCREB o SIRCUPA sobre sus acreditaciones. Conciliar el pago él mismo |
| **PSP del comercio vía OAuth, fee 0, webhook "pagado"** | Código: no guardar datos de tarjeta, tokens cifrados | Sin registro BCRA ❓, sin UIF ❓, sin agente IIBB ❓. Custodiar tokens OAuth (Ley 25.326 art. 9). Hay que redactar términos y política de privacidad | Contrato con el PSP. Retenciones IIBB que aplique el PSP (SIRTAC o art. 91 AGIP). Contracargos (Ley 25.065). Botón de arrepentimiento si corresponde |
| **PSP con split y fee de plataforma** | Si P cobra el fee, P necesita **personería**: tendría ingresos gravados | Si N cobra el fee: **ingresos gravados** (monotributo/RI, IIBB, factura al comercio por el fee). No es agregador mientras MP liquide ❓. **Mayor riesgo de solidaridad del art. 40** (criterio *Almirón*: comisión) | Igual que el anterior + factura o recibe comprobante por el fee |
| **Vereda/nodo cobra y reparte** | 🔴 Imposible sin persona jurídica | 🔴 **PSP a registrar** (1.4.8 agregador o PSPCP) → persona jurídica con objeto social, **sujeto obligado UIF** (Res. 200/2024), **agente de retención IIBB** (art. 91 AGIP, SIRTAC PBA), guarda de fondos, régimen informativo, **responsabilidad solidaria** casi segura. Con transferencias, además, riesgo de intermediación financiera no autorizada ❓ | Sufre retenciones del nodo. Relación contractual con el nodo |

---

## No confirmado
1. Que "mostrar el alias" y "redirigir por OAuth" **no sean** "aceptación" (1.4.3) ni "iniciación" (1.4.4) es interpretación mía. **No hay** dictamen del BCRA ni FAQ sobre software que no toca fondos. Además, el verbo "facilitar los mecanismos para iniciar los pagos" es amplio.
2. El texto exacto y el alcance actual de la **RG 2616/2009** (no la leí).
3. Si existe algún **régimen provincial de información** para marketplaces o intermediarios digitales en PBA, CABA, Córdoba o Santa Fe que alcance a un sitio que solo publica ofertas. No lo encontré, pero la búsqueda no fue exhaustiva, sobre todo fuera de CABA y PBA.
4. El texto literal del art. 40 de la LDC y de la Ley 25.326: lo cito de memoria con el enlace de InfoLEG, sin haberlo releído en esta sesión.
5. Los datos de la Res. UIF 200/2024 y de los fallos *Almirón* y *Juárez* salen de estudios jurídicos y de Microjuris, no del texto oficial ni de la sentencia.
6. El tratamiento en Ganancias e IIBB de los aportes voluntarios al operador depende de hechos concretos (habitualidad, contraprestación).
7. Si el botón de arrepentimiento (Res. 424/2020) le toca al nodo, al comercio o a los dos, y cómo convive con la excepción por perecederos.
8. **Persona humana como operadora**: no puede ser PSP. Si un nodo operado por una persona humana cobrara fondos de terceros, el encuadre (¿ejercicio irregular?, ¿Ley 21.526?) no está verificado.

## Consultar con abogado/contador
- **Abogado fintech/BCRA**: una opinión escrita de que el flujo "alias + OAuth al PSP del comercio + webhook" no constituye función PSP (1.4.3, 1.4.4, 1.4.8). Conviene llevarle el diagrama de flujo, que es el mismo tipo de diagrama que pide el BCRA al registrar.
- **Abogado de consumo**: términos y condiciones del nodo (canal técnico, el comercio es el proveedor), redacción que resista el criterio *Almirón*, botón de arrepentimiento y deber de información (art. 4 LDC).
- **Abogado de datos**: política de privacidad, inscripción de bases en la AAIP y custodia de tokens OAuth.
- **Contador**:
  - encuadre de los aportes al operador (¿donación o servicio?), monotributo y categoría;
  - IIBB en CABA, PBA y la provincia del operador;
  - efecto de SIRCUPA y SIRCREB sobre su cuenta;
  - si se cobra un fee en algún momento: facturación al comercio, IVA y Convenio Multilateral.
- **Gobernanza**: si el proyecto va a cobrar algo o firmar con PSPs, necesita **persona jurídica**, por ejemplo una asociación civil o una fundación. Evaluar con abogado.
