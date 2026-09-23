# Datos y privacidad

Principio: no somos dueños de nada, y eso es verificable.

- **Mínimos.** Dirección exacta, teléfono y nombre completo viven en tablas separadas con acceso restringido. Se borran o anonimizan a los 90 días de entregado el pedido: ese es el **default** del protocolo y el que rige si el comercio no dice otra cosa. Cada comercio puede fijar otro plazo en `datos.retencion_dias` de su ficha, y queda siempre visible ahí. El resto del historial es anónimo.
- **Visibilidad.** Nombre y dirección del usuario los ven solo el comercio y el repartidor del pedido activo. El nombre es el que la persona eligió para mostrar (`PUT /yo/nombre`) y llega en `partes` del pedido (`esquemas/pedido.json`); terminado el pedido lo sigue viendo ella y el comercio solo si aceptó su lista de clientes. Si no eligió ninguno, el pedido no trae nombre: nunca se muestra el handle de la identidad, y cómo nombrarla ("Cliente #4821") lo decide cada app. Ubicación del repartidor, solo las partes mientras está en camino: en el evento `pedido.ubicacion_repartidor` y en `GET /pedidos/{id}`, que trae el último reporte para quien abre el pedido a mitad del viaje. CUIT completo, DNI y cuentas de cobro nunca son públicos ni se federan; la única cuenta pública es la del operador del nodo, que pide aportes a la vista de todos (`docs/sostenimiento.md`). El alias del repartidor lo ve solo quien le debe un pago de un viaje activo; la lista de repartidores propios de un comercio y los repartidores de confianza de una persona no se publican. Las direcciones guardadas de una persona (`PUT /yo/direcciones`) las escribe y las lee solo ella con su sesión; al comercio y al repartidor les llega la del pedido, no la lista. La única excepción es para su agente: con un mandato `leer` puede listar las **etiquetas** de esas direcciones ('casa', 'oficina'; `GET /yo/direcciones`, herramienta `mis_direcciones`), sin calle, altura, piso ni punto, y usar una por su etiqueta al crear un carrito o elegir su modalidad (`direccion_etiqueta`, scope `armar`): la dirección exacta la pone el nodo desde lo que la persona guardó. Un agente nunca escribe ni cambia direcciones.
- **Chat.** Cifrado de punta a punta (X25519 + XChaCha20) entre las partes cuando todas tienen clave; el nodo guarda el payload cifrado. Los mensajes que entran por agente de voz se cifran al ingresar.
- **Exportación y borrado.** `GET /yo/exportar` entrega todo firmado; `POST /yo/borrar` elimina datos personales en 30 días. Las reseñas firmadas quedan como emitidas por un autor anonimizado, porque son parte de la reputación del reseñado.
- **Auditoría.** Cada lectura de datos personales por un operador del nodo queda registrada y es consultable por la persona.
- **Sin trackers.** Los clientes de referencia no incluyen SDK de terceros ni analítica externa.
- **Ley 25.326 (Argentina).** El operador de cada nodo registra su base de datos ante la autoridad de aplicación, publica su política de privacidad y designa un responsable. La spec no reemplaza asesoramiento legal; cada operador es responsable de su nodo.
- **Lo público es público.** Comercios, catálogos, precios, modalidades y reseñas son legibles por cualquiera sin token, incluidas las plataformas que Vereda reemplaza. Es una consecuencia deliberada de ser abiertos.

## Los datos del comercio son del comercio

El otro lado del mostrador tiene el mismo derecho que la persona: lo que el comercio produce
operando —su ficha, su catálogo, sus promociones, su stock, sus pedidos, las reseñas que recibió y
sus métricas— es suyo y se lo lleva entero.

- **Exportación total.** `GET /comercios/{id}/exportar` entrega todo eso en un documento firmado por
  el nodo, verificable en cualquier otro. Es para mudarse de nodo, tener respaldo, o alimentar el
  sistema propio del comercio. No hay nada que el nodo se guarde para sí.
- **Política pública en la ficha.** El bloque `datos` de `esquemas/comercio.json` es parte de la
  ficha pública: cuántos días retiene los datos personales de un pedido (`retencion_dias`) y si
  guarda una lista de clientes más allá del pedido activo (`lista_de_clientes`). Cualquiera lo lee
  antes de comprar, sin token. Un comercio que retiene un año no está escondido: está declarado.
- **Un default promovido, no obligado.** El protocolo estandariza y recomienda la minimización —90
  días, sin lista de clientes—, y el nodo marca con `datos.estandar` a quien coincide. Ese sello es
  lo que muestran las apps. El sello no se declara a mano: si la política no es la del default, el
  esquema rechaza el `estandar: true`. Quien elige otra política opera igual, con los mismos
  derechos y el mismo ranking; la diferencia la ve el usuario y decide él.
- **Consentimiento para la lista de clientes.** Si el comercio declara `lista_de_clientes: true`, el
  nodo no le entrega nombre ni contacto más allá del pedido activo hasta que la persona acepte:
  `acepta_lista_de_clientes` al confirmar el carrito, una vez por comercio, y se puede decir que no
  sin perder el pedido.
- **Métricas sin identidad.** `GET /comercios/{id}/metricas` devuelve agregados —visitas a la ficha,
  apariciones en búsqueda, pedidos, conversión, ticket promedio— y nunca quién. No existe la
  operación que diga qué persona miró la ficha, y un nodo que no puede agregar sin identificar no
  publica la métrica.
- **Responsabilidad de lo que sale.** Lo que el comercio hace con esos datos fuera del nodo es suyo,
  incluida la responsabilidad legal (Ley 25.326): exportar no transfiere la obligación al nodo, y el
  nodo no puede hacerla cumplir afuera.

## Sin gatekeeper

Nadie habilita comercios, repartidores ni usuarios. `POST /comercios` lo crea activo al instante para la sesión
que lo crea: no hay revisión del operador del nodo, ni alta manual, ni sello de autoridad, ni una
cola de aprobación en ningún lado. Lo mismo vale para el repartidor: `PUT /repartidor` lo da de alta al instante, sin screening ni datos que cargue un tercero (`docs/repartidores.md`). Los campos de `verificacion` de la ficha son chequeos automáticos y
verificables (CUIT, foto geolocalizada, cuenta de cobro que coincide), no una habilitación: un
comercio con los tres en false vende igual, y quien compra ve exactamente qué está verificado y qué
no. Cómo se distingue a un comercio verdadero de uno que se hace pasar por él, sin que nadie
otorgue nada, está en `docs/identidad-y-verificacion.md`: ahí el contacto confirmado de una persona
se guarda solo como hash, y la cuenta de cobro se comprueba sin publicarse nunca. La única reputación es la suma de reseñas firmadas de pedidos entregados, que nadie —tampoco el
operador del nodo— puede editar ni borrar.
