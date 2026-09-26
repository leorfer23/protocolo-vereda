# Antifraude y transparencia

Propuesta del 2026-09-25. Es un plan para aprobar, todavía no es norma de la spec: cada salvaguarda
entra al protocolo con su propio PR (esquema, `openapi.yaml`, `mcp/herramientas.json`, suite) una vez
aprobada.

Sale de una auditoría de la spec, `vereda-nodo`, `vereda-app` (iOS y Android) y `vereda-webapp`
contra el fraude real de marketplaces y delivery en Argentina.

## 1. La regla fija: Vereda no es juez

- **Nadie bloquea, banea ni puntúa a nadie por una decisión invisible nuestra.** Ni el operador del
  nodo, ni un agente, ni un equipo de Vereda.
- **El arma es la transparencia.** Cada salvaguarda produce **hechos verificables** (firmados, con su
  fórmula o su regla pública) que ve **quien decide**: el comercio antes de aceptar, el comprador
  antes de pagar, el repartidor antes de tomar un viaje.
- **Las reglas son públicas y las elige cada uno.** El protocolo puede fijar límites iguales para
  todos (un tope, un plazo), escritos en la spec y anunciados en `/.well-known/vereda.json`. Lo que
  depende de cada caso (aceptar o no, exigir algo más) lo decide el comercio, con reglas que se ven
  en su ficha.
- **Todo deja registro auditable.** Lo que alguien afirma, lo firma. Lo que el nodo calcula, lo
  publica con cómo recalcularlo.
- **La experiencia normal no se toca.** Un comprador, un comercio o un repartidor honesto no ve un
  paso más. Las señales aparecen donde ya se decide (la tarjeta del pedido, la pantalla de pago, la
  oferta de viaje) y solo llaman la atención cuando hay algo que ver.
- **Hechos, no puntajes.** "3 pedidos entregados, 1 sin retirar, cuenta de hace 4 días" y no "riesgo
  alto". El que mira saca su conclusión.

## 2. Amenazas, de mayor a menor impacto

El impacto pesa tres cosas: qué tan común es en Argentina hoy, cuánto pierde la víctima, y qué tan
expuesto queda Vereda en el lanzamiento del 28/9 (efectivo y transferencia, sin PSP).

| # | Amenaza | Qué pasa hoy en Vereda | Impacto |
|---|---|---|---|
| A1 | **Transferencia que no llegó** ("ya te transferí", captura falsa o editada) | "Ya transferí" no confirma nada y solo confirma el comercio: bien. Pero la referencia de cobro **choca** entre pedidos (primer tramo del UUIDv7: todos los pedidos del nodo en la misma ventana de ~65 s comparten referencia), no hay centavos únicos, el comercio confirma con un toque y sin firma, un agente con `administrar` puede confirmar plata que no ve, y se puede entregar sin cobro confirmado. Las apps muestran "Avisó que te transfirió" aunque el comprador no avisó. | **Crítico** |
| A2 | **Pedido fantasma y comprador que no aparece** (efectivo nunca cobrado, retiro que nadie busca) | No existe el estado "no vino"; un pedido `listo` sin retirar no vence y retiene el stock; el comercio cancela con la política del comprador y queda como `cancelado_por_usuario`. Un comprador que no aparece no deja rastro: su historial solo cuenta lo bueno. | **Alto** |
| A3 | **Suplantación de comercio o de alias** (ficha falsa, alias de un tercero, alias cambiado) | Vinculaciones verificables y homónimos cerca: bien. Pero el `titular` es texto libre del comercio, "el titular coincide" se cuenta por comercio y no por alias (sobrevive 90 días a un cambio de alias), cambiar el alias no deja evento ni registro, y lo puede hacer un miembro del equipo o un agente. | **Alto** |
| A4 | **Robo de cuenta** (clave, sesión, SIM swap, XSS) | Declarar la clave comprometida o rotarla **no cierra las sesiones** (duran 30 días y se renuevan sin firmar). No hay lista de dispositivos. En la web la semilla es extraíble y el token vive en `localStorage`, sin CSP. En las apps, las 12 palabras se ven sin pedir desbloqueo. | **Alto** |
| A5 | **Inundación de pedidos y ataque al ranking** | `confirmarCarrito` no tiene límite; una transferencia reserva stock hasta 60 min sin requisito; el ranking cuenta "sin respuesta" como rechazo, así que inundar a un rival con pedidos que tiene que rechazar lo baja. El límite de pedidos por IP mira la IP del proxy de Cloudflare: bloquea a todos o a nadie. | **Alto** |
| A6 | **Repartidor que no rinde el efectivo** | Rendición firmada por las dos partes: bien. Pero solo la ven comercio y repartidor, `al_retirar` no se exige al retirar, y "nada vence": un repartidor con diez rendiciones colgadas se ve igual que uno limpio. | **Medio** |
| A7 | **Cuentas múltiples** (granjas de promos de primera compra, campañas de reseñas, evadir denuncias) | Reseñas con prueba de compra y crédito `k`: bien. Pero la primera compra se regala por identidad, y las identidades son gratis. | **Medio** |
| A8 | **"No llegó" / "llegó mal"** (reclamo falso) | La entrega la firma solo el repartidor; el comprador nunca co-firma. No hay objeto de reclamo: palabra contra palabra. | **Medio** |
| A9 | **Contracargo o transferencia desconocida** (el comprador denuncia en su banco después de recibir) | No existe `revertido`: un cobro confirmado es final y no queda rastro. | **Medio** (sube con PSPs) |
| A10 | **Trucos con centavos y pasarelas** (pagar un monto parecido, señalar la transferencia de otro, QR pegado encima) | Los centavos únicos no existen todavía (solo en `docs/investigaciones/cobros.md`). Sin reglas de colisión, ventana ni reuso. | **Medio**, se vuelve alto el día que haya centavos únicos mal hechos |

### Donde hoy Vereda sí juzga, y hay que sacarlo

- **Lista de bloqueo del nodo "por fraude"** (`docs/federacion.md`): es pública, pero la decide el
  operador sin criterio escrito.
- **`dni_prueba_de_vida`, `cuit_verificado`, `foto_geolocalizada`**: ningún documento dice cómo se
  obtienen, y una prueba de vida supone un verificador externo (RENAPER).
- **El vínculo persona-comercio que anula una reseña** (`dueno_o_vinculada`): el motivo no se publica
  y nadie de afuera lo puede recalcular.
- **El término de cumplimiento del ranking** baja a un comercio por lo que hacen otros (pedidos que
  tuvo que rechazar), justo lo que la spec prohíbe a las denuncias.

La salvaguarda 10 los corrige.

## 3. Las diez salvaguardas

**Dueño** dice quién la construye. Todo lo que toca cobros lo construye el Lead de pagos, que ya
tiene los centavos únicos y los conectores en su tablero; esta propuesta fija lo que el antifraude
necesita de esas piezas.
**Costo** es trabajo de agentes (días de un worker) más lo que cuesta en plata. Ninguna salvaguarda
necesita un servicio pago, una cuenta nueva ni un verificador.

---

### S1. Cada cobro tiene huella única (centavos y referencia) — *dueño: Lead de pagos*

- **Protege:** A1, A10. El comercio reconoce **su** transferencia en el extracto sin mirar una
  captura, y nadie puede señalar la transferencia de otro.
- **Cómo lo ve la gente:** el comprador ve el monto con los centavos resaltados ("mandá exactamente
  $12.400,**37**") y los copia con un toque. El comercio ve el mismo monto y la referencia para
  buscar en su app del banco.
- **Protocolo:** los centavos únicos pasan de la investigación a la spec, con reglas de colisión: son
  únicos entre los cobros abiertos del mismo destinatario, no se reusan hasta 24 h después de cerrado
  el cobro, y el ajuste va siempre a favor del comprador (se resta, nunca se suma). La `referencia`
  deja de derivarse del id (hoy choca) y pasa a ser corta, única por destinatario y legible. Se aclara
  que `instrucciones` se congelan al crear el cobro.
- **Nodo:** asignación de centavos con índice único; referencia nueva; pagos al repartidor igual.
- **Apps y webapp:** monto con centavos resaltados y copiable; en la web, usar el monto ajustado
  (hoy muestra el monto sin ajustar).
- **Procesos:** liberar los centavos al cerrar o vencer el cobro.
- **Costo:** 1-2 días. $0.

### S2. "Recibido" es una constancia firmada, y puede revertirse a la vista — *dueño: Lead de pagos*

- **Protege:** A1, A9. Separa "el comprador dice que pagó" de "el comercio vio la plata", y deja
  rastro si después la plata se fue.
- **Cómo lo ve la gente:**
  - El comercio ve "Avisó que te transfirió · 21:14 · referencia K7Q2" solo si el comprador avisó, y
    una línea fija: "Mirá tu app del banco, no una captura". Confirma con "Ya la vi en mi cuenta".
  - El comprador recibe "El local confirmó tu pago a las 21:16", con el sello Firmada.
  - Si después la transferencia se revierte, el comercio lo marca ("Me la desconocieron"), firmado.
- **Protocolo:**
  - `pago.confirmacion`: `{por, instante, firma}` firmado por quien recibe. Se suma
    `firmas.cobro` al pedido.
  - Estado `revertido` con evento `pago.revertido` y motivo, firmado por el destinatario.
  - Confirmar una transferencia pide un alcance de mandato propio (`confirmar_cobros`): un agente con
    `administrar` ya no puede confirmar plata que no ve, salvo que la persona se lo dé a propósito.
  - Entregar un pedido con transferencia pide cobro confirmado, o una decisión explícita y firmada del
    comercio ("entrego sin confirmar").
- **Nodo:** los cambios de estado (hoy aceptar antes de confirmar deja el pedido sin poder
  confirmarse y lo cancela al vencer: bug entregado al Lead de pagos), la firma y el estado nuevo.
- **Apps y webapp:** el aviso solo si `pago.transferencia` existe (hoy aparece antes de tiempo en
  iOS y Android, y nunca en la web por un bug de estado), la línea fija, el sello Firmada.
- **Procesos:** ninguno nuevo.
- **Costo:** 2-3 días. $0.

### S3. La cuenta de cobro deja huella — *dueño: Lead de pagos (alias) + este Lead (señal de identidad)*

- **Protege:** A3. Un impostor puede copiar un nombre; no puede heredar el historial de un alias ni
  cambiar el alias sin que se vea.
- **Cómo lo ve la gente:**
  - En la pantalla de transferencia, el comprador ve "Titular: Juan Pérez · coincidió en 38 pagos con
    este alias". Si el alias es nuevo: "Alias nuevo: todavía nadie comprobó el titular".
  - Si el comercio cambió el alias hace poco: "Cambió su cuenta de cobro hace 2 días".
  - Después de pagar se sigue preguntando "¿el titular coincidía?" (hoy ya existe).
- **Protocolo:**
  - `comprobacion_titular` pasa a contarse por huella del alias (hash), no por comercio.
  - Evento público `comercio.cuenta_cobro_cambiada` (sin el alias, con el instante y quién la
    cambió), y la ficha publica `cuenta_cobro_desde`.
  - Cambiar la cuenta de cobro pide firma fresca de la clave de quien la cambia (ver S8): un token de
    sesión o de agente solo no alcanza. Entra al permiso `cobros` del equipo, separado de `datos`.
- **Nodo:** tabla de comprobaciones por huella, evento, firma fresca en `editarComercio` cuando toca
  `privado.cuenta_cobro`.
- **Apps y webapp:** dos líneas nuevas en la pantalla de transferencia y una en la ficha.
- **Procesos:** ninguno.
- **Costo:** 1-2 días. $0.

### S4. El comercio ve hechos del comprador antes de aceptar — *dueño: este Lead*

- **Protege:** A2, A5, A7. Quien arriesga su mercadería decide con información, sin que Vereda
  decida por él.
- **Cómo lo ve la gente:** en la tarjeta del pedido, una línea discreta con hechos: "Cuenta de hace
  3 días · primer pedido acá · 0 entregados". Para un comprador con historia: "41 entregados · 2 años".
  Si hay algo para mirar: "1 sin retirar", "1 transferencia revertida", "pedido hecho por su agente".
  Nunca un número de riesgo ni un color de alarma por defecto.
- **Protocolo:** `pedido.partes.usuario.hechos` (calculado por el nodo, con reglas públicas en
  `docs/antifraude.md`): antigüedad de la cuenta, entregados (total y con este comercio), sin retirar
  o no recibidos (S5), cancelados por él después de aceptado, transferencias revertidas (S2),
  contacto confirmado sí/no, hecho por mandato sí/no. Todo es un conteo de pedidos que el comprador
  mismo puede ver en `GET /yo/hechos`, igual que los ve el comercio.
- **Nodo:** un agregado por identidad, actualizado al cerrar cada pedido.
- **Apps y webapp:** una línea en `TarjetaDePedido` y en el detalle del pedido, con los componentes
  que ya existen (`Sello`, `DatosDeLocal` como patrón). El comprador ve sus propios hechos en Vos.
- **Procesos:** recálculo nocturno de antigüedad (barato).
- **Costo:** 2 días. $0.

### S5. "No vino" existe, cierra el pedido y libera el stock — *dueño: este Lead*

- **Protege:** A2, A5.
- **Cómo lo ve la gente:**
  - El comercio, pasada la hora de retiro prometida más un margen público (30 min), ve "No vino a
    retirar" en el pedido. Tocarlo cierra el pedido y devuelve el stock.
  - El repartidor que llegó a la puerta y nadie atiende marca "No me atendieron" desde donde está (su
    ubicación firmada queda como evidencia) y vuelve con el pedido.
  - El comprador ve el motivo en su pedido y en sus hechos, con un botón "Yo sí fui" para dejar su
    versión firmada al lado. Nadie arbitra: quedan las dos.
- **Protocolo:** motivos `no_retirado` y `no_recibido` que puede usar el comercio (o el repartidor
  para `no_recibido`) desde `listo`, `asignado` y `en_camino`, firmados, con plazo mínimo público.
  Descargo del comprador firmado. El comercio deja de cancelar "como el comprador" (hoy queda
  `cancelado_por_usuario`).
- **Ranking:** los pedidos cerrados como `no_retirado`, `no_recibido`, `pago_vencido` o cancelados
  por el comprador **no cuentan** en el término de cumplimiento del comercio. Inundar a un rival deja
  de bajarlo.
- **Nodo:** transiciones nuevas en la tabla de estados, descargo, cambio en la fórmula del ranking.
- **Apps y webapp:** un botón en el pedido del comercio y del repartidor, una línea y un botón en el
  del comprador.
- **Procesos:** ninguno: lo dispara una persona, no un reloj. Así nadie queda "no vino" por un
  timeout del nodo.
- **Costo:** 2-3 días. $0.

### S6. Entregar con código: el comprador co-firma que recibió — *dueño: este Lead*

- **Protege:** A8 ("no llegó") y A2 (efectivo nunca cobrado).
- **Cómo lo ve la gente:** igual que el retiro por el local, que ya usa código: el comprador ve
  "Tu código: 4821" y se lo dice a quien le entrega. El repartidor lo escribe y listo. Si el comprador
  no está (lo deja en portería), el repartidor entrega con foto, como hoy, y queda como "entregado sin
  código". El comercio elige en su ficha si pide código siempre, solo en efectivo o nunca.
- **Protocolo:** `codigo_entrega` (4 dígitos) para pedidos con envío, y `firmas.recepcion` cuando se
  usa. Límite de intentos (5) igual para el código de retiro, que hoy no tiene. Regla pública del
  comercio en `modalidades`.
- **Nodo:** código al despachar, validación con tope de intentos, marca "sin código".
- **Apps y webapp:** el código en el pedido del comprador, el teclado en la entrega del repartidor.
- **Procesos:** ninguno.
- **Costo:** 1-2 días. $0.

### S7. La rendición del efectivo a la vista — *dueño: este Lead*

- **Protege:** A6.
- **Cómo lo ve la gente:**
  - Al elegir repartidor (y en la oferta del pool) el comercio ve "Rindió 57 de 57" o "2 rendiciones
    en desacuerdo · 1 sin rendir hace más de 24 h".
  - El repartidor ve lo mismo sobre el comercio ("confirmó 57 de 57 rendiciones"), porque el que no
    confirma lo que recibió también hace daño.
  - Si el comercio eligió "el repartidor paga al retirar", el retiro no se marca hasta que el
    repartidor declara el pago y el comercio lo confirma.
- **Protocolo:** en la reputación pública del repartidor y del comercio, agregados de rendición:
  `rendidas`, `en_desacuerdo`, `pendientes_mas_24h`. Son conteos, nunca los montos. `al_retirar`
  pasa a ser condición de `retirarPedido`.
- **Nodo:** los agregados y la condición.
- **Apps y webapp:** una línea en la opción de repartidor y en la oferta de viaje; el sello Firmada
  (ya existe en VeredaUI y no lo usa nadie) en cada rendición. Arreglar "Recibí otro monto": en la
  web registra $0 si el campo está vacío, y en iOS pierde los centavos.
- **Procesos:** el conteo de "más de 24 h" corre en el mantenimiento horario que ya existe.
- **Costo:** 1-2 días. $0.

### S8. La cuenta protegida: sesiones a la vista y firma fresca para lo que importa — *dueño: este Lead*

- **Protege:** A4, y es la base de S3.
- **Cómo lo ve la gente:**
  - En Vos (y en el portal del comercio): "Dónde está abierta tu cuenta", con cada dispositivo o
    sesión, desde cuándo, y "Cerrar las otras".
  - Cambiar el alias, rotar la clave, sumar a alguien al equipo o darle un mandato a un agente pide
    confirmar con Face ID, huella o el código del teléfono. Nada más.
  - Si se abre una sesión nueva o se da un mandato nuevo, aviso a los otros dispositivos: "Se abrió tu
    cuenta en un teléfono nuevo".
  - Ver las 12 palabras pide desbloqueo, y la pantalla no se puede capturar (Android `FLAG_SECURE`).
- **Protocolo:**
  - `GET /yo/sesiones` y `DELETE /yo/sesiones/{id}` (y "todas menos esta").
  - Declarar la clave comprometida o rotarla **cierra todas las sesiones** de esa identidad (hoy no).
  - **Firma fresca**: las operaciones sensibles (cuenta de cobro, rotar, equipo, mandatos, exportar)
    llevan una firma de la clave sobre la operación con instante de menos de 5 minutos, además del
    token. Un token robado solo no alcanza para nada de eso.
  - Eventos `sesion.abierta` y `mandato.otorgado` al propio usuario.
- **Nodo:** borrar sesiones al rotar o comprometer; lista y cierre de sesiones; verificación de
  firma fresca.
- **Webapp:** la clave pasa a CryptoKey no extraíble (WebCrypto Ed25519) y la sesión a una cookie
  `HttpOnly`/`Secure`/`SameSite=Strict` del worker. Cabeceras CSP (`script-src 'self'`,
  `frame-ancestors 'none'`), `Referrer-Policy` y `Permissions-Policy` en el worker y en `vereda-web`.
- **Apps:** biometría (LocalAuthentication / BiometricPrompt) para firma fresca y para ver la frase.
- **Procesos:** ninguno.
- **Costo:** 3-4 días (lo más grande). $0.

### S9. Topes públicos contra inundación y granjas — *dueño: este Lead*

- **Protege:** A5, A7.
- **Cómo lo ve la gente:** casi nunca lo ve. Quien pasa un tope recibe el motivo en palabras
  ("Tenés 3 pedidos esperando pago. Pagá o cancelá uno para hacer otro"). El comercio, en su ficha,
  puede sumar reglas que se ven públicas: "Transferencia: desde tu segundo pedido entregado en
  Vereda" o "Promo de primera compra: con contacto confirmado".
- **Protocolo:**
  - Topes iguales para todos, publicados en `/.well-known/vereda.json`: pedidos abiertos sin pagar
    por identidad (3), pedidos confirmados por minuto por identidad, mensajes por minuto en un
    pedido. `429` con `detalle` legible.
  - Los requisitos que hoy el comercio puede poner al efectivo (`pedidos_entregados_minimo`) se
    pueden poner también a la transferencia.
  - `promocion.condiciones.primera_compra` suma requisitos que elige el comercio: contacto confirmado
    o un mínimo de pedidos entregados en la red.
- **Nodo:** los topes; el límite por IP pasa a leer la IP real del cliente
  (`CF-Connecting-IP`, que solo acepta del worker propio) y se suma el límite por identidad.
- **Apps y webapp:** mostrar el motivo del 429; en el portal del comercio, las reglas nuevas en su
  configuración de cobro y promos.
- **Procesos:** ninguno (ventanas en memoria o en Postgres).
- **Costo:** 1-2 días. $0.

### S10. Registro público y sin jueces escondidos — *dueño: este Lead*

- **Protege:** la regla fija de §1, y sostiene a todas las demás: cualquiera puede comprobar que el
  nodo no inventa ni esconde hechos.
- **Cómo lo ve la gente:** en "Cómo se calcula" (que ya existe para la reputación), un enlace a "Qué
  registra este nodo" y a las reglas de esta página. Para un periodista, un auditor o un agente: una
  URL con el registro.
- **Protocolo:**
  - `GET /registro`: registro público solo-agregar con los hechos que cambian lo que ven otros
    (cambios de cuenta de cobro, reversiones, no vino y su descargo, denuncias, vinculaciones caídas,
    bloqueos de federación), cada entrada firmada por su autor y **encadenada por hash** con la
    anterior, sin datos personales (identidades y pedidos por referencia). Cualquiera lo copia y
    comprueba que nadie reescribió el pasado.
  - Sacar el juicio de los cuatro lugares de §2: la lista de bloqueo de federación solo con criterios
    escritos y automáticos; quitar `dni_prueba_de_vida` y definir `cuit_verificado` y
    `foto_geolocalizada` como pruebas automáticas (o quitarlos); publicar el motivo de
    `dueno_o_vinculada` como un hecho recalculable ("comparte teléfono con quien administra el
    comercio", sin el teléfono); el cambio de ranking de S5.
- **Nodo:** tabla del registro, escrita en la misma transacción que el hecho; endpoint paginado.
- **Apps y webapp:** un enlace. Sin pantalla nueva.
- **Procesos:** ninguno (el encadenado se hace al escribir).
- **Costo:** 2 días. $0.

## 4. Resumen

| Salvaguarda | Amenazas | Dueño | Días | Plata |
|---|---|---|---|---|
| S1 Huella única del cobro | A1, A10 | pagos | 1-2 | $0 |
| S2 Recibido firmado y revertible | A1, A9 | pagos | 2-3 | $0 |
| S3 Cuenta de cobro con huella | A3 | pagos + antifraude | 1-2 | $0 |
| S4 Hechos del comprador | A2, A5, A7 | antifraude | 2 | $0 |
| S5 "No vino" y ranking sin ataque | A2, A5 | antifraude | 2-3 | $0 |
| S6 Entrega con código | A8, A2 | antifraude | 1-2 | $0 |
| S7 Rendición a la vista | A6 | antifraude | 1-2 | $0 |
| S8 Cuenta protegida | A4 | antifraude | 3-4 | $0 |
| S9 Topes públicos | A5, A7 | antifraude | 1-2 | $0 |
| S10 Registro público, sin jueces | todas | antifraude | 2 | $0 |

Orden propuesto para construir: primero lo que ya está roto y expone plata el 28/9 (S1-S2 en pagos;
S8 cierre de sesiones y CSP, S9 límite por IP real), después las señales (S4, S5, S7), después
S3, S6 y S10.

### Pantallas

Cada señal nueva usa componentes que ya existen (`Sello`, `Firmada`, `Nota`, `Stat`, la línea de
`DatosDeLocal`, la hoja de "Cómo se calcula"), con el mismo nivel de diseño que las pantallas de
cobro. Lo que sea una dirección visual nueva de verdad (la lista de sesiones, el descargo "Yo sí
fui") se presenta con opciones antes de construirse.

### Lo que esta propuesta no hace

- No bloquea a nadie, no esconde fichas ni baja a nadie en el ranking por una señal.
- No pide DNI, selfie ni documentos, ni usa un verificador externo.
- No arbitra disputas: deja a la vista las dos versiones firmadas.
- No toca la plata ni suma un PSP.
