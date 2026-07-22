"""Router para disparar scraping manual."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status

from app.pipeline.runner import fuente_existe, run

router = APIRouter(tags=["scraping"])


@router.post("/run", status_code=status.HTTP_202_ACCEPTED)
def run_scraping(
    background_tasks: BackgroundTasks,
    fuente: str | None = Query(None),
) -> dict:
    if fuente is not None and not fuente_existe(fuente):
        raise HTTPException(status_code=404, detail="Fuente no encontrada")
    background_tasks.add_task(run, fuente, "manual")
    return {
        "status": "accepted",
        "trigger": "manual",
        "fuente": fuente,
        "detail": "Scraping encolado.",
    }
