"""Fixtures de pytest.

Se usa la MISMA Postgres del compose (el plan exige Postgres real por
JSONB/tsvector; NO SQLite). Cada test corre dentro de una transacción que se
revierte al terminar -> aislamiento sin ensuciar la BD.

Variables de entorno:
  - TEST_DATABASE_URL: URL de la BD de test. Si no se define, usa DATABASE_URL.
"""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker

# Importa TODOS los modelos (registro en metadata) antes de create_all.
import app.models  # noqa: F401
from app.api.main import app
from app.database import Base, get_db

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://convocatorias:convocatorias@db:5432/convocatorias",
)


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    """Engine de test. Crea el esquema si falta (idempotente, no hace drop)."""
    eng = create_engine(TEST_DATABASE_URL, future=True)
    # checkfirst=True: no recrea tablas ya existentes (creadas por alembic).
    Base.metadata.create_all(eng, checkfirst=True)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine: Engine) -> Generator[Session, None, None]:
    """Sesión ligada a una transacción que se revierte al final del test."""
    connection: Connection = engine.connect()
    trans = connection.begin()
    TestingSession = sessionmaker(
        bind=connection, autoflush=False, autocommit=False, future=True
    )
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient con `get_db` sobreescrito para usar la sesión transaccional."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
