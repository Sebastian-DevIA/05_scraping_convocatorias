"""Router de métricas agregadas."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.services.stats import obtener_stats
from app.schemas.stats import StatsResponse

router = APIRouter(tags=["stats"])


@router.get("", response_model=StatsResponse)
def stats(db: Session = Depends(get_db)) -> StatsResponse:
    return obtener_stats(db)
