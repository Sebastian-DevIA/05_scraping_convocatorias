# CLAUDE.md — Reglas del proyecto `06.scraping_convocatorias`

Sistema automatizado de búsqueda de convocatorias (SECOP, PNUD, MinCiencias,
MinTIC, UNGM). API FastAPI + worker APScheduler + Postgres + frontend nginx,
todo con `docker compose`.

## Reglas DURAS (no negociables)

1. **CERO datos inventados.**
   - Las convocatorias vienen ÚNICAMENTE del scraping real de fuentes oficiales.
   - `scripts/seed_fuentes.py` inserta SOLO las 5 fuentes. **JAMÁS** convocatorias.
   - Los fixtures de tests son **capturas REALES** de cada fuente (guardadas en
     `tests/fixtures/<fuente>/`). Nada de payloads inventados a mano.
   - **Fecha imparseable o ausente → `NULL`** + warning. Nunca rellenar con una fecha inventada.
   - Todo dato ausente en la fuente → `None`/`NULL`. No adivinar.

2. **`url_original` SIEMPRE presente.** Cada convocatoria debe enlazar a su publicación real.

3. **Timestamps en UTC (TIMESTAMPTZ).** Toda fecha se normaliza a UTC antes de persistir.

4. **Hashes de deduplicación.**
   - `hash_dedupe = sha256("{codigo_fuente}:{id_externo}")` — UNIQUE global.
   - `hash_contenido = sha256(<campos relevantes normalizados>)` — el upsert solo
     ACTUALIZA si `hash_contenido` cambió. `ultima_vez_visto = now()` siempre.

## Vocabulario canónico (ver `app/constants.py`)

- Estado de convocatoria: `abierta | cerrada | adjudicada | vencida | desconocido`.
- Tipo de convocatoria: `licitacion | subvencion | fondo | rfp | eoi | otro`.
- Tipo de fuente: `api | html | js`.
- Trigger de ejecución: `cron | manual`. Estado de ejecución: `en_curso | ok | parcial | error`.

El `estado_fuente` (texto libre de cada fuente) lo mapea el pipeline a un estado
canónico. Los conectores NO mapean estado; entregan `estado_fuente` crudo.

## Arquitectura de conectores (plugin)

- Agregar una fuente = crear `app/connectors/<fuente>.py` con una subclase de
  `BaseConnector` (`codigo`, `nombre`, `fetch(config) -> list[RawConvocatoria]`).
- El **auto-registro** (`connectors/__init__.py`, vía pkgutil) la descubre sola.
  **Nadie edita** `base.py`, `http.py` ni `__init__.py` para añadir una fuente.
- Usar el `HttpClient` compartido (`connectors/http.py`): timeout, reintentos,
  User-Agent, pausa y token Socrata ya resueltos.
- `fetch()` devuelve `RawConvocatoria` (contrato en `app/schemas/raw.py`). Errores
  como excepciones tipadas (`ConnectorError`, `RateLimitError`, `ParseError`,
  `SourceUnavailableError`).

## Separación de capas (estricta)

- `api/routers/` solo orquestan (request → service → response).
- `services/` (Fase 1) contienen TODA la lógica de negocio.
- `models/` solo tablas SQLAlchemy. `schemas/` solo Pydantic v2 (`*Request` / `*Response`).
- Nunca retornar un modelo SQLAlchemy directo: siempre pasar por un schema Response.
- `SessionLocal` usa `autoflush=False` → llamar `db.flush()` antes de queries que
  deban ver objetos pendientes (`add`/`delete`).
- Toda migración de esquema va por Alembic. Nunca tocar el esquema sin migración.
- La migración inicial y los modelos deben coincidir 1:1.

## Rutas EXCLUSIVAS por agente (Fase 1 — cero solapamiento)

En Fase 1 **nadie modifica** `models/`, `schemas/`, `connectors/base.py|http.py|__init__.py`,
ni el contrato `docs/api-contract.md`.

| Agente | Rutas exclusivas |
|---|---|
| A — SECOP | `app/connectors/secop.py` + `tests/connectors/test_secop*` + `tests/fixtures/secop/` |
| B — PNUD (+stub UNGM) | `app/connectors/pnud.py`, `ungm.py` + tests + fixtures |
| C — MinCiencias + MinTIC | `app/connectors/minciencias.py`, `mintic.py` + tests + fixtures |
| D — pipeline + worker + utils | `app/pipeline/*`, `app/worker/scheduler.py`, `app/utils/*` + tests |
| E — API REST | `app/api/**` (routers, services, deps nuevos) + tests |
| F — frontend | `frontend/**` (contra `docs/api-contract.md`) |

Cada agente de conector **verifica su fuente en vivo** y guarda fixtures de capturas REALES.

## Comandos docker compose útiles

```bash
# Levantar todo (build). Puertos host: db 5433, api 8100, frontend 8090.
docker compose up -d --build

# Solo BD + API (criterio de salida Fase 0):
docker compose up db api

# Health:  curl http://localhost:8100/api/v1/health
# Frontend: http://localhost:8090

# Logs:
docker compose logs -f api
docker compose logs -f worker

# Correr los tests (Postgres real, NO SQLite):
docker compose run --rm api pytest

# Disparar un scraping manual:
curl -X POST "http://localhost:8100/api/v1/scraping/run"           # todas
curl -X POST "http://localhost:8100/api/v1/scraping/run?fuente=secop"

# Migraciones:
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic revision -m "descripcion"      # (autogenerate: --autogenerate)

# Reset total (borra el volumen pgdata):
docker compose down -v
```

## Entorno

- Copiar `.env.example` → `.env` (el `.env` está gitignored; contiene credenciales).
- Keywords del filtro: `SCRAPE_KEYWORDS` (lista por comas, editable sin tocar código).
- Editar desde Windows hacia WSL: `.gitattributes` fuerza `eol=lf` (crítico para `*.sh`).
