"""Worker APScheduler para ejecutar scraping periódico."""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.config import settings
from app.pipeline.runner import run

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


def main() -> None:
    scheduler = BlockingScheduler(timezone="UTC")
    scheduler.add_job(
        run,
        "interval",
        minutes=settings.scrape_interval_minutes,
        args=[None, "cron"],
        id="scraping-cron",
        max_instances=1,
        coalesce=True,
        next_run_time=None,
    )
    logger.info("Ejecutando scraping inicial")
    run(None, "cron")
    logger.info("Scheduler activo cada %s minutos", settings.scrape_interval_minutes)
    scheduler.start()


if __name__ == "__main__":
    main()
