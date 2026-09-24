# Equipo del comercio

Un local no lo atiende una sola persona. La dueña abre, el encargado cierra, alguien atiende los pedidos del mediodía y otra persona carga la carta los domingos. El equipo es eso: las personas que administran un comercio además de su dueña, cada una con su rol y con lo que puede hacer.

Tres reglas lo sostienen:

- **Nadie aprueba a nadie.** Cada comercio arma su equipo. Ni el operador del nodo ni nadie habilita a un colaborador.
- **Cada uno con su clave.** Un miembro entra al nodo con su propia identidad, la de su clave (`docs/acceso.md`). Nadie comparte la clave de la dueña ni la del comercio.
- **Todo queda a su nombre.** Lo que hace un miembro lo registra el nodo con su identidad: el `actor` de cada paso del `historial` de un pedido es la persona que aceptó, preparó o entregó, no el comercio. Los objetos del comercio (una reseña que responde, un pedido que firma) siguen firmados con la clave del comercio, como siempre.

Esquema en `esquemas/equipo.json`; rutas en `openapi.yaml` (`verEquipo`, `invitarAlEquipo`, `revocarInvitacion`, `aceptarInvitacion`, `cambiarMiembro`, `sacarDelEquipo`); herramientas MCP `equipo_ver`, `equipo_invitar`, `equipo_aceptar`, `equipo_cambiar` y `equipo_sacar`.

## La dueña y los miembros

**La dueña** es la identidad que administra el comercio desde siempre: la sesión que lo dio de alta, o quien lo ganó en un reclamo (`docs/identidad-y-verificacion.md`). Puede todo, incluido exportar, y nadie la saca ni le cambia los permisos. No figura como miembro: el equipo la nombra en `duena`.

**Un miembro** es una persona con un `rol` y sus `permisos`:

- El **rol** es como lo llama el comercio, en texto libre: "encargado", "atención", "despacho", "catálogo", "contaduría". No habilita nada por sí mismo. Las apps sugieren algunos con permisos típicos, sin obligar a ninguno.
- Los **permisos** dicen qué puede hacer. Son cinco, y alcanzan para todo lo que hoy hace quien administra un comercio:

| Permiso | Qué puede |
| --- | --- |
| `pedidos` | La bandeja, aceptar y rechazar, resolver ítems, marcar listo, entregar, asignar repartidor, transferencias y rendiciones, leer los pedidos y viajes del comercio |
| `catalogo` | Ofertas, stock, promociones y fotos |
| `numeros` | Las métricas del comercio |
| `datos` | La ficha (horarios, abierto ahora, modalidades, cobro, envíos, política de datos, `clave_cifrado`), el aporte al nodo, vinculaciones y atestaciones, y responder reseñas y denuncias |
| `equipo` | Invitar, cambiar rol y permisos, y sacar gente |

**Exportar el comercio es solo de la dueña.** El paquete lleva los datos de los compradores; que salgan del nodo es una decisión de quien responde por ellos.

Qué permiso pide cada operación lo dice `x-permiso-equipo` en `openapi.yaml`: la lista de permisos que alcanzan (con uno basta), `[]` para cualquier miembro y `[duena]` para la dueña sola. `validar.py` falla si una operación con `administrar` no lo dice.

Roles típicos, como sugerencia:

| Rol | Permisos |
| --- | --- |
| encargado | `pedidos`, `catalogo`, `numeros`, `datos`, `equipo` |
| atención / despacho | `pedidos` |
| catálogo | `catalogo` |
| contaduría | `numeros` |

## Invitar

```
dueña o miembro con 'equipo'                 nodo                       persona invitada
  |-- POST /comercios/{id}/equipo/invitaciones ->|                                |
  |   { rol, permisos, vence_en_horas? }         |  guarda el hash del código     |
  |<- 201 { id, codigo, enlace, vence, … } ------|                                |
  |   le pasa el código o el QR, en mano o por mensaje ------------------------->|
  |                                              |<-- POST /equipo/aceptar -------|
  |                                              |    { codigo }, con SU sesión   |
  |                                              |--- 201 miembro --------------->|
```

- **Un solo uso, con vencimiento.** A las 72 horas si no se dice otra cosa, nunca más de 7 días. El código tiene al menos 128 bits de azar y el nodo guarda solo su hash.
- **El código se ve una vez.** Viene en la respuesta de `invitarAlEquipo` y nunca más, ni para quien lo creó. `enlace` es el mismo código listo para un QR: `vereda://equipo?nodo=<dominio>&codigo=<codigo>`. La app lo abre y llama a `aceptarInvitacion` en ese nodo. El nodo no dibuja pantallas: no hay página de invitación.
- **Lo acepta quien tenga el código.** Por eso se comparte en mano o por mensaje, y se anula con `revocarInvitacion` si se mandó a quien no era. Quien acepta entra con su identidad, la de su sesión.
- **Solo se da lo que uno tiene.** Un miembro con `equipo` y `pedidos` invita con `pedidos`, no con `catalogo`: 403 `sin_permiso`, con `detalle.falta`. La dueña da cualquiera.

## Cambiar y sacar

- **Cambiar** (`cambiarMiembro`): con `equipo`, y solo para dar o quitar permisos que uno tiene. Nadie se cambia sus propios permisos: se los cambia otro, o se va.
- **Sacar** (`sacarDelEquipo`): con `equipo`. Cualquier miembro puede irse solo, sin permiso.
- **La dueña no se toca.** Ni cambiarla ni sacarla: 403 `sin_permiso`. Un comercio cambia de dueña solo por un reclamo, y un reclamo resuelto vacía el equipo y anula sus invitaciones, igual que revoca los mandatos de la dueña anterior: la nueva dueña arma el suyo.

**Sacar corta en el acto.** El nodo decide en cada llamada quién administra: no hay un permiso guardado en un token que haya que revocar aparte. Desde la llamada siguiente, la persona que salió recibe 403 `no_es_el_dueno` en ese comercio, y el comercio ya no aparece en su `GET /yo/comercios`. Lo mismo un cambio de permisos: rige desde la próxima acción.

## Agentes: nunca más que su persona

Un miembro puede darle a un agente un mandato `administrar`, como la dueña (`esquemas/mandato.json`). El mandato actúa en su nombre, así que en cada comercio el agente puede exactamente lo mismo que la persona: todo si es la dueña, sus permisos si es del equipo, nada desde que la sacan. El nodo no guarda permisos en el mandato: los mira en el equipo en cada llamada, y así el techo no se puede desincronizar.

## Quién administra, en cada llamada

Para una operación sobre un comercio, el nodo resuelve:

1. Si quien llama (o el otorgante del mandato) es la dueña: sigue.
2. Si es miembro y tiene alguno de los permisos de `x-permiso-equipo` de la operación: sigue.
3. Si es miembro sin ese permiso: 403 `sin_permiso`, con `detalle.falta`.
4. Si no es ni una cosa ni la otra: 403 `no_es_el_dueno`, como siempre.

Un comercio sin equipo se comporta exactamente como antes: la dueña sola. Un nodo que no implementa equipos responde `501 no_implementado` en las rutas de equipo y sigue siendo conforme en todo lo demás.

## Errores

| Qué pasa | Estado | Código |
| --- | --- | --- |
| Quien llama no es la dueña ni está en el equipo | 403 | `no_es_el_dueno` |
| Está en el equipo pero le falta el permiso, quiere dar uno que no tiene, o quiere tocar a la dueña | 403 | `sin_permiso` |
| El código no existe, ya se usó, se anuló o venció (sin decir cuál) | 410 | `invitacion_invalida` |
| Quien acepta ya es la dueña o miembro | 409 | `ya_es_miembro` |
| Rol vacío o de más de 40 caracteres, permisos vacíos o desconocidos | 422 | `documento_invalido` |

## Privacidad

El equipo no es público y no se federa: lo ven solo quienes administran el comercio. La ficha pública no dice quién trabaja en un local. El historial de un pedido sí nombra a la persona que hizo cada paso, y lo leen las partes del pedido, como hoy.
