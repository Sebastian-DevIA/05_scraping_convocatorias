FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# curl -> healthcheck del compose contra /api/v1/health.
# (psycopg2-binary trae libpq embebido, no hace falta libpq-dev.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# 1) Dependencias (capa cacheable): manifiesto + paquete, instalación editable.
COPY pyproject.toml ./
COPY app ./app
RUN pip install --upgrade pip && pip install -e ".[dev]"

# 2) Resto del backend (migraciones, seed, entrypoint, tests).
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts
COPY tests ./tests
# Manual de usuario (contexto de soporte de la capa de IA). Llega vía el
# contexto adicional `docs` declarado en docker-compose (additional_contexts),
# manteniendo docs/ como única fuente de verdad (sin duplicar ni bind-mount).
COPY --from=docs . ./docs
COPY entrypoint.sh ./entrypoint.sh

# El bit ejecutable no siempre sobrevive al editar desde Windows: lo fijamos
# aquí y además invocamos el script vía `sh` en el ENTRYPOINT.
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
