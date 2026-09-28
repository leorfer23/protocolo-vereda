---
name: vereda-comercio
description: Abrir y administrar un comercio en Vereda desde un agente, por el servidor MCP del nodo. Usala cuando una persona quiere vender en Vereda, dar de alta su local o distribuidora, cargar su catálogo, cambiar horarios, envíos o medios de cobro, o atender los pedidos de su comercio.
---

# Vereda para comercios

Vereda es un protocolo abierto de comercio de barrio. Un comercio se da de alta solo, sin que nadie lo apruebe, y queda vendiendo al instante. Vos actuás en nombre de la persona con el mandato que ella te da; nunca manejás plata: cada comprador le paga directo al comercio.

## 1. Conectarte

1. Leé `https://{nodo}/.well-known/vereda.json`. `endpoints.mcp` es el servidor MCP (Argentina: `https://ar.protocolovereda.com/mcp`).
2. Las herramientas públicas (`buscar_comercios`, `ver_comercio`, …) andan sin token. Para administrar hace falta un mandato con scope `administrar`: la persona lo firma desde su sesión (app o web del nodo) cuando tu cliente MCP inicia OAuth. No hay herramienta de acceso: si no tenés mandato, pedile que lo otorgue.
3. Fijate qué ofrece el nodo en `vereda.json`: sin `endpoints.medios`, `medio_subir` responde `no_implementado` y las fotos van por URL pública; `cobradores` dice qué proveedores de tarjeta se pueden conectar.

## 2. Dar de alta el comercio

1. `mis_comercios`. Si ya administra el comercio, no crees otro: seguí en el paso 3.
2. Confirmá quién es la dueña. Quien crea el comercio queda como dueña para siempre (cambia solo por un reclamo, `docs/identidad-y-verificacion.md`). El mandato tiene que ser de la dueña real, no de quien la ayuda; quien ayuda entra después por `equipo_invitar`.
3. Juntá lo mínimo y mostráselo antes de crear:
   - `nombre`, `tipo` (`restaurante`, `almacen`, `verduleria`, `supermercado`, `catering`, `productor`, `panaderia`, `farmacia`, `otro`) y `subtipo` libre (ej. `distribuidora`).
   - `ubicacion.direccion`: `texto` y `punto` `{lat, lng}`. Si no publica la dirección (un productor sin local), `publica_direccion: false`.
   - `ubicacion.zona_entrega`: anillo cerrado de puntos (el primero igual al último, 4 como mínimo).
   - `modalidades`: al menos una. La más simple es `{"id": "retiro", "tipo": "retiro", "precio_envio": {"modo": "gratis"}}`.
   - `politica_cancelacion`: `texto` en sus palabras y `hasta_estado` (`pagado`, `aceptado`, `preparando`, `listo`, `asignado`).
4. `comercio_crear` con esa ficha. Guardá el `id` que devuelve.

Nunca inventes datos del comercio: dirección, precios, horarios, CUIT o cuenta de cobro salen de la persona.

## 3. Completar la ficha

Todo con `comercio_editar` (solo los campos que cambian):

- `descripcion` y `notas_para_agentes`: lo que un mostrador le diría a un cliente.
- `descripcion` del negocio y actividad: `tipo` de la lista y `subtipo` libre (ej. `distribuidora mayorista de alimentos`).
- `marca`: `logo` (`{url, alt}`, cuadrado o casi), `color_primario` y `color_secundario` en `#RRGGBB`. Si la persona trae el logo, proponé los dos colores sacados de él y confirmalos con ella.
- `redes`: `instagram`, `tiktok`, `x`, `facebook`, `youtube` (usuario sin @ o URL), `whatsapp` y `telefono` en formato internacional (`+5491122334455`), `email`, `sitio_web`. Son públicas; `privado.contacto` es solo para el nodo.
- `imagenes`: vidriera, local, productos. `[{url, alt}]`. Con `endpoints.medios`, subilas antes con `medio_subir` y usá la `url` que devuelve.
- `horarios`: franjas `{dias, desde, hasta}`. Vacío es siempre abierto. `apertura_manual` abre o cierra ya.
- `medios_cobro`: `efectivo`, `transferencia`, `qr_interoperable`. `tarjeta` la pone el nodo solo cuando hay un cobrador conectado (`cobrador_conectar`). Con efectivo, `efectivo.monto_maximo` y `efectivo.pedidos_entregados_minimo` protegen al comercio.
- `privado.cuenta_cobro` pide firma fresca de la persona: si el nodo la exige, que lo haga ella desde la app.
- `envios`: cómo consigue repartidor (`propios`, `usuario`, `pool`) y qué pasa si nadie acepta.
- `aporte_nodo`: voluntario y público; `ninguno` vale igual (`aporte_configurar`).

## 4. Catálogo

- `oferta_crear` por producto: nombre, precio en centavos (`{"centavos": 150000, "moneda": "ARS"}` es $1.500), unidad o pesable, stock y fotos.
- Con IA activa en el nodo, `ia_catalogo_desde_fotos` propone borradores desde fotos de góndola o de lista de precios. No publica: revisalos con la persona y confirmá con `oferta_crear`.
- `stock_actualizar` para faltantes; `promocion_crear` para promos.
- Una distribuidora que vende por bulto: una oferta por presentación (ej. "Caja x 12") con su precio, y la unidad en la descripción.

## 5. Operar

- `pedidos_del_comercio` es la bandeja. `pedido_aceptar` o `pedido_rechazar` dentro de `plazo_aceptacion_min`; si no, el pedido se cancela y cuenta como rechazado.
- `pedido_listo`, `pedido_entregar`, `pedido_asignar` según quién lleva.
- `ver_mensajes` y `enviar_mensaje` para hablar con el comprador dentro del pedido.
- `metricas_del_comercio` y `exportar_comercio` (solo la dueña) para sus números y sus datos.

## 6. Verificación

No hace falta para vender. `verificacion` se completa sola cuando el comercio verifica CUIT, foto geolocalizada y cuenta de cobro (`ver_verificacion`). No existe tilde azul ni nadie que apruebe.

## Reglas

- Mostrá cada cambio antes de publicarlo; lo que publicás lo ven compradores al instante.
- Una cosa por llamada y leé la respuesta: un `422` trae `detalle` con qué campo falta o sobra.
- Los datos del comercio son del comercio: no los copies a otro lado.
