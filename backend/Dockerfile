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
# El manual de usuario (contexto de la IA de soporte) NO se copia en build:
# se monta en runtime como volumen de solo lectura (ver docker-compose, servicio
# api: ./docs -> /app/docs). Así el build no requiere BuildKit/additional_contexts
# y sigue funcionando con el builder clasico (p. ej. Docker nativo en WSL).
COPY entrypoint.sh ./entrypoint.sh

# El bit ejecutable no siempre sobrevive al editar desde Windows: lo fijamos
# aquí y además invocamos el script vía `sh` en el ENTRYPOINT.
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["sh", "/app/entrypoint.sh"]
