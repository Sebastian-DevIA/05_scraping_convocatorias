"""Modelos ORM.

IMPORTANTE: importar TODOS los modelos aquí para que Alembic (autogenerate) y
`Base.metadata.create_all` (tests) los registren en el metadata.
"""

from app.database import Base
from app.models.convocatoria import Convocatoria
from app.models.ejecucion import Ejecucion
from app.models.fuente import Fuente
from app.models.gestion import Gestion

__all__ = ["Base", "Fuente", "Convocatoria", "Ejecucion", "Gestion"]
