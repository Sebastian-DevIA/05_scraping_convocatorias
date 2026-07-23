# Sistema automatizado de búsqueda de convocatorias

Capta automáticamente **convocatorias reales y recientes** (licitaciones, fondos,
subvenciones, RFP/EOI) desde **7 fuentes oficiales** — SECOP II, PNUD, MinCiencias,
MinTIC, Banco Mundial, Grants.gov y UNGM (stub) —, guarda sus **requisitos** y el
**enlace a la publicación original** (`url_original`), y las expone en un
**dashboard web** con buscador, filtros y **asistente de IA**.

Incluye un filtro especial para **fundaciones nuevas/primerizas**
(`apto_fundaciones_nuevas`), que marca las convocatorias sin barreras de
experiencia previa a partir de su contenido real. Todo corre con `docker compose`.

> 📖 **Antes de modificar, mejorar o dar contexto al software, lee
> [`CLAUDE.md`](CLAUDE.md)** — contiene TODO: reglas, arquitectura, uso de agentes,
> comandos, pendientes y versionado.

> Regla dura del proyecto: **cero datos inventados** (las convocatorias vienen solo
> del scraping real). Detalles y demás reglas en [`CLAUDE.md`](CLAUDE.md).

## Stack

Python 3.12 · FastAPI · SQLAlchemy 2.0 (síncrono) · Pydantic v2 · Alembic ·
httpx + tenacity (conectores) · APScheduler (worker) · PostgreSQL 16
(JSONB + tsvector en español) · frontend vanilla JS servido por nginx · capa de IA
opcional (degrada con gracia si el proveedor no está configurado).

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

Al arrancar, `api` aplica migraciones y siembra las fuentes (idempotente); el
`worker` corre el scheduler con una primera pasada inmediata. Comandos detallados
(tests, migraciones, scraping manual, troubleshooting) en [`CLAUDE.md`](CLAUDE.md).

## Estructura del repo

```
06.scraping_convocatorias/
├── docker-compose.yml / .env.example
├── README.md                      # esta puerta de entrada
├── CLAUDE.md                      # documento maestro: reglas, arquitectura, agentes, comandos, versionado
├── docs/
│   ├── api-contract.md            # contrato REST congelado (el frontend trabaja contra esto)
│   ├── ai-contract.md             # contrato de los endpoints de IA
│   └── MANUAL_USUARIO.md          # lo lee la IA de soporte
├── backend/
│   ├── Dockerfile / entrypoint.sh / pyproject.toml / alembic.ini
│   ├── alembic/versions/          # 0001 esquema inicial · 0002 apto_fundaciones_nuevas
│   ├── app/
│   │   ├── config.py / database.py / constants.py
│   │   ├── models/                # Fuente, Convocatoria, Ejecucion
│   │   ├── schemas/               # Pydantic v2 (+ raw.py: contrato conector→pipeline)
│   │   ├── connectors/            # base.py, http.py, __init__.py (auto-registro)
│   │   │                          # secop, pnud, minciencias, mintic, worldbank, grantsgov, ungm
│   │   ├── pipeline/              # normalizer (incl. apto_fundaciones_nuevas), dedupe, upsert, runner
│   │   ├── api/                   # main.py, deps.py, routers/, services/
│   │   ├── ai/                    # asistente de IA (búsqueda NL, resumen, soporte)
│   │   ├── worker/                # scheduler.py (APScheduler)
│   │   └── utils/                 # dates.py, text.py
│   ├── scripts/seed_fuentes.py    # SOLO fuentes, jamás convocatorias
│   └── tests/                     # conftest + fixtures reales por fuente
└── frontend/                      # nginx.conf + index.html + css/js
```

## Más información

- **[`CLAUDE.md`](CLAUDE.md)** — reglas, arquitectura de conectores y capas, cómo
  trabaja el equipo de agentes, comandos docker, solución de problemas, pendientes
  e historial de versiones.
- **[`docs/`](docs/)** — contratos técnicos (`api-contract.md`, `ai-contract.md`) y
  `MANUAL_USUARIO.md`.
