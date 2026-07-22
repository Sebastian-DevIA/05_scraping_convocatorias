"""Stub UNGM del MVP: fuente JS desactivada por seed."""

from app.connectors.base import BaseConnector
from app.schemas.raw import RawConvocatoria


class UngmConnector(BaseConnector):
    codigo = "ungm"
    nombre = "UNGM"

    def fetch(self, config: dict) -> list[RawConvocatoria]:
        return []
