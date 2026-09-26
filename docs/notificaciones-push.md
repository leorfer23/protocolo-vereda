# Notificaciones push

El comercio se entera de un pedido nuevo, el comprador de que su pedido salió y el repartidor de que le ofrecen un viaje, aunque la app esté cerrada. Es un aviso, no un canal de datos: lo que pasó de verdad se lee en la API y en `GET /eventos`, como siempre. Un push que no llega no rompe nada.

Es opcional. Un nodo sin credenciales de push no las anuncia, `registrarDispositivo` responde `501 no_implementado` y la app ni pide el permiso.

## Quién manda el push

Apple (APNs) y Google (FCM) solo aceptan un push para una app de quien publicó esa app: la clave `.p8` del equipo de Apple dueño del bundle, la cuenta de servicio del proyecto Firebase de la app. Ningún nodo puede avisarle a la app de otro publicador con sus propias claves. Eso deja dos caminos.

### A. El nodo manda directo (lo que hace hoy el nodo de referencia)

El nodo tiene las credenciales del publicador de la app y habla con APNs y FCM.

- Sin servicio intermedio, sin un salto más, sin costo.
- Sirve mientras quien opera el nodo sea quien publica la app. Hoy hay un solo nodo y lo opera el publicador de la app Vereda.
- Un nodo de otro operador no puede avisarle a la app Vereda sin las claves del publicador, y esas claves no se comparten.

### B. Relay del publicador

El publicador de la app corre un servicio chico (un relay) con sus credenciales. El nodo le manda el aviso ya armado, firmado con la clave del nodo, y el relay lo reenvía a APNs o FCM.

- Cualquier nodo le avisa a la app Vereda sin tener sus claves. El relay puede frenar a un nodo que abusa.
- Es un servicio más que correr y mirar, y un salto más de latencia. El relay ve qué token recibe qué aviso y cuándo, aunque no lo que pasó adentro: el aviso no trae datos personales (ver abajo).

### Por qué A ahora, y por qué no cuesta cambiar

**A**, porque es lo que alcanza para un solo nodo y no suma infraestructura. **B**, el día que exista un segundo nodo cuyos usuarios usen la app Vereda.

El protocolo es el mismo en los dos casos: la app registra su token en su nodo, el nodo decide cómo lo entrega. Pasar de A a B es configuración del nodo y un relay nuevo; no cambia la spec, no cambia la app, no hace falta una versión nueva en las tiendas. Por eso esta es la opción más reversible.

## Registrar un dispositivo

La app lo registra con la sesión de la persona, nunca con un mandato: un agente no recibe push en el teléfono de nadie.

- `POST /yo/dispositivos` (`registrarDispositivo`) con `{plataforma, app, token, entorno?}` (`esquemas/dispositivo.json`). `201` con el dispositivo si es nuevo.
- **Idempotente por token.** El mismo `plataforma` + `app` + `token` devuelve el mismo dispositivo con `200`. Si estaba registrado a otra identidad (se cambió de cuenta en el mismo teléfono), pasa a esta: un teléfono avisa a una sola persona.
- La app lo vuelve a registrar cada vez que el sistema le da un token (al abrir, al rotar): es barato y es como se entera el nodo de un token nuevo.
- `app` es el bundle id de iOS o el package de Android. Una app que el nodo no sabe avisar responde `422 app_no_soportada`, con `detalle.apps`: las que sí.
- `entorno` solo en APNs: `desarrollo` para un build de Xcode, `produccion` para TestFlight y la App Store. Default `produccion`.
- Hasta 10 por identidad. El undécimo reemplaza al que hace más tiempo que no se usa.
- `GET /yo/dispositivos` (`listarDispositivos`) los lista. `DELETE /yo/dispositivos/{id}` (`borrarDispositivo`) borra uno: la app lo hace al cerrar sesión, antes de tirar el token de sesión.

El nodo también los borra solo:

- cuando APNs responde `410 Unregistered` o `400 BadDeviceToken`, o FCM `UNREGISTERED` o `INVALID_ARGUMENT` por el token;
- con `borrarCuenta`, en el momento, no al procesarse el borrado;
- con `clave.comprometida` de la identidad.

Un token es un dato personal: el nodo lo guarda solo para avisar, no lo federa, no lo exporta con `exportarCuenta` ni lo muestra a nadie más que a su dueño.

## Qué se avisa y a quién

Esto y nada más. Un nodo no suma avisos por su cuenta: la persona tiene que poder saber qué le va a llegar.

| Evento | A quién | Título | Cuerpo |
| --- | --- | --- | --- |
| `pedido.creado` | comercio | Pedido nuevo | Entró un pedido en {comercio}. |
| `pedido.pagado` | comercio | Pedido pagado | Se pagó un pedido en {comercio}. |
| `pedido.cancelado` | comercio, si canceló el comprador | Pedido cancelado | Se canceló un pedido en {comercio}. |
| `pedido.aceptado` | comprador | Pedido confirmado | {comercio} confirmó tu pedido. |
| `pedido.rechazado` | comprador | Pedido rechazado | {comercio} no puede tomar tu pedido. |
| `pedido.en_camino` | comprador | Tu pedido está en camino | Ya salió de {comercio}. |
| `pedido.entregado` | comprador | Pedido entregado | Tu pedido de {comercio} fue entregado. |
| `pedido.cancelado` | comprador, si no canceló él | Pedido cancelado | Se canceló tu pedido de {comercio}. |
| `pago.confirmado` | comprador | Pago confirmado | {comercio} recibió tu pago. |
| `pago.vencido` | comprador | Venció el pago | Venció el plazo para pagar tu pedido de {comercio}. |
| `viaje.ofrecido` | el repartidor al que se le ofrece | Viaje disponible | Tenés un viaje para aceptar. |

- **Comercio** es cada persona que lo administra con permiso `pedidos`: la dueña y los miembros del equipo que lo tienen (`docs/equipo.md`). El comercio como identidad no tiene teléfono.
- Nadie recibe el aviso de lo que hizo él mismo.
- Los textos son los de la tabla, en el idioma del barrio, y los escribe el nodo. La app no los arma: si llega un tipo nuevo que no conoce, igual muestra el aviso.
- Cada nodo avisa a quien registró el dispositivo en él, por los eventos que ese nodo ve. Un comprador de otro nodo recibe el aviso de su propio nodo cuando le llega el evento federado.
- El chat (`mensaje.nuevo`) queda fuera de esta versión.

## Qué lleva el aviso

Nada personal. El aviso pasa por Apple o Google y se ve con el teléfono bloqueado, así que lleva el tipo y dónde abrir, nunca lo que pasó adentro:

- **Sí**: el tipo de evento, el id del evento, la entidad (`pedido` o `viaje` y su id), el rol de quien lo recibe, el comercio cuando el rol es `comercio`, y el nombre público del comercio en el texto.
- **No**: nombres de personas, direcciones, teléfonos, ítems, montos, el código de retiro, el texto del chat.

El contenido (`esquemas/dispositivo.json#/$defs/aviso`):

```json
{
  "titulo": "Pedido nuevo",
  "cuerpo": "Entró un pedido en Almacén Don Tito.",
  "datos": { "evento": "ev_…", "tipo": "pedido.creado", "rol": "comercio", "entidad": { "tipo": "pedido", "id": "pe_…" }, "comercio": "co_…" }
}
```

### En APNs

- `aps.alert` con `title` y `body`, `aps.sound` `default`, `aps.thread-id` el id de la entidad.
- `datos` va entero en la clave `vereda`.
- Cabeceras: `apns-push-type: alert`, `apns-priority: 10`, `apns-topic` el bundle id, `apns-collapse-id` `<rol>:<entidad.id>` (el estado nuevo de un pedido reemplaza al anterior en la pantalla), `apns-expiration` como abajo.

### En FCM (HTTP v1)

- Mensaje de datos, sin bloque `notification`: la app arma la notificación, elige el canal y pone a dónde abrir. Todos los valores son strings: `titulo`, `cuerpo`, `evento`, `tipo`, `rol`, `entidad_tipo`, `entidad_id` y `comercio` si va.
- `android.priority: HIGH`, `android.collapse_key` `<rol>:<entidad.id>`, `android.ttl` como abajo.

### Cuánto vive

`viaje.ofrecido` vive hasta `vence_oferta` del viaje: un viaje que ya pasó a otro no tiene que sonar tarde. Los demás, 24 horas.

### Al tocarlo

La app abre la pantalla de la entidad para ese rol (el pedido para el comprador, el pedido en la bandeja del comercio, los viajes ofrecidos para el repartidor) y lee el estado actual de la API. Nunca confía en que el aviso esté al día.

## Entrega

- Fuera de la transacción del evento: un push lento o caído nunca frena un pedido.
- Hasta 3 intentos en una hora ante un error de APNs o FCM que se puede reintentar (429, 5xx), respetando `Retry-After`. Después se abandona: para eso está `GET /eventos`.
- Sin orden garantizado entre avisos.

## Anuncio en el nodo

El nodo que avisa publica `push` en `/.well-known/vereda.json` (`CapacidadPush`): qué apps sabe avisar y por qué plataforma. Ausente, no avisa. La app lo lee antes de pedir el permiso: sin `push`, o sin su `app` en la lista, no lo pide.

## Costo

Cero. APNs y FCM no cobran por mensaje; el proyecto Firebase usa solo Cloud Messaging, en el plan gratuito. Con B, el relay entra en el nivel gratuito de un worker serverless durante mucho tiempo.

## Lo que necesita el publicador de la app

Para encenderlo en un nodo que manda directo (A):

- **Apple**: el Team ID; el App ID con la capacidad Push Notifications; una clave de APNs (`.p8`) y su Key ID. La misma clave sirve para desarrollo y producción, y para todas las apps del equipo.
- **Google**: un proyecto Firebase con la app Android registrada con su package, el `google-services.json` de esa app para el build, y una cuenta de servicio del proyecto con permiso para mandar por Cloud Messaging (JSON). En el proyecto, solo Cloud Messaging: sin Firestore, Storage ni nada que guarde datos, así no hay región que elegir.

El nodo arranca con cada plataforma apagada hasta que tiene sus credenciales, y las dos se encienden por separado.
