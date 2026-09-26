# Protocolo Vereda

**Vereda. Sin nadie en el medio.**

Un protocolo abierto para comprar y recibir de los comercios de tu barrio: restaurantes, almacenes, verdulerías, supermercados, catering, productores. Sin dueño, sin comisión escondida, sin call center. El dinero va directo del que compra al que vende y al que lleva. La red no custodia plata, no guarda más datos que los necesarios y no arbitra nada: garantiza que lo firmado por alguien lo firmó él, que cada prueba de identidad se puede rehacer y que cada reseña corresponde a un pedido real. Lo demás es entre vecinos.

Es un protocolo, no una app. Cualquiera puede correr un nodo, construir un cliente o enchufar un agente. La filosofía es la del email, la web o Ethereum: sin permiso, con identidad propia, federado. Sin blockchain ni moneda: los pesos viajan por el sistema de pagos argentino (Transferencias 3.0, QR interoperable).

## En una página

- **Oferta, no producto.** Un comercio describe cualquier cosa que venda y cualquier forma de venderla con diez piezas componibles: precio (fijo, por kg, por persona, por período, a cotizar), grupos de opciones, variantes, componentes, cantidad, disponibilidad, modalidad, atributos abiertos. Seis tipos base: `producto`, `pesable`, `preparado`, `compuesto`, `servicio`, `recurrente`.
- **La entrega es configurable.** Seis modalidades que el comercio activa y precia: inmediata, franja, consolidada (junta pedidos y traslada el ahorro), ronda (entrega programada a un lugar, como el barrio cerrado los viernes), punto de entrega, retiro.
- **Compra colectiva.** Pedido grupal con link (el edificio, la oficina): cada uno paga lo suyo, un solo envío. Rondas que los propios vecinos abren.
- **Suscripciones.** Viandas semanales, catering mensual, la compra quincenal: una regla de repetición, ventana de edición, y cada ocurrencia es un pedido común.
- **Supermercado de verdad.** Listas persistentes con ítems genéricos que se resuelven contra comercios, catálogo maestro por EAN, pesables con monto final, sustituciones con preferencia declarada, franjas con cupo.
- **Promociones que cualquiera puede calcular.** 2x1, 3x2, segunda unidad al 70 %, precio por cantidad, escalera por total de compra, envío bonificado, descuento por efectivo o por retiro, y puntos por volver al mismo comercio. Son públicas, se calculan con un algoritmo público y no compran posición en el ranking.
- **Agentes primero.** Mandatos firmados con topes de gasto, carrito que se valida paso a paso y dice qué falta en español, preferencias que viven en la red y no en el agente, agentes de comercio que negocian con agentes de usuario. Servidor MCP como primera interfaz.
- **El repartidor también.** Cualquiera se da de alta solo, declara zona, vehículo y cómo cobra, y reparte al instante. Cada comercio elige si usa el pool público, sus propios repartidores o el que eligió el comprador, y en qué orden; al repartidor le paga directo quien lo contrató. Ver `docs/repartidores.md`.
- **El comercio se administra solo.** Se da de alta y queda activo al instante: nadie habilita a nadie, no hay revisión ni sello de autoridad. Desde la misma API publica y edita su ficha, su catálogo y sus promociones, trabaja sus pedidos, mira sus métricas agregadas y se lleva todo firmado cuando quiere.
- **Los datos del comercio son del comercio.** Cada comercio fija en su ficha pública cuántos días retiene los datos de un pedido y si guarda lista de clientes (con consentimiento de la persona). El protocolo promueve un default —90 días, sin lista— y le pone el sello `estandar` a quien lo cumple; no obliga a nadie, y el usuario elige sabiendo. Ver `docs/datos-y-privacidad.md`.
- **Reputación contextual, firmada y portable.** Reseñas solo sobre pedidos entregados, firmadas con la clave del autor, sin edición ni borrado, y te las llevás a otro nodo. La reputación que ves se calcula para vos con una fórmula publicada: pesa más el vecino que volvió a comprar que la identidad creada ayer del otro lado de la ciudad, y las campañas se marcan con un criterio determinista que cualquiera puede rehacer. Ver `docs/resenas.md`.
- **Dinero directo.** La red genera la referencia de cobro y confirma. Nunca custodia, nunca reembolsa, nunca retiene.
- **El nodo se sostiene como el código abierto.** Sin comisión: el comercio elige si aporta al operador del nodo, por pedido o por mes, el comprador puede dejarle una propina, todo por transferencia directa, y el nodo publica mes a mes lo que recibió y en qué lo gastó. Aportar o no no cambia nada. En cada pedido, la línea "Para el nodo" está siempre, aunque sea 0. Ver `docs/sostenimiento.md`.
- **Nadie verifica a nadie; todo se prueba.** No hay tilde azul ni sello de Vereda. Un comercio prueba que su dominio, su Instagram, su WhatsApp, su local y su cuenta de cobro son suyos publicando un código que cualquiera puede ir a mirar; los clientes atestiguan el local escaneando un QR; los duplicados y los comercios del mismo dueño se muestran a la vista, una denuncia de suplantación es pública y firmada, y quien tiene la prueba puede reclamar una ficha que armó otro. Ninguna de esas cosas la resuelve una persona ni un agente: la resuelve la evidencia, sola. Ver `docs/identidad-y-verificacion.md`.
- **Algoritmos públicos.** Ranking y despacho están en `docs/ranking-y-despacho.md`, el peso de cada reseña en `docs/resenas.md`. Nadie puede pagar para aparecer primero ni para subir su reputación.
- **Federación desde el día uno.** Identidad `actor@nodo`, pedidos firmados entre nodos, sin registro central.

## Qué hay acá

| Carpeta | Contenido |
| --- | --- |
| `esquemas/` | 28 esquemas JSON (draft 2020-12): acceso y respaldo de la clave, comercio, equipo del comercio, oferta, promoción, modalidad, carrito, pedido, pago, sostenimiento del nodo, repartidor, usuario, reseña, denuncia, reclamo, suscripción, lista, catálogo maestro, ronda, grupo, viaje, mandato, mensaje, cotización, calles de la zona, evento, error, comunes |
| `openapi.yaml` | La API abierta, 112 rutas: `/acceso` en la raíz del dominio y el resto bajo `/v1`. Apps y agentes usan las mismas |
| `mcp/herramientas.json` | Las 76 herramientas del servidor MCP —del lado del usuario, del comercio y del repartidor—, con descripciones para asistentes |
| `ejemplos/` | Una pizzería, una verdulería con cuatro modalidades, un catering a cotizar, viandas semanales, un supermercado con EAN, un pedido con pesables y sustituciones, un mandato, una ronda al barrio cerrado, un pedido grupal de edificio, `vectores-firma.json` con los vectores de prueba de firma y `vectores-acceso.json` con los del acceso y el respaldo con frase |
| `docs/` | Acceso (desafío firmado, código por mensaje, la clave en el dispositivo y el respaldo con frase), federación (con mudanza, disputas y catálogo maestro), claves y firmas, eventos y webhooks, ranking y despacho, repartidores (asignación, responsabilidad, cobro y reputación), reseñas y reputación contextual, vocabulario sugerido de atributos por rubro, identidad y verificación sin autoridad (vinculaciones, duplicados, denuncias, reclamo de fichas), carrito y reserva, equipo del comercio (roles y permisos de quienes lo administran), promociones, mandatos (qué hizo tu agente), datos y privacidad, sostenimiento del nodo (aportes, propinas y gastos publicados), imágenes y video (clips cortos que no le cuestan al nodo), IA nativa opcional del nodo (`docs/ia/capacidad.md`), el mapa (las calles de la zona, servidas por el nodo desde OpenStreetMap), diseño de la suite de conformidad (fase 1) |
| `validar.py` | Valida los ejemplos contra los esquemas, `openapi.yaml` contra OpenAPI 3.1, reproduce byte a byte el JCS y los bytes de los vectores de firma, acceso y respaldo, y verifica sus firmas |
| `generar-vectores.py` | Regenera `ejemplos/vectores-firma.json` y `ejemplos/vectores-acceso.json`. Determinista: dos corridas dan el mismo archivo |
| `CAMBIOS.md` | Lo que cambió después de publicar, con los cambios incompatibles marcados |
| `conformidad/` | Suite de conformidad, fase 1 (`docs/suite-conformidad.md`). Corre por HTTP contra la URL de cualquier nodo: nivel A (anónimo), B (autenticado, `--sesion`/`--mandato`) y C (federación) — `python3 -m conformidad https://un-nodo.ar --nivel a,b,c` |

```
pip install jsonschema pyyaml openapi-spec-validator cryptography rfc8785 && python3 validar.py
pip install requests && python3 -m conformidad https://un-nodo.ar   # además de lo anterior
```

## Las reglas que el protocolo sí impone

Pocas, y todas verificables:

1. Un pedido es a un solo comercio. Varios comercios se combinan en un **viaje**, no en un pedido.
2. Los precios se congelan al crear el pedido. Pesables y sustituciones ajustan el monto final; la diferencia la devuelve el comercio, y la red solo la muestra.
3. El pago se confirma antes de que el comercio acepte. El efectivo es la excepción: se cobra en mano al entregar o al retirar, y el comercio decide dónde y a quién se lo acepta.
4. Solo se reseña un pedido entregado, una vez por par, dentro de 7 días.
5. Todo lo público (comercios, ofertas, rondas, reseñas) se lee sin token.
6. Toda acción de un agente lleva un mandato y queda marcada como tal.
7. Todo lo demás lo define cada comercio y lo lee cada usuario: políticas de cancelación, modalidades, precios, horarios, tolerancias.

## Lo que el protocolo no hace, a propósito

No media disputas ni arbitra entre nodos (`docs/federacion.md`). No reembolsa. No tiene soporte centralizado. No tiene publicidad ni posiciones pagas. No guarda datos que no necesita. No retiene pagos. Comprarle a un desconocido sin historial da menos seguridad que en una plataforma con garantía central: es intencional, favorece al comercio de la vereda que ya conocés.

## Estado

Versión 1.0 de la especificación, previa a la implementación de referencia. Está pensada para ser leída por personas y por agentes: cada esquema tiene `description` en español y los errores traen frases completas.

## Licencia

Especificación, esquemas, OpenAPI y MCP: **CC0 1.0** (dominio público). Usalos para lo que quieras, incluido competir.
