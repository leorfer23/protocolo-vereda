# Cómo enterarnos de los crashes sin terceros

Investigación del 2026-09-25. Solo fuentes públicas: sin cuentas, sin credenciales, sin escribirle a nadie.
Es una investigación, no una norma de la spec. No es asesoramiento legal.

Cada dato lleva su fuente. Lo marcado **(NC)** no está confirmado en una fuente oficial de 2025–2026.

Los principios no cambian: **sin trackers ni SDK de terceros** (`docs/datos-y-privacidad.md`), la app no manda datos a Sentry, Firebase, Crashlytics ni similares, y lo que se sepa de un crash tiene que ser mínimamente personal y con consentimiento explícito.

Estado actual (2026-09-25): en `vereda-app/ios` y `vereda-app/android` **no hay** ningún SDK de crashes. Una búsqueda por `sentry`, `crashlytics`, `firebase`, `Bugsnag` e `Instabug` en el árbol de la app no devolvió coincidencias.

---

## 1. Comparativa

| Camino | Quién lo ofrece | Qué llega | Consentimiento | Sale del dispositivo hacia un tercero | Esfuerzo hasta el 28/9 | Cobertura típica |
|---|---|---|---|---|---|---|
| **Xcode Organizer / App Store Connect** | Apple | Stacks simbolizados de los crashes más frecuentes (últimas ~2 semanas en Organizer); métricas de terminaciones | App Store: la persona activa *Share With App Developers*. TestFlight: se comparte solo. | A Apple, no a Vereda ni a otro vendor | Casi cero (proceso + dSYM) | Solo quien optó; hay demora de hasta ~1 día tras publicar |
| **MetricKit `MXCrashDiagnostic`** | Apple (framework del sistema) | Diagnóstico de crash en el próximo arranque de la app (`didReceive`) | El sistema entrega el payload a la app; reenviarlo fuera del teléfono es decisión nuestra | No, salvo que la app lo reenvíe | 0,5–1 día (escuchar y loguear local) · 3–5 días si además se manda al nodo | Puede ser un **superset** de lo que muestra App Store Connect (Apple Forums, 2026) |
| **Play Console · Android vitals** | Google Play | Tasas de crash/ANR (incl. *user-perceived*), clusters con stacks | Instalación por Play; vitals excluye dispositivos no certificados y builds no instalados por Play | A Google, no a otro vendor de crashes | Casi cero (cuenta Play + checklist) | Solo distribución por Play; ~90 días en la consola |
| **Play Developer Reporting API** | Google | Las mismas métricas por API (`vitals.crashrate.query`, etc.) | Igual que vitals | A Google | 1–2 días (OAuth de la cuenta del operador) | Igual que vitals; API guarda hasta 3 años |
| **`ApplicationExitInfo`** | Android (API 30+) | Motivo de muerte del proceso (`REASON_CRASH`, `REASON_ANR`, nativo, low memory…) y, a veces, un trace | Lectura local en el próximo arranque | No, salvo que la app lo reenvíe | 0,5–1 día (leer y loguear) · 3–5 días con envío al nodo | Solo lo que el sistema guardó para *esta* instalación |
| **Endpoint propio en el nodo** | Operador del nodo | Lo que la app mande (ver §4) | Consentimiento **en la app**, aparte del de Apple/Google | Al nodo del operador (no a un SaaS) | Spec + nodo + iOS + Android: ~1–2 semanas | Quien consintió y tiene red al arrancar |

Conclusión corta: **para el 28/9 alcanza Organizer + Play vitals**. MetricKit y `ApplicationExitInfo` suman señal en el teléfono sin terceros. Un endpoint propio solo hace falta si queremos enterarnos más rápido, de más dispositivos o fuera de las tiendas.

---

## 2. iOS — lo que Apple da gratis

### 2.1 Xcode Organizer y App Store Connect

- Ventana **Organizer → Crashes**: Xcode baja los reportes con más ocurrencias en dispositivos distintos de las **últimas dos semanas**. Puede haber hasta **un día** de demora entre publicar y ver el primer reporte. [fuente: ayuda de Xcode *About Crashes organizer*, consultado 2026-09-25]
- App Store: la persona tiene que tener activado **Settings → Privacy & Security → Analytics & Improvements → Share With App Developers**. Si apaga *Share iPhone Analytics*, eso también se apaga. [fuente: https://www.apple.com/legal/privacy/data/en/app-analytics/, actualizado 2025-12-12]
- **TestFlight comparte solo** con el desarrollador; no hace falta ese toggle. [misma ayuda de Xcode]
- Al subir el build hay que **incluir los símbolos (dSYM)** (*Upload your app’s symbols…*). Sin eso, los stacks llegan sin simbolizar o hay que simbolizar a mano con el archive guardado. [fuente: ayuda de Xcode *Distribution options*]
- App Store Connect muestra totales y feedback de crashes de TestFlight; el detalle útil para arreglar sigue viviendo en Organizer / “Open in Xcode”.

Qué implica para el 28/9:

1. Checklist de release: dSYM subidos, Apple ID del equipo en Xcode, alguien mira Organizer el día del lanzamiento y a las 24–48 h.
2. No hay código nuevo. No hay SDK. No hay cambio de protocolo.

Límites: no vemos a quien no compartió; no es tiempo real; Organizer prioriza los crashes **más frecuentes**, no necesariamente el primero de una persona.

### 2.2 MetricKit — `MXCrashDiagnostic`

- Framework de Apple. La app se suscribe a `MXMetricManager` y recibe payloads en `didReceive` en un arranque posterior.
- `MXCrashDiagnostic` trae, entre otras, `terminationReason` (texto legible del motivo). [fuente: https://developer.apple.com/documentation/metrickit/mxcrashdiagnostic/terminationreason, © 2026 Apple]
- Apple confirma en foros (hilo sobre analytics de crashes, 2026) que lo que llega por MetricKit **puede ser un superset** de lo visible en App Store Connect, y que esos diagnósticos **no se guardan en servidores de Apple para el desarrollador**: se entregan a la app. Si la app no los reenvía, no salen del teléfono.
- También hay métricas de terminaciones en primer/segundo plano (`ForegroundTerminationMetric` / `BackgroundTerminationMetric`) útiles para distinguir crash de “el sistema mató la app por memoria”. [fuente: https://developer.apple.com/documentation/xcode/reduce-terminations-in-your-app]

Qué implica:

- **Escuchar y guardar en el teléfono** (o log de depuración en TestFlight): compatible con “sin terceros”, esfuerzo chico.
- **Reenviar al nodo**: pasa a ser el camino del §4; hace falta consentimiento propio y texto para legales.

---

## 3. Android — lo que Play da gratis

### 3.1 Android vitals (Play Console)

- Tasas de crash y ANR, con variante **user-perceived** (crash mientras había Activity o foreground service).
- Clusters con stacks para priorizar.
- Ventana típica en la consola: **90 días**; la Play Developer Reporting API documenta hasta **3 años**. [fuente: https://support.google.com/googleplay/android-developer/answer/9844486, consultado 2026-09-25; https://developers.google.com/play/developer/reporting]
- **No incluye** issues en dispositivos no certificados ni en versiones que no se instalaron por Google Play.

Qué implica para el 28/9: misma lógica que Organizer — cuenta Play del operador, build firmado subido por Play (o al menos la vía que alimenta vitals), alguien mira Crashes & ANRs el día 0 y a las 24–48 h. Cero código en la app.

### 3.2 `ApplicationExitInfo` (API 30+)

- `ActivityManager.getHistoricalProcessExitReasons` devuelve muertes recientes del proceso.
- Motivos útiles: `REASON_CRASH`, `REASON_CRASH_NATIVE`, `REASON_ANR`, más low-memory, signal, user-requested, etc. [fuente: https://developer.android.com/reference/android/app/ApplicationExitInfo, consultado 2026-09-25]
- A veces hay un stream de trace (`getTraceInputStream`); no siempre.

Igual que MetricKit: leer al arrancar es gratis y local; mandarlo al nodo es §4.

---

## 4. Opción propia — ¿hace falta en el protocolo?

### Veredicto

**No hace falta para el 28/9.** Organizer + vitals cubren “enterarnos”.

**Después sí conviene esbozarlo** como **capacidad opcional del nodo** (como la subida de fotos), no como obligación del protocolo: cada operador decide si la ofrece; las apps de referencia la usan solo si el `/.well-known` (o el manifiesto de capacidades) dice que está. Así no empujamos a todos los nodos a guardar dumps, y seguimos sin SaaS.

No es identidad, no es pedido, no es ranking: es telemetría de falla del **cliente de referencia**. Meterlo en el núcleo del protocolo lo mezclaría con datos de personas y comercios. Mejor un doc de capacidad + esquema suelto, y recién promoverlo a spec si varios operadores lo piden.

### Esbozo de endpoint (no implementar)

```
POST /v1/diagnosticos/crash
Authorization: Bearer <sesión de la persona>   # o token de dispositivo anónimo de un solo uso
Content-Type: application/json
```

Cuerpo propuesto (mínimo, sin datos personales):

| Campo | Tipo | Notas |
|---|---|---|
| `plataforma` | `"ios"` \| `"android"` | |
| `app` | string | p.ej. `comprador` / `comercio` / `repartidor` |
| `version_app` | string | semver o marketing version |
| `build` | string | número de build |
| `version_os` | string | p.ej. `18.1`, `15` |
| `cuando` | string ISO-8601 | hora del crash en el dispositivo (no la del POST) |
| `motivo` | string | `terminationReason` / `REASON_*` / señal |
| `excepcion` | string? | nombre de clase/señal, sin mensaje libre del usuario |
| `stack` | string[]? | frames **ya simbolizados en el cliente** o hashes de frames; tope duro (p.ej. 40 líneas, 8 KiB) |
| `consentimiento` | string | id/versión del texto de consentimiento aceptado |
| `idempotencia` | string | uuid generado en el cliente para no duplicar al reintentar |

Respuesta: `204` o `201 { "id": "…" }`. El nodo **no** indexa por persona para ranking ni ficha; retención corta (p.ej. 30–90 días) alineada con `docs/datos-y-privacidad.md`; exportable/borrable con `GET/POST /yo/…` si la sesión identificó a alguien.

Reglas duras del payload:

- **Prohibido:** nombre, handle, email, teléfono, dirección, geolocalización, ids de pedido/comercio, texto libre del usuario, capturas de pantalla, cookies de terceros.
- **Preferible:** sesión opcional; si no hay sesión, un token de diagnóstico de un solo uso pedido justo antes del POST (para rate-limit sin atar a la identidad).
- Rate-limit agresivo por IP y por clave (pocos por día).
- Solo `POST` de diagnóstico; nada de SDK que espíe pantallas.

Capacidad en el manifiesto del nodo (idea): `"diagnosticos_crash": true`. Sin eso, la app ni ofrece el toggle.

---

## 5. Privacidad — qué tendría que declarar legales

Esto es lista de trabajo para el agente de legales / la política del operador, **no** un dictamen.

### Si solo usamos Organizer + Play vitals (mínimo 28/9)

- La app **sigue sin** SDK de analytics/crashes de terceros → coherente con “Sin trackers”.
- Quien optó con Apple o usa TestFlight ya consentió el flujo de Apple; Play documenta vitals como parte de la distribución.
- En la política del operador alcanza con decir, en una línea, que **Apple y Google pueden enviarle reportes de falla agregados o seudonimizados según sus propios controles**, y que Vereda no instala herramientas de terceros para eso.
- App Store Nutrition Labels / Data safety de Play: **no declarar** recolección propia de “Crash Data” si la app no manda nada; lo que ve el desarrollador llega por la consola de la tienda. **(NC: validar el wording exacto con legales ante el formulario actual de cada tienda.)**

### Si activamos MetricKit / ApplicationExitInfo solo en el teléfono

- No cambia la narrativa hacia afuera si no sale del dispositivo.
- Si en algún momento se loguea a un archivo que después se exporta o se pega en un issue, tratarlo como dato técnico del dispositivo.

### Si mandamos diagnósticos al nodo

Hay que declarar, como mínimo:

1. **Finalidad:** mejorar la estabilidad de la app; no perfilar ni vender.
2. **Base:** consentimiento libre, informado, revocable (Ley 25.326 arts. 5–6); toggle off por defecto o pedido en contexto la primera vez que haya un crash pendiente de enviar.
3. **Datos:** lista cerrada del §4; afirmar que no van datos de pedidos ni de identidad más allá de lo necesario para autenticar el POST.
4. **Retención y borrado:** plazo corto; derecho de acceso/supresión; si el POST fue con sesión, entra en `GET /yo/exportar` y `POST /yo/borrar`.
5. **Encargado / responsable:** el **operador del nodo**, no “Vereda” como marca abstracta (igual que el resto de la base).
6. **Transferencias:** el diagnóstico viaja al host del nodo (hoy AR); sin reenvío a EE.UU. vía Sentry/etc.
7. **Tiendas:** marcar Crash Data / “App diagnostics” como recolectados **por la app**, vinculados o no a la identidad según el diseño del token.

Tensión de marca: un endpoint propio es más “Signal” (datos al operador que elegiste) que un SaaS. Sigue siendo recolección: hay que pedirla con claridad, sin lettering gris.

---

## 6. Esfuerzo estimado

| Trabajo | iOS | Android | Spec / nodo | Total calendario |
|---|---|---|---|---|
| Checklist Organizer / vitals + dSYM / símbolos Play | 2–4 h | 2–4 h | — | **medio día** (mínimo 28/9) |
| Escuchar MetricKit / ExitInfo y log local (TestFlight / debug) | 0,5–1 d | 0,5–1 d | — | **~2 días** en paralelo |
| Capacidad + `POST /diagnosticos/crash` + retención | — | — | 2–4 d | |
| Cliente: consentimiento, cola al arrancar, simbolización acotada, reintentos | 2–3 d | 2–3 d | — | **~1–2 semanas** punta a punta |
| Copy + política + Data safety / Privacy labels | — | — | legales 1–3 d | en paralelo |

---

## 7. Recomendación

### Para el 28/9 (mínimo)

1. **No agregar ningún SDK de crashes.** Seguir como estamos.
2. **Operar Organizer (iOS) y Android vitals (Play)** el día del lanzamiento y las 48 h siguientes.
3. **Checklist de release:** subir dSYM; no strippear símbolos de Play; tener acceso a App Store Connect y Play Console del operador del nodo AR.
4. Opcional barato si sobra un día: **MetricKit + `ApplicationExitInfo` solo locales** en builds de TestFlight / internos, para ver stacks antes de que lleguen a la consola — **sin POST**.

### Después del 28/9

1. Si Organizer/vitals alcanzan (pocos crashes, demora aceptable): no construir endpoint.
2. Si hace falta enterarnos más rápido o fuera de las tiendas: capacidad opcional `diagnosticos_crash` con el esbozo del §4, consentimiento en la app, retención corta, sin PII.
3. **No** meterlo en el núcleo del protocolo hasta que un operador real lo pida; documentarlo como investigación → capacidad, igual que fotos opcionales.

### Una línea

**El 28/9 nos enteramos por Apple Organizer y Play vitals (cero terceros, cero código); un POST propio al nodo queda como capacidad opcional post-lanzamiento, con consentimiento y sin datos personales.**
