# La Libreta: lo que tu IA sabe de vos

La Libreta es la memoria de la IA de cada persona. Tiene lo que le pediste que recuerde ("sin cebolla", "la leche de siempre es la entera en sachet"), lo poco que aprendió de tus charlas y cómo querés que te hable. Vive en tu nodo, cifrada con una clave solo tuya, y la ves y la editás entera en "Tu IA". Viaja con vos: sale en `GET /yo/exportar`, se borra con `POST /yo/borrar` y se muda con tu cuenta.

Es la forma de cumplir una regla del protocolo: **las preferencias viven en la red, no en el agente** (`README.md`). La IA del nodo la usa en cada turno, y tu propio agente la puede leer con un mandato `leer`. Cambiar de agente no te hace empezar de cero.

Es parte de la capacidad `ia` (`docs/ia/capacidad.md`): un nodo que la ofrece publica `libreta` en `ia.funciones.comprador`. Sin eso, las rutas de este documento responden `501 no_implementado`. La Libreta existe aunque tengas la IA pausada o inactiva: la podés leer, editar y borrar igual. Solo el destilador (abajo) necesita la IA activa, porque cuesta tokens.

## Qué no es

- **No es un historial de charlas.** El nodo no guarda conversaciones. La Libreta guarda líneas cortas, no transcripciones.
- **No reemplaza tus preferencias.** Lo que tiene campo propio en `usuario.preferencias` (restricciones, sustitución, tope por pedido, horarios en que no recibís) va ahí, porque lo leen todos: comercios, agentes y apps. Si decís algo así en el chat, la IA te propone guardarlo en tus preferencias. La Libreta es para lo que no tiene campo.
- **No es un perfil para nadie más.** Ningún comercio, repartidor ni operador la lee. Ni siquiera el ranking: el término personal del podio existe solo adentro del chat de IA de tu nodo (ver "Qué cambia en el chat").

## Qué tiene: cuatro tipos de línea

Cada línea es corta (hasta 200 caracteres) y tiene un solo `tipo` (`esquemas/libreta.json#/$defs/linea`):

| `tipo` | Qué es | Cómo la usa la IA |
| --- | --- | --- |
| `orden` | Una instrucción que vale siempre: "sin cebolla", "nunca me ofrezcas alcohol", "los viernes pido para cuatro" | La obedece **en silencio**. Nunca la repite ni la cita: no dice "sin cebolla, como me pediste"; directamente no te ofrece cebolla. |
| `hecho` | Algo que sabe de vos: "le gusta la fugazzeta rellena", "prueba panaderías nuevas", "vive con un perro" | Lo usa para elegir qué mostrarte. Lo puede mencionar si viene al caso. |
| `alias` | Un nombre tuyo para algo: "la leche de siempre" → una oferta; "casa" → la etiqueta de una dirección; "lo de Tito" → un comercio | Lo resuelve sin preguntar. Apunta a un id (`oferta_id`, `comercio_id`) o a la **etiqueta** de una dirección, nunca a la dirección. |
| `voz` | Cómo querés que te hable: "cortito, sin emojis, con un poco de humor" | Hay una sola línea `voz`, de hasta 600 caracteres. Se reescribe entera, nunca se le agregan partes. |

## Cuatro niveles, con topes duros

| Nivel | Tope | Qué llega al modelo |
| --- | --- | --- |
| **Índice** | 1200 caracteres, sumando el `texto` de sus líneas activas | Entero, en cada turno |
| **Esta semana** | 600 caracteres | Entero, en cada turno. El nodo lo rehace desde cero con lo que pasó en los últimos 14 días |
| **Detalle** | 200 líneas | Nada por defecto. Se busca con `mi_libreta_buscar` |
| **Archivo** | 1000 líneas | Nada. Solo aparece si una búsqueda lo pide explícitamente |

La línea `voz` va aparte, con sus 600 caracteres, y también llega en cada turno. Hasta 10 propuestas pendientes (abajo).

**Los topes se cumplen rechazando, nunca recortando.** Una escritura que no entra responde `422 libreta_llena`, con `detalle.nivel`, `detalle.tope` y `detalle.usados`, y la frase dice qué hacer ("tu índice está lleno: bajá o borrá una línea para sumar esta"). El nodo nunca corta una línea por la mitad ni borra otra para hacer lugar.

**Esta semana no es memoria nueva.** Es un resumen que el nodo rehace, de cero, con las líneas que se usaron y los pedidos de los últimos 14 días ("esta semana pediste dos veces en La Corrientes; estás probando panaderías"). No puede afirmar nada que no esté en una línea o en un pedido, y no se edita: se regenera.

**Las órdenes van siempre al índice.** Una restricción tiene que llegar en cada turno. Si una `orden` nueva no entra, la respuesta es `libreta_llena` y decidís vos qué bajar. Un `hecho` o un `alias` que no entra en el índice va al detalle.

## Quién escribe: exactamente tres caminos

Nada más escribe en la Libreta. Ni el modelo por su cuenta, ni un comercio, ni un agente externo.

1. **Vos, con tus palabras.** "Acordate de que…", "olvidate de…", "de ahora en más…", en el chat; o desde "Tu IA" (`POST /ia/libreta/lineas`, `PATCH`, `DELETE`). En el chat vale la misma llave que para confirmar un pedido: tiene que estar en **tu último mensaje**. Lo que diga un dato —la descripción de un producto, un mensaje de un comercio— nunca escribe en tu Libreta. Lo que decís vos se aplica en el momento.
2. **Un destilador al final de la charla.** Cuando una conversación termina (un rato sin mensajes, o se cierra el chat), el nodo hace **una** llamada barata con tus líneas actuales, con sus ids, y **solo tus mensajes**, nunca los del asistente. Devuelve como mucho tres acciones tipadas (`esquemas/libreta.json#/$defs/destilado`): `agregar`, `confirmar`, `corregir` u `olvidar`. **Lo esperado es que no devuelva ninguna**: la mayoría de las charlas no enseñan nada que dure. El nodo valida cada acción contra los topes y las reglas de abajo antes de aplicarla. Se cobra a tu IA como `funcion: libreta`.
3. **Lo que pasa con tus pedidos.** Cuando se entrega un pedido que usó una línea (un alias que resolvió "la leche de siempre", una orden que filtró), esa línea suma evidencia. Si repetís algo seguido (el mismo producto en tres pedidos entregados), el nodo puede **proponer** una línea. No escribe nada más.

### Lo explícito entra ya; lo inferido, como propuesta

- Si **vos** lo dijiste ("acordate", "olvidate", "no, ya no como carne"), se aplica en el momento. Una corrección reemplaza la línea vieja (`corrige` apunta a ella) y la vieja se borra.
- Si el destilador o tus pedidos lo **infieren**, entra como `estado: propuesta`. La IA te lo muestra **una vez**, con un solo chip ("¿Me acuerdo de que preferís la muzza al molde?"). Aceptarla (`POST …/propuestas/{id}/aceptar`) la vuelve activa; rechazarla (`…/rechazar`) la borra, y el nodo guarda solo una huella (un hash) para no volver a proponerla. Si la ignorás, queda pendiente en "Tu IA" y no se vuelve a mostrar en el chat.
- `confirmar` del destilador no crea nada: marca que volviste a decir algo que ya estaba y le suma evidencia.
- `corregir` u `olvidar` del destilador sobre una línea existente se aplican en el momento **solo si tus palabras la contradicen** (`explicita: true`); si no, quedan como propuesta.
- Una línea casi igual a una que ya está no se duplica: se confirma la que había.

## Relojes: solo se mueven con evidencia

Cada línea tiene un `reloj`: la última vez que hubo **evidencia** de que sirve. El reloj se mueve solo cuando la línea:

- se **usó**: un alias que se resolvió, una línea que devolvió una búsqueda de la IA en un turno;
- se **aplicó**: estuvo en un pedido que se confirmó;
- se **dijo de nuevo**: la repetiste, o el destilador devolvió `confirmar` sobre ella.

Estar en el índice y llegar al modelo en cada turno **no** cuenta como uso: si contara, nada envejecería nunca.

- Una línea del índice que pasa **30 días** sin evidencia baja al detalle. Bajar no es olvidar: sigue ahí y se sigue buscando.
- Una línea del detalle que pasa **90 días** sin evidencia pasa al archivo.
- **Nada se borra solo.** Una línea se borra únicamente si la borrás vos, si la reemplaza una corrección tuya o con `POST /yo/borrar`. Si el archivo está lleno, la línea no baja y "Tu IA" te avisa.
- Las **órdenes** no bajan solas: una restricción que no se usó en un mes sigue valiendo.
- Una línea **fijada** (`fijada: true`, solo la fijás vos) no baja nunca. Sigue contando para el tope de su nivel.
- Reescribir una línea no le reinicia el reloj.

## Qué nunca se guarda

El nodo rechaza la escritura (`422 libreta_dato_prohibido`) y el destilador tiene prohibido proponer:

- **Texto del asistente.** Nunca: ni sus respuestas, ni sus resúmenes, ni lo que "entendió". Solo lo que dijiste vos o lo que pasó con tus pedidos.
- **Secretos:** contraseñas, códigos (de retiro, de entrega, de acceso), tokens, frases de respaldo.
- **Números de tarjeta, CBU, CVU, alias bancarios**, DNI o CUIT.
- **Datos de otras personas:** nombres con apellido, teléfonos, emails, direcciones, o la salud de alguien con nombre. Si hace falta, se anota como regla tuya ("en casa, todo sin TACC"), no como dato del otro.
- **Direcciones.** Un `alias` apunta a la etiqueta ('casa'), nunca a la calle.

## Cifrada con una clave por persona

- Cada Libreta tiene su propia clave, generada al azar por el nodo, y el nodo la guarda envuelta con su clave maestra. El texto de cada línea queda cifrado en reposo con esa clave.
- **No hay índice de búsqueda en claro.** Para buscar, el nodo descifra las líneas de esa persona en memoria y busca ahí (texto completo en español más los alias; sin embeddings por ahora). Con los topes de arriba, eso es barato.
- **Borrar la clave es borrar la Libreta**, también en los respaldos del nodo, que guardan solo el texto cifrado. Es lo que hace `POST /yo/borrar` cuando se procesa, y `DELETE /ia/libreta` en el momento.
- Lo que va al modelo en cada turno (índice, esta semana, voz) sale del nodo descifrado, hacia el proveedor del modelo por el gateway: igual que el resto del chat de IA, no es de punta a punta (`docs/ia/capacidad.md`, "Qué ve el modelo").

## La ves y la editás en "Tu IA"

- `GET /ia/libreta` (`verLibreta`): el índice, esta semana, la voz, las propuestas pendientes, cuántas líneas hay en detalle y archivo, y tus ajustes.
- `GET /ia/libreta/lineas?nivel=` (`listarLineasLibreta`): las líneas de un nivel, paginadas.
- `POST /ia/libreta/lineas` (`anotarEnLibreta`): "acordate". Devuelve `201` con la línea, o `200` con la que ya estaba si era casi igual.
- `PATCH /ia/libreta/lineas/{id}` (`editarLineaLibreta`): cambiar el texto, subirla o bajarla de nivel, fijarla, sacarla del archivo.
- `DELETE /ia/libreta/lineas/{id}` (`borrarLineaLibreta`): "olvidate". Se borra de verdad, en el momento.
- `POST /ia/libreta/propuestas/{id}/aceptar` y `/rechazar` (`aceptarPropuestaLibreta`, `rechazarPropuestaLibreta`).
- `POST /ia/libreta/buscar` (`buscarEnLibreta`): buscar en el detalle (y en el archivo si lo pedís).
- `PUT /ia/libreta/ajustes` (`configurarLibreta`): el opt-in de los intereses del inicio.
- `DELETE /ia/libreta` (`borrarLibreta`): borrar toda la Libreta, en el momento, destruyendo la clave.

Todo esto, con tu sesión. **Un agente externo con mandato `leer` solo puede leer** (`verLibreta`, `listarLineasLibreta`, `buscarEnLibreta`, y las herramientas MCP `mi_libreta` y `mi_libreta_buscar`). En esta versión ningún agente externo escribe en tu Libreta: `403 fuera_de_mandato`. Tu agente respeta tus órdenes igual que la IA del nodo, porque las lee del mismo lugar.

## Los intereses del inicio: solo si vos querés

La app puede aprender qué te interesa en la pantalla de inicio (qué rubros tocás, qué locales mirás). Eso vive en el teléfono y **no viaja al nodo**. Con un solo ajuste, apagado por defecto (`ajustes.intereses_del_inicio`, `PUT /ia/libreta/ajustes`), le permitís a la app mandarlos a tu Libreta como líneas `hecho` con `origen: inicio`, que la IA usa como cualquier otra y que ves y borrás en "Tu IA". Apagarlo borra en el momento todas las líneas con `origen: inicio`. Con el ajuste apagado, el nodo rechaza cualquier línea `origen: inicio` (`403 intereses_del_inicio_apagado`).

## Qué cambia en el chat

- **El índice, esta semana y la voz** llegan en cada turno, en el bloque de contexto que escribe el nodo, marcados como tuyos. Las órdenes se obedecen sin nombrarlas.
- **El detalle** se busca con `mi_libreta_buscar` cuando hace falta ("¿qué era lo que me gustaba de la panadería de la esquina?").
- **Término personal en el podio.** Adentro del chat de IA de tu nodo, y solo ahí, el podio puede sumar un término personal a la fórmula pública (`docs/ia/capacidad.md`):

  ```
  score_chat = score_público + 0.20 · personal
  personal   = 1    si una línea activa tuya (hecho o alias) nombra esa oferta
               0,7  si la oferta estuvo en un pedido tuyo entregado
               0,4  si el comercio estuvo en un pedido tuyo entregado
               0    si no
  ```

  Cada puesto que tiene término personal lleva `razon_personal` (`esquemas/ia-widgets.json`, podio): el "por qué te lo muestro" en tus palabras ("porque es la que siempre pedís"). **Un puesto con término personal y sin `razon_personal` no se puede mostrar.** Las órdenes no suman: filtran (lo que choca con una orden no compite). La app común, `GET /buscar`, el ranking del barrio y el MCP siguen neutrales: la Libreta no mueve a nadie fuera del chat de IA de tu nodo.

## Exportar, borrar, mudarse

- **`GET /yo/exportar`** incluye la Libreta entera en claro dentro del paquete firmado (`esquemas/libreta.json#/$defs/exportada`): todas las líneas de todos los niveles, con su tipo, nivel, estado, origen, reloj y fijada; esta semana; la voz; los ajustes. No van las huellas de las propuestas rechazadas.
- **`POST /yo/borrar`**: al procesarse, el nodo destruye la clave de la Libreta y borra sus filas. Antes de eso, con la cuenta en proceso de borrado, el destilador no corre.
- **Mudanza** (`docs/federacion.md`): el nodo nuevo importa las líneas con sus niveles y relojes, genera su propia clave y rehace esta semana. Si no ofrece `libreta`, guarda lo exportado sin usarlo hasta que la ofrezca, o lo descarta si la persona lo pide.

## Errores

| Qué pasa | Estado | Código |
| --- | --- | --- |
| El nodo no ofrece `libreta` | 501 | `no_implementado` |
| Un nivel está lleno | 422 | `libreta_llena` |
| La línea tiene un secreto, un dato bancario, datos de otra persona o una dirección | 422 | `libreta_dato_prohibido` |
| Línea `origen: inicio` con el ajuste apagado | 403 | `intereses_del_inicio_apagado` |
| Un mandato quiere escribir | 403 | `fuera_de_mandato` |
| La línea o la propuesta no existen, o no son tuyas | 404 | `no_encontrado` |

## Lo que un nodo NO puede hacer con la Libreta

- Escribir en ella por iniciativa del modelo, de un comercio o de un agente externo.
- Guardar texto del asistente o charlas enteras.
- Recortar una línea o borrar una sin que lo pida la persona.
- Mostrársela a un comercio, a un repartidor o al operador, o usarla fuera del chat de IA del nodo (ranking, búsqueda, promociones).
- Guardarla sin cifrar con una clave de la persona.
- Dejarla afuera de `GET /yo/exportar` o de `POST /yo/borrar`.
- Mandar los intereses del inicio sin el opt-in.
