# Cobro con proveedor de pagos (PSP)

Un comercio puede cobrar con tarjeta u otros medios de uno o varios proveedores (Ualá Bis, Mercado Pago, Mobbex, …) sin que Vereda toque la plata. La plata va a la cuenta del comercio en el proveedor con el que pagó el comprador; el nodo solo crea el cobro con las credenciales del comercio, guarda referencias y confirma cuando el proveedor dice que pagaron. Diseño del lanzamiento en `docs/investigaciones/pagos-lanzamiento.md`.

## Principios

- **Vereda nunca toca la plata.** El cobro se crea en la cuenta del comercio, con las credenciales o el token del comercio. El nodo no es marketplace: la comisión de plataforma es **siempre 0**. No manda `marketplace_fee` ni campos equivalentes.
- **Sin datos de tarjeta en el nodo.** El comprador paga en la página del proveedor (`link_pago`). El nodo no recibe número de tarjeta, CVV ni nada PCI.
- **Confirmar solo después de re-consultar.** Un aviso del proveedor, una vuelta del navegador o una query string avisan; el nodo marca el cobro `confirmado` recién cuando re-consulta al proveedor y lo ve aprobado. Idempotente: el mismo aviso dos veces no duplica.
- **Los secretos no salen.** Credenciales y tokens viven cifrados en el nodo. Nunca están en la ficha, en `GET /comercios/{id}/cobradores`, en un evento, en un error ni en un log.
- **Varios proveedores a la vez.** El comercio activa los que quiera; el comprador elige con cuál paga entre los activos de ese comercio, además del efectivo y la transferencia. Ninguno es "el" medio.
- **El proveedor es intercambiable.** Todo lo que sabe de un proveedor en particular vive en su adaptador (abajo). La API, los eventos y los estados son los mismos con cualquiera.
- **El efectivo y la transferencia directa no cambian.** Tarjeta es un medio más en `medios_cobro`, nunca el primero por defecto (`docs/carrito-y-reserva.md`).

## Proveedores

Un id de proveedor es un string libre (`^[a-z0-9_]+$`), sin enum cerrado: un nodo puede anunciar otro. Los que conoce la spec:

| Id | Proveedor | Conexión | Qué necesita el operador del nodo | Orden |
| --- | --- | --- | --- | --- |
| `uala_bis` | Ualá Bis (API Checkout v2) | `credenciales`: el comercio pega `username`, `client_id` y `client_secret_id` | Nada que registrar: solo la clave de cifrado del nodo | **Oficial, primero** |
| `mercado_pago` | Mercado Pago (Checkout Pro) | `redireccion` (OAuth) | Una aplicación en "Tus integraciones" de su cuenta de MP + la clave de cifrado | Segundo |
| `mobbex` | Mobbex (API Checkout) | `credenciales`: el comercio pega `api_key` (de una aplicación que crea en su propio portal de desarrolladores) y `access_token` (de su consola) | Nada que registrar: solo la clave de cifrado | Tercero |
| `prueba` | Proveedor falso de conformidad y e2e | `credenciales`: una `clave` | Nada; **nunca en producción** | Para pruebas |
| `prueba_redireccion` | Proveedor falso, con conexión por redirección | `redireccion` | Nada; **nunca en producción** | Para pruebas |

Mobbex también ofrece Dev Connect (un "Conectar con Mobbex" por redirección), pero pide que el operador tenga su propia aplicación Mobbex y una cuenta validada; con las credenciales del comercio no hace falta nada del operador, igual que Ualá Bis.

## Cómo se sabe si el nodo lo ofrece

El nodo que ofrece cobradores publica `cobradores` en `/.well-known/vereda.json`: una lista donde cada proveedor dice cómo se conecta (`CapacidadCobrador` en `openapi.yaml`):

```json
"cobradores": [
  {
    "psp": "uala_bis",
    "nombre": "Ualá Bis",
    "conexion": "credenciales",
    "campos": [ { "nombre": "username", "secreto": false }, { "nombre": "client_id", "secreto": false }, { "nombre": "client_secret_id" } ],
    "ambientes": ["produccion"],
    "monto_minimo": { "centavos": 2500, "moneda": "ARS" },
    "reembolso": { "parcial": true, "dias_maximo": 90 }
  },
  { "psp": "mercado_pago", "nombre": "Mercado Pago", "conexion": "redireccion", "reembolso": { "parcial": true, "dias_maximo": 180 } },
  { "psp": "mobbex", "nombre": "Mobbex", "conexion": "credenciales", "campos": [ { "nombre": "api_key" }, { "nombre": "access_token" } ], "reembolso": { "parcial": true, "dias_maximo": 180 } }
]
```

- `conexion`: `credenciales` (el comercio pega lo que generó en su cuenta del proveedor) o `redireccion` (autoriza en el proveedor y vuelve).
- `campos`: solo con `credenciales`, qué pide y en qué orden. `secreto` le dice al portal si lo oculta al tipearlo; sea secreto o no, nunca vuelve.
- `ambientes`: de qué ambiente del proveedor acepta credenciales. Un nodo de producción anuncia solo `produccion`.
- `monto_minimo` / `monto_maximo`: lo que acepta el proveedor por cobro (Ualá Bis: $25 mínimo).
- `reembolso`: si el nodo puede devolver por la API del proveedor, si acepta parciales y hasta cuántos días después. Ausente: la devolución es del comercio con su proveedor, fuera del nodo. El plazo de Mobbex no está documentado: el nodo de referencia anuncia 180 días y, si el proveedor rechaza antes, la devolución queda `fallida`.

Sin `cobradores`, las operaciones del cobrador responden `501 no_implementado` y las apps no ofrecen tarjeta.

## Interruptores del operador

Un nodo **anuncia un proveedor solo cuando su operador lo encendió y el nodo tiene lo que necesita para usarlo**. Apagado, el proveedor no aparece en `cobradores`; si no queda ninguno, todo vuelve a `501` como antes. Sin datos a medias: un proveedor encendido al que le falta algo no se anuncia, y el nodo lo dice en su log al arrancar.

| Proveedor | Se anuncia cuando |
| --- | --- |
| `uala_bis`, `mobbex` | El operador lo encendió y el nodo tiene su **clave de cifrado** (con qué cifra las credenciales en reposo). Nada que registrar en el proveedor: cada comercio trae las suyas. |
| `mercado_pago` | Lo anterior, más la **aplicación de MP del operador**: `client_id`, `client_secret`, la clave secreta del webhook y la URL pública del nodo (para la vuelta OAuth y el aviso). |
| `prueba`, `prueba_redireccion` | Solo en un nodo de prueba. Un nodo de producción **nunca** los anuncia: el nodo de referencia se niega a arrancar con uno de ellos encendido en producción. |

Apagar un proveedor con comercios conectados no borra nada: sus cobradores quedan guardados, sale de los `cobradores` públicos de esos comercios mientras está apagado (y `tarjeta` de sus `medios_cobro` si no les queda otro) y los cobros pendientes se siguen re-consultando hasta cerrar. Encenderlo de nuevo los devuelve como estaban.

## Activar y desactivar proveedores

Solo el dueño del comercio, o un agente / miembro con permiso `datos`. Un comercio tiene **uno por `psp`, varios a la vez**: activar Mercado Pago no toca a Ualá Bis.

| Operación | Qué hace |
| --- | --- |
| `GET /comercios/{id}/cobradores` (`listarCobradores`) | Todos sus proveedores con su estado. Lista vacía si no tiene ninguno |
| `POST /comercios/{id}/cobradores/{psp}/conectar` (`conectarCobrador`) | Activa ese proveedor. Volver a conectar el mismo reemplaza sus credenciales |
| `GET /comercios/{id}/cobradores/{psp}` (`verCobrador`) | El estado de uno. `404` si ese no está conectado |
| `DELETE /comercios/{id}/cobradores/{psp}` (`desconectarCobrador`) | Lo desactiva en el acto y borra sus secretos cuando cierran sus cobros pendientes. Los otros siguen |

Lo mismo por MCP: `cobrador_conectar`, `cobrador_ver` (sin `psp`, la lista), `cobrador_desconectar`.

**Conectar decide a dónde va la plata de los compradores**, igual que cambiar `privado.cuenta_cobro`: pide firma fresca de quien lo conecta (`docs/acceso.md`, punto 7). Un token robado, o un agente con mandato, no alcanza.

El cuerpo de `conectarCobrador` va según la `conexion` del proveedor:

**Con credenciales (Ualá Bis, Mobbex, `prueba`).**

1. El comercio genera sus credenciales en el proveedor (Ualá Bis: app → Cobros online → API; Mobbex: una aplicación en su portal de desarrolladores y el token de su consola) y las pega en el portal.
2. `{credenciales, ambiente?}` con exactamente los `campos` del anuncio. `ambiente` es `produccion` si no se dice.
3. El nodo **las prueba contra el proveedor** (Ualá Bis: pide un token; Mobbex: consulta las operaciones de la entidad) antes de guardar. Si el proveedor las rechaza, `422 credenciales_invalidas` y no se guarda nada. Si el proveedor no responde, `503 psp_no_disponible`.
4. Si andan, las guarda cifradas y responde `200` con el cobrador ya `conectado` (`{psp, conexion, ambiente, estado, titular, conectado_en}`). No hay `volver_a` ni URL.

**Por redirección (Mercado Pago, `prueba_redireccion`).**

1. `{volver_a}` → `200 {url}` de autorización (con `state` firmado por el nodo y PKCE).
2. El comercio autoriza en el proveedor, que vuelve al nodo **fuera de `/v1`** (`/pagos/{psp}/volver`). El nodo canjea el código por tokens, los guarda cifrados y redirige a `volver_a`.

Mandar la forma equivocada (credenciales a uno de redirección o al revés) es `422 conexion_no_corresponde` con `detalle.conexion`. Faltan o sobran campos: `422 cuerpo_invalido` con `detalle.campos`. Un ambiente que el anuncio no lista: `422 ambiente_no_ofrecido`. Un proveedor que el nodo no anuncia: `422 psp_no_ofrecido`.

**Lo que ve el comprador.** La ficha pública del comercio trae `cobradores`: los ids de los proveedores que tiene `conectado` ahora, sin titulares ni nada más (el nombre para mostrar sale del anuncio del nodo). `tarjeta` está en `medios_cobro` si y solo si esa lista no está vacía; el nodo la pone y la saca solo.

**Lo privado.** `privado.cuenta_cobro.cobradores` tiene un ítem por proveedor: `psp`, `estado`, `ambiente`, `titular_psp` y `conectado_en`. No se federa.

### Estados de cada proveedor

| Estado | Qué pasó | Qué hace el comercio |
| --- | --- | --- |
| `conectado` | El nodo puede cobrar con ese proveedor | Nada |
| `vencido` | El token venció y no se pudo renovar (redirección) | Volver a autorizar |
| `revocado` | El comercio o el proveedor cortaron el vínculo (MP avisa con su tópico de desconexión) | Conectar de nuevo si quiere |
| `credenciales_rechazadas` | El proveedor dejó de aceptar las credenciales guardadas: el comercio las regeneró o las dio de baja (Ualá Bis responde 401 al pedir el token; Mobbex, 401 a cualquier llamada) | Pegar las nuevas con `conectarCobrador` |

Cada proveedor tiene su estado; uno caído no afecta a los otros. Fuera de `conectado`, ese proveedor sale de los `cobradores` públicos hasta que vuelva a quedar conectado (y `tarjeta` sale de `medios_cobro` si no queda ninguno); sus cobros pendientes se siguen re-consultando mientras se pueda. Cada cambio sale como `comercio.cobrador_cambiado` (abajo).

## Checkout con tarjeta

1. El comprador elige `metodo_pago: tarjeta` al confirmar, solo si el comercio tiene `tarjeta` en `medios_cobro`. Si no, `422 medio_no_disponible` con `detalle.medios_cobro`.
2. **Elige también el proveedor**, en `psp`, entre los `cobradores` de la ficha del comercio. Si el comercio tiene uno solo, puede omitirlo. Con varios y sin `psp`: `422 psp_requerido`. Uno que ese comercio no tiene activo: `422 psp_no_activo`. Los dos traen `detalle.cobradores`, los activos, para que la persona elija de nuevo.
3. Si el total a pagar con tarjeta está fuera de `monto_minimo` / `monto_maximo` de ese proveedor: `422 monto_menor_al_minimo` o `monto_mayor_al_maximo`, con el límite en `detalle`, y no se crea nada. La app puede ofrecer otro de los activos.
4. El nodo crea el cobro en ese proveedor con las credenciales del comercio, por el monto exacto, con su propia referencia (el id del pago) como referencia externa, la URL de aviso del nodo y la vuelta a la app. Si el proveedor no responde: `503 psp_no_disponible`, sin pedido ni reserva.
5. El cobro nace `pendiente` con `link_pago`, `psp` (el elegido), `psp_referencia` y `vence` (`ventana_pago_min` del comercio). Hasta `vence` el pedido retiene stock y cupos, como cualquier pendiente.
6. La app abre `link_pago` (navegador, `SFSafariViewController`, Custom Tabs). Al volver, el estado real llega por el evento (`pago.confirmado`, `pago.fallido`, `pago.vencido`), no por la query string.
7. Confirmado: `confirmado_por: psp`, el pedido pasa a `pagado` y salen `pago.confirmado` y `pedido.pagado`.

Si el comercio desactiva un proveedor con cobros pendientes en él, esos cobros siguen su curso: el nodo los re-consulta con las credenciales que tenía hasta que cierran, y recién ahí las borra.

**Al vencer.** Antes de dar un cobro por `vencido`, el nodo re-consulta al proveedor: si ya está aprobado, lo confirma. Si no, el pago queda `vencido` y el pedido `cancelado` con `pago_vencido`. Si el proveedor igual lo aprueba después (el comprador pagó en el último segundo), el nodo lo confirma igual —la plata existe y no se esconde—, el pedido sigue cancelado y el comercio lo ve para devolverlo con `reembolsarPago`. El nodo no devuelve solo.

## La interfaz del proveedor

Lo que un proveedor tiene de particular vive en un **adaptador**. El nodo de referencia lo llama así; otro nodo puede organizarlo distinto, pero el comportamiento observable desde la API tiene que ser este. Un proveedor nuevo es un adaptador nuevo, sin tocar la spec ni las apps.

| Operación | Qué hace | Ualá Bis | Mercado Pago | Mobbex |
| --- | --- | --- | --- | --- |
| **Probar credenciales** | Antes de guardar: ¿andan? Devuelve el titular si el proveedor lo da | `POST /v2/api/auth/token` (`grant_type: client_credentials`); 401 → `credenciales_invalidas` | No aplica: el OAuth ya prueba | `GET /p/entity/operations` con `x-api-key` y `x-access-token`; 401 → `credenciales_invalidas`; titular de `entity.name` |
| **Autorizar / canjear / renovar** | Solo redirección: URL de autorización, canje del código, renovación del token | No aplica: el token de 24 h se vuelve a pedir con las credenciales | OAuth con PKCE; el refresh token **rota en cada uso** y se guarda en la misma transacción | No aplica: el token de la entidad no vence (NC) |
| **Crear cobro** | Monto, referencia externa, vencimiento, URL de aviso, vuelta. Devuelve `psp_referencia` y `link_pago` | `POST /v2/api/checkout`: `amount` en centavos como string, `external_reference`, `notification_url`, `callback_success` / `callback_fail` → `uuid`, `links.checkout_link` | `POST /checkout/preferences` sin `marketplace_fee`, `binary_mode: true`, `expiration_date_to` = `vence` → `id`, `init_point` | `POST /p/checkout` con `total`, `reference` (única), `webhook`, `return_url`, `timeout` = minutos hasta `vence`, sin `split` → `id`, `url` |
| **Re-consultar** | Estado real del cobro, monto y referencia externa. Es lo único que confirma | `GET /v2/api/orders/{uuid}` | `GET /v1/payments/{id}` (o la búsqueda por `external_reference`) | `GET /p/operations/{id}` (o `?ref=`) |
| **Reembolsar** | Total o parcial, idempotente | `POST /v2/api/orders/{uuid}/refund` con `amount`; responde `INITIATED`, el resultado llega por aviso | `POST /v1/payments/{id}/refunds` con `X-Idempotency-Key` | Total `GET /p/operations/{id}/refund`; parcial `POST` con `total`, solo desde el día siguiente al cobro |
| **Interpretar un aviso** | Del cuerpo crudo saca **qué** cobro cambió; nunca **cómo** quedó | `{uuid, external_reference, status}` sin firma | Verifica `x-signature` (HMAC-SHA256) y saca `data.id` | `data.payment.id` y `data.checkout.reference`, sin firma |

El adaptador compara siempre lo re-consultado con lo que el nodo espera: la referencia externa es la del pago y el monto es el del pago. Si no coinciden, no confirma y lo registra.

### De los estados del proveedor a los de `pago.json`

Se marca pagado **solo con el estado aprobado de la re-consulta**. Un estado intermedio (Ualá `PROCESSED`, MP `in_process`, Mobbex `100` en revisión) no es pagado: el pedido espera.

| `pago.estado` | Ualá Bis | Mercado Pago | Mobbex (código) | `prueba` |
| --- | --- | --- | --- | --- |
| `pendiente` | `PENDING`, `PROCESSED` | `pending`, `in_process`, `authorized` | `1`, `2`, `3`, `100` | `pendiente`, `procesado` |
| `confirmado` (`confirmado_por: psp`) | `APPROVED` | `approved` | `200` a `302` | `aprobado` |
| `fallido` | `REJECTED` | `rejected`, `cancelled` | `400`, `402`, `403`, `410` a `419`, `610` | `rechazado` |
| `vencido` | Pasó `vence` sin `APPROVED` | Pasó `vence` sin `approved` (o el proveedor lo dio por caducado) | `401` (expirada), o pasó `vence` | `vencido`, o pasó `vence` |
| Sigue `confirmado`, con una devolución (`reembolsado`) | `REFUNDED` | `refunded` | `601`, `602`, `605` | `reembolsado` |
| Sigue `confirmado`, sale `pago.contracargo` | — (Ualá lo debita de la cuenta del comercio, sin aviso por API) | `charged_back`, `in_mediation` | — (Mobbex lo debita de liquidaciones futuras) | — |

Un cobro `fallido` cancela el pedido con `pago_fallido` y uno `vencido` con `pago_vencido` (`docs/carrito-y-reserva.md`): los dos liberan stock y cupos, y el comprador puede confirmar el carrito de nuevo, con el mismo proveedor o con otro.

### Avisos del proveedor

- Llegan **fuera de `/v1`**: `POST /pagos/{psp}/webhook`. La URL que el nodo le da al proveedor al crear el cobro lleva un token opaco por cobro, para descartar avisos inventados sin ir al proveedor.
- **Ualá Bis y Mobbex no firman sus avisos**: el nodo nunca cree lo que dice el cuerpo y **siempre re-consulta**. Mercado Pago firma: el nodo verifica la firma y **re-consulta igual**. El aviso solo dice "mirá este cobro".
- **Idempotencia por referencia + estado**: un aviso con el mismo `psp_referencia` y el mismo estado que el nodo ya procesó no hace nada. Ni Ualá ni Mobbex mandan id de aviso; Ualá reintenta hasta 4 veces.
- El nodo responde `200` apenas anotó el aviso, aunque la referencia no sea suya (y la descarta): un error hace que el proveedor reintente algo que no va a cambiar.

### Barrido de pendientes

Un aviso se puede perder. Cada minuto el nodo re-consulta los cobros `pendiente` con `psp` que llevan más de un minuto así, y siempre antes de vencer uno. También re-consulta las devoluciones pendientes. Con el proveedor caído, espera y vuelve a probar; nunca da por vencido un cobro sin haberlo re-consultado.

## Devoluciones

`POST /pedidos/{id}/reembolso` (`reembolsarPago`, MCP `pedido_reembolsar`). Solo el comercio del pedido: la dueña, o un agente / miembro con permiso `pedidos`, con `Idempotency-Key`. Va siempre por el proveedor con el que se cobró (`psp` del cobro), aunque el comercio tenga otros activos.

- **Qué se puede devolver:** el cobro de `productos` con `metodo: tarjeta`, ya `confirmado`, de un proveedor que anuncia `reembolso`. Con efectivo o transferencia, o sin `reembolso` en el anuncio, es `422 reembolso_no_disponible`: esa devolución la hace el comercio por su cuenta, como siempre. Si el comercio desactivó ese proveedor, tampoco se puede por el nodo (ya no tiene sus credenciales): `422 reembolso_no_disponible`.
- **Cuánto:** `monto_centavos`, o todo lo que queda sin devolver si no viene. Más de eso: `422 monto_excede_lo_cobrado` con `detalle.disponible_centavos`. Menos que el total con un proveedor que solo devuelve el total: `422 reembolso_parcial_no_admitido`.
- **Hasta cuándo:** `reembolso.dias_maximo` desde que se cobró (Ualá Bis 90, MP 180). Después: `422 reembolso_fuera_de_plazo` con `detalle.dias_maximo`.
- **Una a la vez:** con otra devolución del mismo cobro en curso, `409 reembolso_en_curso` (Ualá Bis no acepta dos).
- **Cómo queda:** un pago nuevo en el pedido, `concepto: devolucion`, `pagador` el comercio, `destinatario` el comprador, mismo `metodo` y `psp`, `reembolsa` el id del cobro, `motivo`, `estado: pendiente` y `vence` (hasta cuándo el nodo re-consulta: 7 días en el de referencia). Cuando el proveedor confirma: `confirmado` con `confirmado_por: psp`, el cobro original suma `reembolsado` y sale `pago.reembolsado`. Si la rechaza (Ualá `NOT_REFUNDED`, sin saldo en MP): `fallido` y sale `pago.fallido`. Si vence sin respuesta, queda `vencido` y el comercio lo mira con su proveedor.
- Devolver **no cancela ni cambia el pedido**. Cancelar sigue siendo `cancelarPedido`, y un pedido cancelado ya pagado se devuelve con esta misma operación.
- **Devoluciones hechas afuera:** si el comercio devuelve directo desde la app del proveedor y el nodo lo ve al re-consultar (Ualá `REFUNDED`, MP `refunded`, Mobbex `602`/`605`), anota la devolución confirmada por lo que diga el proveedor, con `reembolsa`, y publica `pago.reembolsado` igual.
- La plata sale de la cuenta del comercio en su proveedor. Con fee 0, Vereda no pone ni retiene nada.

## Contracargos

Son entre el comercio y su proveedor. Si el proveedor avisa (MP `charged_back` / `in_mediation`), el nodo publica `pago.contracargo` y no toca estados: el cobro sigue `confirmado`, el pedido sigue como estaba. Ualá Bis y Mobbex los debitan de la cuenta del comercio sin aviso por API.

## Los proveedores de prueba (`prueba`, `prueba_redireccion`)

Dos proveedores falsos para la suite de conformidad y los e2e, sin plata ni terceros. Se comportan igual al cobrar y al devolver (como Ualá Bis: sin firma, re-consulta, devoluciones parciales hasta 90 días); cambian en cómo se conectan, para probar las dos formas y **dos proveedores activos a la vez**. Solo los anuncia un nodo de prueba; un nodo de producción nunca.

- **Anuncio:**
  - `{"psp": "prueba", "nombre": "Proveedor de prueba", "conexion": "credenciales", "campos": [{"nombre": "clave"}], "ambientes": ["prueba"], "monto_minimo": {"centavos": 2500, "moneda": "ARS"}, "reembolso": {"parcial": true, "dias_maximo": 90}}`
  - `{"psp": "prueba_redireccion", "nombre": "Proveedor de prueba (redirección)", "conexion": "redireccion", "monto_minimo": {"centavos": 2500, "moneda": "ARS"}, "reembolso": {"parcial": true, "dias_maximo": 90}}`
- **Conectar `prueba`:** `credenciales: {clave: "prueba-valida"}`, `ambiente: prueba` → `conectado`, titular `Comercio de prueba`. Cualquier otra clave → `422 credenciales_invalidas`.
- **Conectar `prueba_redireccion`:** `{volver_a}` → `{url}`, una página del mismo nodo con **Autorizar** y **Cancelar**. Un `POST` a esa `url` con `{"resultado": "autorizar"}` hace lo que el botón: el proveedor queda `conectado` (titular `Comercio de prueba`) y responde `204`; con `"cancelar"` no se conecta. Es lo que haría la vuelta OAuth de Mercado Pago.
- **Cobrar:** `link_pago` es una página del mismo nodo con dos botones, **Pagar** y **Rechazar**. Para no depender de un navegador, un `POST` a ese mismo `link_pago` con `{"resultado": "…"}` hace lo que haría el botón y responde `204`:

  | `resultado` | El proveedor falso queda en | El nodo, al re-consultar |
  | --- | --- | --- |
  | `aprobado` | `aprobado` | `confirmado`, pedido `pagado` |
  | `procesado` | `procesado` | Sigue `pendiente` (como `PROCESSED` de Ualá) |
  | `rechazado` | `rechazado` | `fallido`, pedido `cancelado` con `pago_fallido` |
  | `vencido` | `vencido` | `vencido`, pedido `cancelado` con `pago_vencido`, sin esperar `vence` |

  Cada cambio manda el aviso a `/pagos/{psp}/webhook` **dos veces**, sin firma, para ejercitar la re-consulta y la idempotencia. Un `resultado` sobre un cobro que ya no está `pendiente` o `procesado` es `409`.
- **Devolver:** `reembolsarPago` sobre un cobro de un proveedor de prueba queda `pendiente` y el proveedor falso la confirma solo, con su aviso, en menos de un segundo. Un `monto_centavos` que termina en `13` la rechaza, para probar el camino `fallido`.
- Lo usan la suite de conformidad (nivel B) y los e2e de las apps. En el nodo de referencia, el mock local los trae encendidos.

## Eventos

Además de `pago.pendiente` / `confirmado` / `vencido` / `fallido`:

| Evento | Cuándo |
| --- | --- |
| `pago.reembolsado` | El proveedor confirmó una devolución. `datos.pago` es la devolución (`concepto: devolucion`, con `reembolsa`). |
| `pago.contracargo` | El proveedor avisó un contracargo. Informativo: la plata la discute el comercio con su proveedor. |
| `comercio.cobrador_cambiado` | Uno de los proveedores del comercio cambió de estado. `datos.psp` siempre; `datos.cobrador` con el estado (conectado, vencido, revocado, credenciales_rechazadas), o sin `datos.cobrador` si se desconectó. Solo al comercio y a quien lo administra con `datos`; sin secretos. Si cambian los `cobradores` públicos, la ficha cambia como cualquier otra. |

## Errores

| Qué pasa | Estado | Código |
| --- | --- | --- |
| El nodo no anuncia `cobradores` | 501 | `no_implementado` |
| El nodo no anuncia ese `psp` | 422 | `psp_no_ofrecido` |
| Credenciales a un proveedor de redirección, o al revés | 422 | `conexion_no_corresponde` |
| Faltan o sobran campos de credenciales | 422 | `cuerpo_invalido` |
| Ambiente que el anuncio no lista | 422 | `ambiente_no_ofrecido` |
| El proveedor rechazó las credenciales | 422 | `credenciales_invalidas` |
| Conectar sin firma fresca válida | 403 | `firma_fresca_requerida` |
| El proveedor no responde | 503 | `psp_no_disponible` |
| No es el dueño, o falta el permiso | 403 | `no_es_el_dueno` / `sin_permiso` |
| `metodo_pago: tarjeta` y el comercio no tiene `tarjeta` | 422 | `medio_no_disponible` |
| Tarjeta sin `psp` y el comercio tiene varios activos | 422 | `psp_requerido` |
| Tarjeta con un `psp` que el comercio no tiene activo | 422 | `psp_no_activo` |
| Total fuera de lo que acepta ese proveedor | 422 | `monto_menor_al_minimo` / `monto_mayor_al_maximo` |
| Devolver algo que no se puede devolver por el proveedor | 422 | `reembolso_no_disponible` |
| Devolver pasado el plazo del proveedor | 422 | `reembolso_fuera_de_plazo` |
| Parcial con un proveedor que solo devuelve el total | 422 | `reembolso_parcial_no_admitido` |
| Devolver más de lo que queda | 422 | `monto_excede_lo_cobrado` |
| Ya hay una devolución de ese cobro en curso | 409 | `reembolso_en_curso` |
