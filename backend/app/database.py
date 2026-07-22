"""Capa de acceso a datos: engine síncrono, SessionLocal y Base declarativa."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# Engine síncrono (SQLAlchemy 2.0). pool_pre_ping evita conexiones muertas.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

# autoflush=False -> recordar db.flush() antes de queries que deban ver
# objetos pendientes (add/delete). Convención del repo.
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


class Base(DeclarativeBase):
    """Base declarativa para todos los modelos ORM."""


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI: abre una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
