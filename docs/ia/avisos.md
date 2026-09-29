# Avisos de la IA: que te escriba primero, solo si vos querés

Normalmente tu IA habla cuando vos le hablás. Los avisos son la excepción: la IA te escribe primero, pero **solo si los prendiste**, **como mucho una vez por día** (salvo los de un pedido en curso) y **solo porque pasó algo concreto**. Nunca porque "es viernes" o porque hace rato que no pedís. **El silencio es el default.**

Es parte de la capacidad `ia` (`docs/ia/capacidad.md`): un nodo que la ofrece publica `avisos` en `ia.funciones.comprador`. Sin eso, las rutas de este documento responden `501 no_implementado`.

## Dos llaves para que te escriba

1. **La IA activa** (`PUT /ia/yo`, como siempre).
2. **Los avisos prendidos**, aparte: `PUT /ia/yo/avisos` con `activos: true`. Vienen **apagados**. Prender la IA no los prende.

Apagar cualquiera de las dos corta los avisos en el momento. Lo que ya estaba pendiente queda en la lista hasta que venza.

## Solo eventos: cinco tipos

Cada aviso nace de un hecho que el nodo puede comprobar. El nodo los evalúa **sin llamar al modelo**: comparar precios, fechas y estados no cuesta tokens, y no se cobra. Los textos los arma el nodo con plantillas.

| `tipo` | Cuándo | Default al prender |
| --- | --- | --- |
| `pedido_demorado` | Un pedido tuyo en curso pasó 20 minutos de su `eta` (la hora prometida) sin entregarse | prendido |
| `sustitucion` | El comercio te propone un reemplazo en un pedido en preparación (`item.sustitucion_propuesta`) y todavía no respondiste. Vence con la sustitución | prendido |
| `reposicion` | Algo que comprás seguido se te estaría por terminar, según tu ritmo de compra: "el café te dura unas tres semanas" | prendido |
| `vigia` | Se cumplió algo que vos pediste vigilar: "avisame cuando baje el aceite" | prendido |
| `promo_adherido` | Un comercio adherido al chat publicó una promo de algo que está en tu Libreta (una línea activa tuya nombra esa oferta o ese comercio) | **apagado** |

### Reposición: tu ritmo, no el del comercio

- Hace falta que el mismo producto (la misma oferta, o el mismo alias de tu Libreta) esté en **al menos tres pedidos entregados**.
- El nodo toma la mediana de los intervalos entre esas compras (`ritmo`) y avisa cuando pasó el 85 % de ese intervalo desde la última compra, sin un pedido nuevo del producto en el medio.
- Un aviso por ciclo: si lo descartás, o si compraste, no vuelve hasta la próxima compra.

### Vigías: los ponés vos

Un vigía es algo que le pedís a la IA que mire por vos: una oferta o un comercio, y una condición.

| `condicion.tipo` | Se cumple cuando |
| --- | --- |
| `precio_hasta` | La oferta cuesta `monto` o menos |
| `baja_de_precio` | El precio de la oferta baja al menos `porcentaje` % desde que pusiste el vigía |
| `vuelve_stock` | La oferta vuelve a estar disponible |
| `abre` | El comercio abre |
| `promo_nueva` | El comercio publica una promoción nueva |

- Los creás con tu sesión (`POST /ia/vigias`) o diciéndolo en el chat ("avisame cuando…", abajo). El modelo no pone vigías por su cuenta.
- **Vencen siempre.** `vence` es obligatorio, como mucho 90 días después de crearlo. Si no decís hasta cuándo, 30 días.
- **Disparan pocas veces.** `disparos_max` entre 1 y 3 (1 por defecto). Al llegar, el vigía queda `cumplido`.
- Hasta **10 vigías activos** por persona. El undécimo responde `422 tope_de_vigias`.
- Los evalúa el nodo con los eventos públicos que ya publica (`oferta.precio_cambiado`, `oferta.stock_cambiado`, `comercio.abierto`) y las promociones nuevas: no busca, no llama al modelo y no cuesta nada.
- Un vigía no sabe qué te importa más allá de lo que pediste. Solo mira una oferta o un comercio concreto, nunca una búsqueda abierta.

#### Desde el chat

"Avisame cuando el aceite baje de 3 mil" pone un vigía, con las mismas llaves que confirmar un pedido:

- **Tu último mensaje lo pide.** Tiene que decir "avisame cuando…" o "avisame si…" sobre un precio (que baje, que cueste tanto), el stock (que vuelva, que haya), una promo o que abra un local. "Avisame si te falta algo" no es un vigía. Lo que diga un mensaje anterior, un producto o un comercio no pone nada.
- **La condición es la que pediste.** Si hablaste de precio, el vigía es de precio; no puede ser de otra cosa. El `monto` de `precio_hasta` tiene que ser **uno que dijiste** ("3.000", "3 mil", "3 lucas"); si no dijiste cuánto, es `baja_de_precio`, con el porcentaje que dijiste o uno chico que fija el nodo.
- **Solo con tu sesión.** Un mandato nunca pone vigías, ni desde el chat ni por MCP.
- **Vence a los 30 días** si no dijiste hasta cuándo; si lo dijiste, como mucho 90.
- **Uno por turno.** Un mensaje pone como mucho un vigía.
- **La confirmación la escribe el nodo, sin modelo**: qué mira y hasta cuándo ("Listo, te aviso: …. Queda puesto hasta el 29/10."). Si tenés los avisos apagados, o el tipo `vigia` apagado, te lo dice: el vigía mira igual, pero no te escribe hasta que los prendas.
- Los topes y errores son los mismos que con `POST /ia/vigias` (10 activos, `tope_de_vigias`; `vigia_invalido`).

## Topes: pocos y duros

- **Como mucho un push por día** de `reposicion`, `vigia` y `promo_adherido`, sumando los tres (`por_dia`: 1, o 0 para no recibir ninguno y ver los avisos solo al abrir el chat). El día corre en tu `zona_horaria`.
- **Los avisos de un pedido en curso no tienen tope diario.** `sustitucion` y `pedido_demorado` son sobre un pedido que está pasando ahora: no cuentan para el tope y el tope no los frena. Sigue valiendo todo lo demás: los dos opt-in, el tipo prendido, `por_dia: 0`, un aviso por clave y la pausa por ignorados.
- **Horas de silencio.** De 22 a 9 por defecto; las cambiás en `horas_de_silencio`. Nunca suena en ese rango, salvo un `sustitucion` o un `pedido_demorado` de un pedido que **sigue activo en ese momento**.
- **Un aviso por clave.** Cada aviso tiene una `clave` que dice qué lo disparó (`pedido_demorado:<pedido>`, `reposicion:<oferta>:<última compra>`, `vigia:<vigía>:<disparo>`). La misma clave nunca genera dos avisos.
- **Si no los usás, se callan.** Después de **4 avisos seguidos ignorados** (vencieron sin que los abrieras ni los descartaras), el nodo deja de mandar pushes: `en_pausa: true`. Vuelve cuando retomás: abrís un aviso, usás el chat o los prendés de nuevo en "Tu IA".

Lo que el tope o las horas de silencio no dejan sonar **no se pierde**: el aviso queda `pendiente` y lo ves al abrir el chat, sin push. El push es lo único que se limita.

## Vida de un aviso

```
pendiente ──▶ usado        la persona lo abrió o actuó (POST /ia/avisos/{id}/usar)
     │
     ├──────▶ descartado   la persona lo sacó (POST /ia/avisos/{id}/descartar)
     │
     └──────▶ vencido      pasó `vence` sin nada de lo anterior
```

**Descartar enseña**, sin tocar tu Libreta (los avisos no son uno de sus tres caminos de escritura, `docs/ia/libreta.md`):

| `motivo` | Qué aprende |
| --- | --- |
| `ya_lo_tengo` | Reposición: arranca el ciclo de nuevo, como si hubieras comprado |
| `no_me_interesa` | No vuelve a avisar por esa misma oferta o ese mismo comercio en ese tipo por 90 días |
| `no_de_este_tipo` | Apaga ese tipo en tus preferencias. La app te lo confirma antes |
| `mal_momento` | Nada más que este aviso. Cuenta como respuesta, no como ignorado |

Sin `motivo`, es `no_me_interesa`. Un descarte nunca cuenta para la pausa por ignorados: descartar es responder.

Qué botón manda qué motivo lo decide cada app; la spec solo fija los cuatro. Lo esperable: la X que cierra el aviso manda `mal_momento` (no enseña nada), y "No me interesa" manda `no_me_interesa`. Como descartar sin `motivo` es `no_me_interesa`, una X que no manda motivo enseña más de lo que parece.

## Qué lleva el push

Lo mismo que cualquier push de Vereda (`docs/notificaciones-push.md`): **nada personal**, porque se ve con el teléfono bloqueado y pasa por Apple o Google. Nunca el producto, el precio, el monto ni el texto de tu Libreta. Solo el nombre público del comercio.

| `tipo` | Título | Cuerpo |
| --- | --- | --- |
| `pedido_demorado` | Tu pedido viene demorado | Tu pedido de {comercio} está tardando más de lo previsto. |
| `sustitucion` | Te proponen un cambio | {comercio} te propone un reemplazo en tu pedido. |
| `reposicion` | ¿Reponés? | Puede que se te esté terminando algo que comprás seguido. |
| `vigia` | Pasó lo que esperabas | Se cumplió uno de tus vigías en {comercio}. |
| `promo_adherido` | Una promo para vos | {comercio} tiene una promo de algo que te gusta. |

El detalle (qué producto, cuánto bajó) está en el aviso, que se lee con tu sesión en `GET /ia/avisos`. En el push, `datos.entidad` es `{tipo: aviso_ia, id}` y `datos.tipo` es `ia.aviso`.

## Rutas

Todas con la sesión de la persona: es consentimiento, igual que `/ia/yo`.

- `GET /ia/yo/avisos` (`verAvisosIa`) / `PUT /ia/yo/avisos` (`configurarAvisosIa`): las preferencias (`esquemas/ia-avisos.json#/$defs/preferencias`). También vienen en `GET /ia/yo`, en `avisos`.
- `GET /ia/avisos` (`listarAvisosIa`): los avisos, los pendientes primero. Filtro `estado`.
- `POST /ia/avisos/{id}/usar` (`usarAvisoIa`) y `POST /ia/avisos/{id}/descartar` (`descartarAvisoIa`, con `motivo` opcional).
- `POST /ia/vigias` (`crearVigia`), `GET /ia/vigias` (`listarVigias`), `DELETE /ia/vigias/{id}` (`borrarVigia`).

Un mandato no lee ni configura los avisos de nadie, y ningún agente externo recibe avisos ni pone vigías en esta versión. **En v1 no hay herramientas MCP para avisos ni vigías:** es a propósito, no un olvido. El evento `ia.aviso` (`docs/eventos.md`) llega solo a las sesiones de la persona.

## Datos

- Un aviso vive 90 días y después se borra. Un vigía cumplido o vencido queda 7 días en la lista y después se borra; uno activo, cuando lo borrás vos.
- `GET /yo/exportar` incluye las preferencias, los vigías y los avisos de los últimos 90 días (`esquemas/ia-avisos.json#/$defs/exportados`). En la mudanza viajan las preferencias y los vigías. Los avisos no viajan: eran de ese nodo.
- `POST /yo/borrar` los borra con el resto de la cuenta. Los pushes se cortan en el momento, igual que los dispositivos (`docs/notificaciones-push.md`).

## Errores

| Qué pasa | Estado | Código |
| --- | --- | --- |
| El nodo no ofrece `avisos` | 501 | `no_implementado` |
| Más de 10 vigías activos | 422 | `tope_de_vigias` |
| `vence` en el pasado o a más de 90 días, o `porcentaje` fuera de 1 a 90 | 422 | `vigia_invalido` |
| La condición no corresponde (precio sobre un comercio, `abre` sobre una oferta) | 422 | `vigia_invalido` |
| El aviso ya no está pendiente | 409 | `aviso_no_pendiente` |
| No existe o no es tuyo | 404 | `no_encontrado` |

## Lo que un nodo NO puede hacer

- Mandar un aviso sin los dos opt-in, o de un tipo que la persona apagó.
- Mandar más de un push por día de `reposicion`, `vigia` y `promo_adherido`, o sonar en horas de silencio (salvo `sustitucion` o `pedido_demorado` de un pedido que sigue activo).
- Inventar un tipo de aviso, o escribir por reloj ("hace mucho que no pedís", "es viernes").
- Usar el modelo para decidir si avisa.
- Mandar un `promo_adherido` que no coincide con la Libreta, o de un comercio no adherido.
- Poner datos personales en el push.
- Seguir mandando pushes después de 4 ignorados seguidos.
