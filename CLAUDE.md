# CLAUDE.md — Conocimiento operativo de `06.scraping_convocatorias`

Este es el documento MAESTRO del proyecto: reglas, arquitectura, cómo trabaja el
equipo de agentes, comandos, pendientes y versionado. El `README.md` es solo la
puerta de entrada y apunta aquí. **Junto a `README.md`, este es uno de los dos
únicos documentos oficiales** (los contratos en `docs/` son referencia técnica del
código, no documentación de proceso).

> **Recordatorio:** al cerrar cualquier cambio, añade una entrada en el
> [Historial de versiones](#historial-de-versiones) con **versión y fecha**, y
> actualiza los [Pendientes del desarrollador](#-pendientes-del-desarrollador).

## Qué es

Sistema que capta automáticamente **convocatorias reales y recientes**
(licitaciones, fondos, subvenciones, RFP/EOI) desde fuentes oficiales, guarda sus
**requisitos** y el **enlace a la publicación original** (`url_original`), y las
expone en un **dashboard web** con buscador, filtros, **asistente de IA** y un
filtro especial para **fundaciones nuevas/primerizas**. Todo corre con
`docker compose`.

**Stack:** Python 3.12 · FastAPI · SQLAlchemy 2.0 (síncrono) · Pydantic v2 ·
Alembic · httpx + tenacity (conectores) · APScheduler (worker) · PostgreSQL 16
(JSONB + tsvector en español) · frontend vanilla JS servido por nginx (proxy
`/api`, sin CORS) · capa de IA opcional (búsqueda en lenguaje natural, resumen y
soporte; **degrada con gracia** si el proveedor de IA no está configurado).

**Servicios y puertos en el host:** frontend `http://localhost:8090`, API
`http://localhost:8100/api/v1`, health `/api/v1/health`, Postgres `localhost:5433`.
Al arrancar, `api` aplica migraciones (`alembic upgrade head`) y **siembra las
fuentes** (idempotente); `worker` corre el scheduler con una primera pasada
inmediata.

### Fuentes actuales (7)

| `codigo` | Nombre | `tipo` | Estado |
|---|---|---|---|
| `secop` | SECOP II (Colombia Compra Eficiente) | `api` | activa |
| `pnud` | PNUD Procurement Notices | `html` | activa |
| `minciencias` | MinCiencias Convocatorias | `html` | activa |
| `mintic` | MinTIC Convocatorias | `html` | activa |
| `worldbank` | Banco Mundial (World Bank Procurement Notices, API v2) | `api` | activa |
| `grantsgov` | Grants.gov (EE. UU., subvenciones federales, API `search2` POST) | `api` | activa |
| `ungm` | UNGM (ONU) | `js` | **inactiva** (stub; la fuente carga por JS) |

### Filtro `apto_fundaciones_nuevas`

Columna booleana **DERIVADA** (heurística trazable) en `convocatorias`. La calcula
el pipeline (`app/pipeline/normalizer.py::es_apto_fundaciones_nuevas`) desde el
contenido REAL (título + descripción + requisitos + modalidad), comparándolo contra
señales editables en `app/constants.py`:

- `SEÑALES_FUNDACIONES_NUEVAS` (positivas) y `SEÑALES_EXPERIENCIA_REQUERIDA`
  (descalificantes).
- `true` = hay señal positiva **y** ninguna descalificante.
- `false` = sin evidencia (NO afirma "no apto").

Se expone como filtro `?apto_fundaciones_nuevas=true` en la API, como checkbox +
badge en el frontend, y como clave interpretable por el asistente de IA.
**Siempre verificar en la publicación oficial** (`url_original`).

## Reglas DURAS (no negociables)

1. **CERO datos inventados.**
   - Las convocatorias vienen ÚNICAMENTE del scraping real de fuentes oficiales.
   - `scripts/seed_fuentes.py` inserta SOLO las fuentes. **JAMÁS** convocatorias.
   - Los fixtures de tests son **capturas REALES** de cada fuente (en
     `tests/fixtures/<fuente>/`). Nada de payloads inventados a mano.
   - **Fecha imparseable o ausente → `NULL`** + warning. Nunca rellenar con una
     fecha inventada.
   - Todo dato ausente en la fuente → `None`/`NULL`. No adivinar.

2. **`url_original` SIEMPRE presente.** Cada convocatoria debe enlazar a su
   publicación real; un registro sin URL válida se descarta.

3. **Timestamps en UTC (TIMESTAMPTZ).** Toda fecha se normaliza a UTC antes de
   persistir.

4. **Hashes de deduplicación.**
   - `hash_dedupe = sha256("{codigo_fuente}:{id_externo}")` — UNIQUE global.
   - `hash_contenido = sha256(<campos relevantes normalizados>)` — el upsert solo
     ACTUALIZA si `hash_contenido` cambió. `ultima_vez_visto = now()` siempre.

## Vocabulario canónico (ver `app/constants.py`)

- Estado de convocatoria: `abierta | cerrada | adjudicada | vencida | desconocido`.
- Tipo de convocatoria: `licitacion | subvencion | fondo | rfp | eoi | otro`.
- Tipo de fuente: `api | html | js`.
- Trigger de ejecución: `cron | manual`. Estado de ejecución:
  `en_curso | ok | parcial | error`.

Los conectores entregan `estado_fuente` **crudo** (texto libre de cada fuente); el
pipeline (`normalizer.map_estado`) lo mapea al estado canónico. Los conectores NO
mapean estado.

## Arquitectura de conectores (plugin)

- Agregar una fuente = crear `app/connectors/<fuente>.py` con una subclase de
  `BaseConnector` (`codigo`, `nombre`, `fetch(config) -> list[RawConvocatoria]`).
- El **auto-registro** (`connectors/__init__.py`, vía pkgutil) la descubre sola.
  **Nadie edita** `base.py`, `http.py` ni `__init__.py` para añadir una fuente.
- Usar el `HttpClient` compartido (`connectors/http.py`): expone `.get()` y
  `.post(url, *, json=...)` (para fuentes que exigen POST, ej. Grants.gov), con
  timeout, reintentos (429/5xx/red), User-Agent, pausa y token Socrata resueltos.
- `fetch()` devuelve `RawConvocatoria` (contrato en `app/schemas/raw.py`). Errores
  como excepciones tipadas (`ConnectorError`, `RateLimitError`, `ParseError`,
  `SourceUnavailableError`).

## Separación de capas (estricta)

- `api/routers/` solo orquestan (request → service → response).
- `api/services/` contienen TODA la lógica de negocio.
- `models/` solo tablas SQLAlchemy. `schemas/` solo Pydantic v2
  (`*Request` / `*Response`).
- Nunca retornar un modelo SQLAlchemy directo: siempre pasar por un schema
  Response.
- `SessionLocal` usa `autoflush=False` → llamar `db.flush()` antes de queries que
  deban ver objetos pendientes (`add`/`delete`).
- Toda migración de esquema va por Alembic. Nunca tocar el esquema sin migración.
  La migración y los modelos deben coincidir 1:1.
- **Migraciones actuales:** `0001` esquema inicial; `0002` añade
  `apto_fundaciones_nuevas` (+ índice).

## Cómo trabaja el equipo de agentes

### Flujo de lectura obligatorio (antes de tocar nada)

1. `README.md` — puerta de entrada, contexto rápido y estructura del repo.
2. `CLAUDE.md` (este documento) — contexto completo: reglas, arquitectura,
   comandos, versionado.
3. La sección [📌 Pendientes del desarrollador](#-pendientes-del-desarrollador) —
   para saber **QUÉ** y **DÓNDE** trabajar sin escanear todo el repositorio.

### Orquestación

- Usa el agente `tech-lead` para descomponer el objetivo y delegar en los
  especialistas disponibles: `backend-fastapi`, `frontend-web`,
  `automation-engineer`, `qa-tester`, `security-auditor`, `devops-git`.
- Lanza en **PARALELO** los trabajos independientes.

### Regla de RUTAS EXCLUSIVAS (cero solapamiento)

- Un archivo lo toca **UN solo agente** por tarea.
- Los archivos de **CONTRATO COMPARTIDO** — `models/`, `schemas/`,
  `constants.py`, `connectors/base.py|http.py|__init__.py`, el pipeline central,
  las migraciones Alembic y `docs/*-contract.md` — los edita de forma **COHESIVA
  el orquestador** (o un único agente), **nunca varios a la vez**.
- Los conectores (`app/connectors/<fuente>.py` + sus tests + sus fixtures) y el
  frontend (`frontend/**`) se delegan en paralelo.

### Reparto por rutas (ejemplo, actualizado a las 7 fuentes)

| Agente / trabajo | Rutas exclusivas |
|---|---|
| SECOP | `app/connectors/secop.py` + `tests/connectors/test_secop*` + `tests/fixtures/secop/` |
| PNUD (+ stub UNGM) | `app/connectors/pnud.py`, `ungm.py` + tests + fixtures |
| MinCiencias + MinTIC | `app/connectors/minciencias.py`, `mintic.py` + tests + fixtures |
| World Bank | `app/connectors/worldbank.py` + tests + fixtures |
| Grants.gov | `app/connectors/grantsgov.py` + tests + fixtures |
| Pipeline + worker + utils | `app/pipeline/*`, `app/worker/scheduler.py`, `app/utils/*` + tests |
| API REST | `app/api/**` (routers, services, deps nuevos) + tests |
| Frontend | `frontend/**` (contra `docs/api-contract.md`) |

> Los archivos compartidos (`constants.py`, `models/`, `schemas/`, migraciones,
> `seed_fuentes.py`) NO aparecen en la tabla: los toca solo el orquestador.

### Un conector nuevo, paso a paso

1. Subclase de `BaseConnector` en su propio archivo `app/connectors/<fuente>.py`.
2. **VERIFICA la fuente EN VIVO** y guarda un **fixture de captura REAL** en
   `tests/fixtures/<fuente>/`.
3. Escribe sus tests. NO edita archivos compartidos.
4. El registro en `seed_fuentes.py` (y cualquier cambio en `constants.py`,
   `models/`, `schemas/` o migraciones) lo hace **el orquestador**.

### Cierre de cualquier cambio

- `qa-tester` valida **SIEMPRE** (suite completa sobre Postgres real + smoke en
  vivo de los conectores afectados).
- `security-auditor` audita **antes de pushear**.
- Actualiza el [Historial de versiones](#historial-de-versiones) (versión + fecha)
  y limpia/actualiza los [Pendientes](#-pendientes-del-desarrollador).

## Comandos docker compose

```bash
# Levantar todo (build). Puertos host: db 5433, api 8100, frontend 8090.
docker compose up -d --build

# Health:  curl http://localhost:8100/api/v1/health
# Frontend: http://localhost:8090

# Logs:
docker compose logs -f api
docker compose logs -f worker

# Correr los tests (Postgres real, NO SQLite):
docker compose run --rm api pytest

# Disparar un scraping manual:
curl -X POST "http://localhost:8100/api/v1/scraping/run"              # todas
curl -X POST "http://localhost:8100/api/v1/scraping/run?fuente=secop" # una fuente

# Migraciones:
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic revision -m "descripcion"   # (autogenerate: --autogenerate)

# Reset total (borra el volumen pgdata):
docker compose down -v
```

### Entorno

- Copiar `.env.example` → `.env` (el `.env` está gitignored; contiene
  credenciales).
- Keywords del filtro: `SCRAPE_KEYWORDS` (lista por comas, editable sin tocar
  código).
- La IA de soporte lee el manual desde `settings.ai_manual_path`
  (`docs/MANUAL_USUARIO.md`).
- Editar desde Windows hacia WSL: `.gitattributes` fuerza `eol=lf` (crítico para
  `*.sh`).

### Contratos en `docs/` (referéncialos, NO los borres — el código los usa)

- `docs/api-contract.md` — contrato REST **congelado**; el frontend trabaja contra
  él.
- `docs/ai-contract.md` — contrato de los endpoints de IA.
- `docs/MANUAL_USUARIO.md` — lo lee la IA de soporte vía `settings.ai_manual_path`.

## Solución de problemas

### Gotcha de migraciones al correr tests con `run --rm`

`docker compose run --rm api pytest` **NO aplica migraciones por sí solo** (el
entrypoint solo migra cuando NO se le pasa comando). Tras cambios de esquema hay
que ejecutar **antes**:

```bash
docker compose up -d --build api   # recrea el contenedor de larga vida y aplica alembic upgrade head
```

y luego correr los tests con `run --rm`. Si no, darán falsos errores de "columna no
existe".

### El contenedor `frontend` no arranca en Docker Desktop + WSL

Si el proyecto vive en el sistema de archivos de WSL (`\wsl.localhost\...`) y
Docker Desktop corre en Windows, `docker compose up` puede fallar SOLO en el
servicio `frontend` con:

```
Error response from daemon: accessing specified distro mount service:
stat /run/guest-services/distro-services/ubuntu.sock: no such file or directory
```

Es un problema de integración WSL de Docker Desktop con el **bind-mount** de
`./frontend` (los servicios `db`/`api`/`worker` no usan bind-mount y arrancan
bien). Soluciones, en orden de preferencia:

1. **Habilitar la integración WSL de la distro**: Docker Desktop → *Settings →
   Resources → WSL Integration* → activar **Ubuntu** → *Apply & Restart*.
2. **Levantar el stack desde una terminal de WSL Ubuntu** (no desde PowerShell):
   `cd ~/.../06.scraping_convocatorias && docker compose up -d`. Desde dentro de
   WSL el mount es nativo y no requiere el guest-services socket.
3. **Workaround sin bind-mount** (sirve los estáticos copiándolos a un nginx):
   ```bash
   docker run -d --name conv-fe --network convocatorias_default -p 8090:80 nginx:alpine
   docker cp ./frontend/index.html conv-fe:/usr/share/nginx/html/index.html
   docker cp ./frontend/css conv-fe:/usr/share/nginx/html/
   docker cp ./frontend/js  conv-fe:/usr/share/nginx/html/
   docker cp ./frontend/nginx.conf conv-fe:/etc/nginx/conf.d/default.conf
   docker exec conv-fe nginx -s reload
   ```
   (Solo para verificación; con la opción 1 o 2 el servicio `frontend` del compose
   funciona con recarga en vivo.)

## 📌 Pendientes del desarrollador

> **Los agentes deben leer esta sección primero** para ubicar el trabajo sin
> escanear todo el repositorio. El usuario mantiene aquí las tareas y **las rutas
> exactas** a modificar (ahorra tokens de contexto a los agentes).

| Pendiente | Rutas afectadas | Prioridad | Notas |
|---|---|---|---|
| _(ejemplo)_ Añadir conector ReliefWeb | `app/connectors/reliefweb.py` + tests + fixtures + registrar en `scripts/seed_fuentes.py` | media | requiere `appname` aprobado de ReliefWeb; verificar la fuente en vivo |
| _(ejemplo)_ Activar conector UNGM (hoy stub/JS) | `app/connectors/ungm.py` + tests + fixtures | baja | la fuente carga por JS; evaluar render headless antes |
| _(añade aquí tus tareas reales)_ | | | |

## Historial de versiones

> Más reciente arriba. Cada entrada lleva **versión + fecha**.

- **v1.3.0 — 2026-07-23**: exportación a Excel (`POST /convocatorias/export`) de
  las convocatorias seleccionadas "para participar" (selección persistente +
  barra flotante + descarga `.xlsx` con `openpyxl`, incluye `url_original` para
  verificar existencia); fix de la ficha del Banco Mundial: el `notice_text` HTML
  se aplana a texto legible con `html_to_text` (`app/utils/text.py`) y el frontend
  respeta saltos de línea. Nueva dependencia `openpyxl` (requiere rebuild de la
  imagen `api`).
- **v1.2.0 — 2026-07-23**: filtro para fundaciones nuevas/primerizas (columna
  derivada `apto_fundaciones_nuevas`, migración `0002`, filtro en API / IA /
  frontend); conectores nuevos `worldbank` y `grantsgov` (fixtures reales,
  verificados en vivo); `HttpClient.post`; `map_estado` ampliado; consolidación de
  documentación (README + CLAUDE.md; `AGENTS.md` fusionado aquí y eliminado).
  Verificado: 66 tests en verde sobre Postgres real + smoke en vivo.
- **v1.1.0 — 2026-07-22**: asistente de IA (búsqueda en lenguaje natural, resumen
  y soporte) con degradación con gracia; funcionamiento en Docker sobre WSL; logo.
- **v1.0.0 — 2026-07-22**: sistema base de búsqueda de convocatorias — backend
  (conectores SECOP/PNUD/MinCiencias/MinTIC, pipeline, worker APScheduler, API
  REST), frontend y documentación inicial.
