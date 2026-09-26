# Registro público

Salvaguarda S10 de `docs/antifraude.md`. Vereda no es juez, pero el nodo sí escribe hechos que
cambian lo que ven otros: que un pedido quedó "no vino", que un comercio cambió su cuenta de cobro,
que una vinculación se cayó. El registro público es la lista de esos hechos, en orden, firmada y
encadenada, para que cualquiera compruebe que el nodo no inventa, no reescribe y no esconde lo que
ya anotó.

`GET /registro` es público, sin token y cacheable. MCP: `ver_registro`. En las apps es un enlace
desde "Cómo se calcula" a "Qué registra este nodo", sin pantalla nueva.

## Qué se anota

Solo los hechos que cambian lo que ven otros. Lo que queda entre las partes de un pedido (el chat,
una propina) no entra.

| `tipo` | Cuándo | `autor` | `hecho` | `datos` |
| --- | --- | --- | --- | --- |
| `comercio.cuenta_cobro_cambiada` | El comercio cambió el alias o el titular de `privado.cuenta_cobro` (S3, `docs/identidad-y-verificacion.md`, cuenta de cobro) | quien la cambió | — | nada: nunca el alias |
| `pago.revertido` | El destinatario marcó un cobro confirmado como revertido (S2, `revertirTransferencia`) | quien lo marcó | `pago.reversion`, si la firmó | `metodo` |
| `pedido.no_vino` | Se cerró un pedido como `no_retirado` o `no_recibido` (`docs/carrito-y-reserva.md`, "No vino") | quien lo marcó | `no_vino.constancia` | `motivo`, `rol` |
| `pedido.descargo` | El comprador dejó su versión ("Yo sí fui") | el comprador | `no_vino.descargo` | nada: nunca el texto |
| `denuncia.recibida` | Se publicó una denuncia de suplantación (`docs/identidad-y-verificacion.md`, punto 5) | el denunciante | la denuncia | `reclama`: el tipo de vinculación |
| `denuncia.respondida` | El denunciado respondió | el denunciado | la respuesta | nada |
| `vinculacion.caida` | Una vinculación verificada pasó a `caida` al comprobarse | — (el nodo) | — | `vinculacion_tipo` |
| `federacion.bloqueo` | El nodo bloqueó a otro nodo por un criterio escrito (`docs/federacion.md`, "Lista de bloqueo") | — (el nodo) | — | `nodo_bloqueado`, `criterio`, `evidencia`, `hasta` |
| `federacion.desbloqueo` | El bloqueo venció | — (el nodo) | — | `nodo_bloqueado`, `motivo: vencido` |

Un nodo que todavía no produce un hecho (por ejemplo, porque no implementa cobros revertidos) no lo
anota. No agrega tipos propios: un tipo que no está en `esquemas/registro.json` no es parte del
registro.

## Reglas

- **En la misma transacción que el hecho.** Si el hecho quedó escrito, su entrada también; si la
  transacción se deshace, ninguno de los dos existe. Nunca hay un hecho sin entrada ni una entrada
  sin hecho.
- **Solo se agrega.** No hay borrado, edición ni retención: el registro no tiene datos personales,
  así que no hay nada que borrar. Borrar una cuenta (`/yo/borrar`) no toca sus entradas; su `ref`
  queda y no dice nada a quien no conocía la identidad.
- **Sin datos personales.** Identidades, pedidos, denuncias y vinculaciones van como `ref` opaca
  (`docs/claves-y-firmas.md`, "Registro público"). Nunca montos, textos, alias, teléfonos,
  direcciones ni el valor de una vinculación.
- **El nodo firma cada entrada** y la encadena con la anterior. Lo que firmó una persona va además
  con su huella y su firma (`hecho`), sin el contenido.
- **Orden.** `secuencia` sin huecos, desde 1; `instante` no decrece.

## Formato y paginado

`GET /registro?desde=1&limite=100` → `esquemas/registro.json#/$defs/pagina`: las entradas desde
`desde` en orden, la `cabeza` del registro (secuencia y hash de la última) y `siguiente` si hay
más. El formato de la cadena, la firma, las referencias y cómo auditar están en
`docs/claves-y-firmas.md`, "Registro público". Vector en `ejemplos/vectores-firma.json` →
`registro`.

## Lo que no hace

- No puntúa, no bloquea y no esconde a nadie. Es un registro de hechos; lo que cada uno haga con
  ellos lo decide quien mira.
- No reemplaza a los objetos firmados: el pedido, la denuncia y la reseña siguen siendo la
  evidencia. El registro prueba que existieron y que nadie los cambió.
- No prueba que el nodo anotó todo: un nodo puede callarse un hecho. Lo que no puede es sacar o
  cambiar lo que ya anotó sin que se vea.
