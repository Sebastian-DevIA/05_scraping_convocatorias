"""Router de health-check. `GET /api/v1/health` -> status + chequeo de BD."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.api.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/health", summary="Estado del servicio y de la base de datos")
def health(db: Session = Depends(get_db)) -> dict:
    """Devuelve el estado del servicio y verifica la conexión a la BD.

    - `status`: "ok" si la BD responde, "degraded" si no.
    - `database`: "ok" | "error".
    """
    try:
        db.execute(text("SELECT 1"))
        database_ok = True
    except Exception:  # noqa: BLE001 - health nunca debe lanzar
        database_ok = False

    return {
        "status": "ok" if database_ok else "degraded",
        "version": __version__,
        "database": "ok" if database_ok else "error",
        "time": datetime.now(timezone.utc).isoformat(),
    }
