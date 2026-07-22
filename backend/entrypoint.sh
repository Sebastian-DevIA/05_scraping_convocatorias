#!/bin/sh
# Entrypoint compartido por api y worker.
#  - Siempre espera a que la BD acepte conexiones.
#  - Si se pasa un comando (worker: `python -m app.worker.scheduler`), lo ejecuta
#    directamente: las migraciones ya las aplicó el servicio api (depends_on healthy).
#  - Sin comando (rol api por defecto): alembic upgrade head + seed + uvicorn.
set -e

echo "[entrypoint] Esperando a la base de datos..."
python - <<'PY'
import sys
import time

from sqlalchemy import create_engine, text

from app.config import settings

for intento in range(1, 61):
    try:
        engine = create_engine(settings.database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        print(f"[entrypoint] BD disponible (intento {intento}).")
        break
    except Exception as exc:  # noqa: BLE001 - espera activa tolerante
        print(f"[entrypoint] BD no lista ({intento}/60): {exc}")
        time.sleep(2)
else:
    print("[entrypoint] La BD no respondió a tiempo.")
    sys.exit(1)
PY

# Rol worker (u otro comando explícito): las migraciones ya están aplicadas.
if [ "$#" -gt 0 ]; then
    echo "[entrypoint] Ejecutando comando: $*"
    exec "$@"
fi

# Rol API por defecto.
echo "[entrypoint] Aplicando migraciones (alembic upgrade head)..."
alembic upgrade head

echo "[entrypoint] Sembrando fuentes (idempotente)..."
python scripts/seed_fuentes.py

echo "[entrypoint] Iniciando API (uvicorn)..."
exec uvicorn app.api.main:app --host 0.0.0.0 --port 8000
