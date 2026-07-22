# Sistema automatizado de búsqueda de convocatorias

Capta automáticamente **convocatorias reales y recientes** (licitaciones, fondos,
RFP/EOI) de fuentes oficiales — SECOP II, PNUD, MinCiencias, MinTIC, UNGM —, guarda
sus **requisitos** y el **enlace a la publicación original**, y las expone en un
**dashboard web**. Todo corre con `docker compose`.

> Regla dura del proyecto: **cero datos inventados**. Ver `CLAUDE.md`.

## Stack

- **Backend**: Python 3.12 · FastAPI · SQLAlchemy 2.0 (síncrono) · Pydantic v2 · Alembic.
- **Ingesta**: httpx + tenacity (conectores plugin) · APScheduler (worker).
- **BD**: PostgreSQL 16 (JSONB + tsvector full-text en español).
- **Frontend**: vanilla JS servido por nginx, proxy `/api` (sin CORS).

## Cómo levantar

```bash
cp .env.example .env          # ajustar credenciales (el .env real está gitignored)
docker compose up -d --build
```

Servicios y puertos en el host:

| Servicio | URL / puerto |
|---|---|
| Frontend | http://localhost:8090 |
| API | http://localhost:8100/api/v1 |
| Health | http://localhost:8100/api/v1/health |
| Postgres | localhost:5433 |

Al arrancar, `api` aplica migraciones (`alembic upgrade head`) y siembra las 5
fuentes (idempotente); el `worker` corre el scheduler con una primera pasada
inmediata. Ver comandos útiles en `CLAUDE.md`.

## Estructura

```
06.scraping_convocatorias/
├── docker-compose.yml / .env.example / CLAUDE.md
├── docs/api-contract.md          # contrato REST congelado (el frontend trabaja contra esto)
├── backend/
│   ├── Dockerfile / entrypoint.sh / pyproject.toml / alembic.ini / alembic/
│   ├── app/
│   │   ├── config.py / database.py / constants.py
│   │   ├── models/      # Fuente, Convocatoria, Ejecucion
│   │   ├── schemas/     # Pydantic v2 (+ raw.py: contrato conector→pipeline)
│   │   ├── connectors/  # base.py, http.py, __init__.py (auto-registro) + <fuente>.py
│   │   ├── pipeline/    # normalizer, dedupe, upsert, runner   (Fase 1)
│   │   ├── api/         # main.py, deps.py, routers/           (Fase 1 amplía)
│   │   ├── worker/      # scheduler.py                         (Fase 1)
│   │   └── utils/       # dates.py, text.py                    (Fase 1)
│   ├── scripts/seed_fuentes.py   # SOLO fuentes, jamás convocatorias
│   └── tests/           # conftest + fixtures reales por fuente
└── frontend/            # nginx.conf + index.html (+ css/js en Fase 1)
```

## Desarrollo

- Tests (Postgres real, no SQLite): `docker compose run --rm api pytest`.
- Migraciones: `docker compose run --rm api alembic upgrade head`.
- Keywords del filtro: variable `SCRAPE_KEYWORDS` en `.env` (lista por comas).

## Estado

Fase 0 (esqueleto y contratos) completa. Conectores, pipeline, API completa y
frontend se implementan en Fase 1. Ver el plan y `CLAUDE.md`.

## Solución de problemas

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
   (Solo para verificación; con la opción 1 o 2 el servicio `frontend` del
   compose funciona con recarga en vivo.)
