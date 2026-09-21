# Protocolo Vereda

**Vereda. Sin nadie en el medio.**

Un protocolo abierto para comprar y recibir de los comercios de tu barrio: restaurantes, almacenes, verdulerías, supermercados, catering, productores. Sin dueño, sin comisión escondida, sin call center. El dinero va directo del que compra al que vende y al que lleva. La red no custodia plata, no guarda más datos que los necesarios y no arbitra nada: garantiza que quien aparece es quien dice ser y que cada reseña corresponde a un pedido real. Lo demás es entre vecinos.

Es un protocolo, no una app. Cualquiera puede correr un nodo, construir un cliente o enchufar un agente. La filosofía es la del email, la web o Ethereum: sin permiso, con identidad propia, federado. Sin blockchain ni moneda: los pesos viajan por el sistema de pagos argentino (Transferencias 3.0, QR interoperable).

## En una página

- **Oferta, no producto.** Un comercio describe cualquier cosa que venda y cualquier forma de venderla con diez piezas componibles: precio (fijo, por kg, por persona, por período, a cotizar), grupos de opciones, variantes, componentes, cantidad, disponibilidad, modalidad, atributos abiertos. Seis tipos base: `producto`, `pesable`, `preparado`, `compuesto`, `servicio`, `recurrente`.
- **La entrega es configurable.** Seis modalidades que el comercio activa y precia: inmediata, franja, consolidada (junta pedidos y traslada el ahorro), ronda (entrega programada a un lugar, como el barrio cerrado los viernes), punto de entrega, retiro.
- **Compra colectiva.** Pedido grupal con link (el edificio, la oficina): cada uno paga lo suyo, un solo envío. Rondas que los propios vecinos abren.
- **Suscripciones.** Viandas semanales, catering mensual, la compra quincenal: una regla de repetición, ventana de edición, y cada ocurrencia es un pedido común.
- **Supermercado de verdad.** Listas persistentes con ítems genéricos que se resuelven contra comercios, catálogo maestro por EAN, pesables con monto final, sustituciones con preferencia declarada, franjas con cupo.
- **Promociones que cualquiera puede calcular.** 2x1, 3x2, segunda unidad al 70 %, precio por cantidad, escalera por total de compra, envío bonificado, descuento por efectivo o por retiro, y puntos por volver al mismo comercio. Son públicas, se calculan con un algoritmo público y no compran posición en el ranking.
- **Agentes primero.** Mandatos firmados con topes de gasto, carrito que se valida paso a paso y dice qué falta en español, preferencias que viven en la red y no en el agente, agentes de comercio que negocian con agentes de usuario. Servidor MCP como primera interfaz.
- **Reputación firmada y portable.** Reseñas solo sobre pedidos entregados, firmadas con la clave del autor, sin edición ni borrado. Te la llevás a otro nodo.
- **Dinero directo.** La red genera la referencia de cobro y confirma. Nunca custodia, nunca reembolsa, nunca retiene.
- **Algoritmos públicos.** Ranking y despacho están en `docs/ranking-y-despacho.md`. Nadie puede pagar para aparecer primero.
- **Federación desde el día uno.** Identidad `actor@nodo`, pedidos firmados entre nodos, sin registro central.

## Qué hay acá

| Carpeta | Contenido |
| --- | --- |
| `esquemas/` | 22 esquemas JSON (draft 2020-12): comercio, oferta, promoción, modalidad, carrito, pedido, pago, repartidor, usuario, reseña, suscripción, lista, catálogo maestro, ronda, grupo, viaje, mandato, mensaje, cotización, evento, error, comunes |
| `openapi.yaml` | La API abierta, 64 rutas. Apps y agentes usan las mismas |
| `mcp/herramientas.json` | Las 24 herramientas del servidor MCP, con descripciones para asistentes |
| `ejemplos/` | Una pizzería, una verdulería con cuatro modalidades, un catering a cotizar, viandas semanales, un supermercado con EAN, un pedido con pesables y sustituciones, un mandato, una ronda al barrio cerrado, un pedido grupal de edificio, y `vectores-firma.json` con los vectores de prueba de firma |
| `docs/` | Federación (con mudanza, disputas y catálogo maestro), claves y firmas, eventos y webhooks, ranking y despacho, carrito y reserva, promociones, datos y privacidad |
| `validar.py` | Valida los ejemplos contra los esquemas, `openapi.yaml` contra OpenAPI 3.1 y reproduce los vectores de firma |
| `generar-vectores.py` | Regenera `ejemplos/vectores-firma.json`. Determinista: dos corridas dan el mismo archivo |

```
pip install jsonschema pyyaml openapi-spec-validator cryptography rfc8785 && python3 validar.py
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
