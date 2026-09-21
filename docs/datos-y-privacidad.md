# Datos y privacidad

Principio: no somos dueños de nada, y eso es verificable.

- **Mínimos.** Dirección exacta, teléfono y nombre completo viven en tablas separadas con acceso restringido y se borran o anonimizan a los 90 días de entregado el pedido. El resto del historial es anónimo.
- **Visibilidad.** Nombre y dirección del usuario los ven solo el comercio y el repartidor del pedido activo. Ubicación del repartidor, solo las partes mientras está en camino. CUIT completo, DNI y cuentas de cobro nunca son públicos ni se federan.
- **Chat.** Cifrado de punta a punta (X25519 + XChaCha20) entre las partes cuando todas tienen clave; el nodo guarda el payload cifrado. Los mensajes que entran por agente de voz se cifran al ingresar.
- **Exportación y borrado.** `GET /yo/exportar` entrega todo firmado; `POST /yo/borrar` elimina datos personales en 30 días. Las reseñas firmadas quedan como emitidas por un autor anonimizado, porque son parte de la reputación del reseñado.
- **Auditoría.** Cada lectura de datos personales por un operador del nodo queda registrada y es consultable por la persona.
- **Sin trackers.** Los clientes de referencia no incluyen SDK de terceros ni analítica externa.
- **Ley 25.326 (Argentina).** El operador de cada nodo registra su base de datos ante la autoridad de aplicación, publica su política de privacidad y designa un responsable. La spec no reemplaza asesoramiento legal; cada operador es responsable de su nodo.
- **Lo público es público.** Comercios, catálogos, precios, modalidades y reseñas son legibles por cualquiera sin token, incluidas las plataformas que Vereda reemplaza. Es una consecuencia deliberada de ser abiertos.
