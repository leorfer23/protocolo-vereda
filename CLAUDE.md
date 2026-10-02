# CLAUDE.md — trabajar en protocolo-vereda

Este repo es la **spec** de Vereda (esquemas, OpenAPI, MCP, docs normativos, suite de conformidad). No
corre nada en producción. `AGENTS.md`, si lo ves en el checkout principal, lo genera Chronos y está
excluido de git: no lo edites y no esperes encontrarlo en un worktree.

## Agent quickstart — dónde está cada cosa

- **El checkout principal está viejo.** `~/Documents/GitHub/protocolo-vereda` (y los de los repos
  hermanos) quedó en `main` de hace cientos de commits y para los agentes del Desk es de solo lectura.
  No leas la spec de ahí: `git -C ~/Documents/GitHub/protocolo-vereda fetch -q origin` y después
  `git show origin/main:<ruta>`, o trabajá en un worktree.
- **Worktree:** `mc worktree protocolo-vereda --as <tipo>/<slug>` crea la rama `lf/<tipo>/<slug>` en
  `~/Documents/GitHub/.chronos-worktrees/protocolo-vereda/lf-<tipo>-<slug>`; la última línea que imprime
  es `cd <ruta>` (no la ruta sola: no hagas `$(… | tail -1)`). Sin `mc`:
  `git -C ~/Documents/GitHub/protocolo-vereda worktree add ~/Documents/GitHub/.chronos-worktrees/protocolo-vereda/<slug> -b lf/<tipo>/<slug> origin/main --no-track`.
- **Python:** el Python del sistema no trae las dependencias. En el worktree:
  `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt` (~11 s; `.venv/` está ignorado).
- **El gate es local, no hay CI en este repo** (no hay `.github/`): un PR acá no tiene checks.
  - `.venv/bin/python validar.py` (2–5 s): ejemplos contra esquemas, `ejemplos/casos/*.json`, OpenAPI 3.1,
    reglas de la API y vectores de firma. La última línea dice `✓ validar.py: 0 fallas` o cuántas hay
    (las fallas son las líneas con `✗`); sale con 1 si algo falla. Pegá ese final en el PR.
  - `for f in conformidad/pruebas/verificar_*.py; do .venv/bin/python $f; done` (<2 s cada uno) si tocás
    `conformidad/` o los vectores. `conformidad/pruebas/nodo_falso.py` es un nodo HTTP de mentira para
    probar la suite a mano.
  - `.venv/bin/python generar-vectores.py` si cambiás firmas, acceso o respaldo; es determinista
    (`git diff ejemplos/` vacío = nada cambió).
- **Dónde vive cada cosa:**
  - `openapi.yaml` (~3.2k líneas, ~190 operaciones): `/acceso` en la raíz, el resto bajo `/v1`. Buscá por
    operationId: `grep -n "operationId: crearOferta" openapi.yaml`.
  - `esquemas/*.json`: un recurso por archivo; los `$defs` compartidos (imagen, video, firma, área…)
    están en `esquemas/comunes.json`. Errores y sus códigos: `esquemas/error.json`.
  - `mcp/herramientas.json`: cada herramienta MCP con la operación de `openapi.yaml` que usa.
  - `ejemplos/*.json` se validan solo si están en `MAPA` / `MAPA_DEFS` de `validar.py`: un ejemplo nuevo
    se registra ahí. `ejemplos/casos/*.json` (casos `valido`/`invalido` por esquema) se descubren
    solos, y la conformidad nivel A los usa también como negativos HTTP. No existe `conformidad/casos/`.
  - `conformidad/`: `nivel_a.py` (anónimo), `nivel_b.py` (autenticado, ~2.5k líneas: un método por tema,
    p. ej. `_metodo_pago`, `_videos`), `nivel_c.py` (federación), `cliente.py` (HTTP), `oraculo.py`
    (carga de esquemas). Diseño en `docs/suite-conformidad.md`.
  - `docs/<tema>.md` es normativo; `docs/ia/` es la capacidad IA; `docs/investigaciones/` y
    `.claudedocs/` son investigación, no spec. `skills/vereda-comercio/SKILL.md` es la skill para agentes
    de comercio (no hay otro archivo "skill").
- **JSON a mano:** `mcp/herramientas.json` y varios ejemplos tienen formato propio; volver a escribirlos
  con `json.dump` reformatea el archivo entero. Editá el bloque como texto (Edit o un reemplazo
  puntual).
- **Cada cambio de spec suma una entrada en `CAMBIOS.md`** (la más nueva arriba, bajo `## AAAA-MM-DD`)
  y, si cambia lo que hay, la tabla de `README.md`. Con varios PR en paralelo, el conflicto al rebasear
  casi siempre es esa línea: quedate con las dos entradas.
- **Shell:** zsh con `nomatch`: `grep -rn x --include=*.go .` falla con "no matches found". Citá los
  globs (`--include='*.go'`) o usá `git grep` / `rg`. macOS no trae `timeout`.
- **Búsqueda:** el MCP **fff** (`grep`, `find_files`) indexa la carpeta donde arrancó la sesión: arrancá
  en un worktree, no en `~` ni en `~/Documents/GitHub/<ws>`, y no en el checkout principal (indexa la
  spec vieja). **graphify**: `graphify update .` en el worktree y después
  `graphify explain "<símbolo>"` o `graphify query "<pregunta>"`. **ast-grep** (`ast-grep run -p 'self.casos.append($X)' -l py conformidad`;
  `sg` es el alias viejo) para llamadas en Python. RTK comprime la salida de Bash solo.
- **PR:** rama `lf/<tipo>/<slug>`, título `tipo(área): …`, cuerpo en voseo con `## Para Leo (resumen)`
  arriba. Los PR los mergea Leo, con squash. Mergear no es desplegar, y este repo no se despliega.

## Qué repo es dueño de qué

| Repo | Qué tiene | Gate |
| --- | --- | --- |
| `protocolo-vereda` (este) | La spec: esquemas, OpenAPI, MCP, docs normativos, suite `conformidad/`, skill de comercio, `datos/` CC0 | `validar.py` |
| `vereda-nodo` | El nodo de referencia (Go + PostgreSQL/PostGIS) y su copia de la spec en `spec/`; el SDK TypeScript (`web/sdk/`); el **concepto de diseño de la app** (`docs/app/diseno.md`, `docs/app/flujos.md`); deploy (`docs/deploy-cloudflare.md`, `docs/restaurar-neon.md`); notas de implementación en `docs/ia/` (el contrato es el de acá) | `make test`, `make conformidad` |
| `vereda-app` | Apps nativas: `ios/` (SwiftUI, `ios/ARQUITECTURA.md`) y `android/` (Compose, `android/ARQUITECTURA.md`, `PARIDAD.md`); copia de la spec en `ios/VeredaNodo/spec/` | `make verificar` en `ios/` |
| `vereda-webapp` | App web del comprador y portal del comercio (`app.` y `comercio.protocolovereda.com`); copia de la spec en `spec/` y del SDK en `src/comun/sdk/` | `npm run verificar` |
| `vereda-web` | La landing (`protocolovereda.com`) y la lista de espera | `npm test` |

En los repos hermanos, los jobs de GitHub Actions hoy no arrancan (problema de la cuenta, no del código):
el gate es el local de la tabla.

### Un cambio de spec que el nodo implementa

1. PR acá primero. Leo lo mergea con squash: el commit en `main` **no** es el de tu rama.
2. En un worktree de `vereda-nodo`: `spec/sincronizar.sh <checkout de protocolo-vereda en ese commit de main>`.
   Copia `esquemas/`, `ejemplos/`, `openapi.yaml` y `mcp/herramientas.json` y escribe el HEAD de ese
   checkout en `spec/VERSION`; el CI del nodo vuelve a clonar ese hash y compara `spec/`. Un checkout en
   un commit fijo:
   `git -C ~/Documents/GitHub/protocolo-vereda worktree add --detach ~/Documents/GitHub/.chronos-worktrees/protocolo-vereda/spec-<hash7> <hash>`.
3. `make conformidad` del nodo usa `CONFORMIDAD_SPEC=../protocolo-vereda` por defecto: desde el checkout
   principal del nodo eso es la spec vieja, y desde un worktree no existe. Pasala siempre, en el commit de
   `spec/VERSION` (una suite más nueva trae casos que el nodo todavía no implementa), con el venv de esa
   carpeta adelante en el `PATH`:
   `PATH=<spec>/.venv/bin:$PATH make conformidad CONFORMIDAD_SPEC=<spec>`.
4. Las apps copian la spec aparte (`vereda-app`: `ios/VeredaNodo/README.md`; `vereda-webapp`:
   `spec/` y `npm run tipos`). Que el nodo se sincronice no las actualiza.
