"""Contrato base de los conectores (plugins de fuente).

Agregar una fuente = agregar un archivo `connectors/<fuente>.py` con una
subclase de `BaseConnector`. El auto-registro (ver `__init__.py`) la descubre
sin tocar código compartido.
"""

from abc import ABC, abstractmethod

from app.schemas.raw import RawConvocatoria


# --- Excepciones tipadas ---------------------------------------------------
class ConnectorError(Exception):
    """Error base de un conector. El runner lo captura y marca la ejecución 'error'."""


class RateLimitError(ConnectorError):
    """La fuente respondió con rate limit (HTTP 429) tras agotar reintentos."""


class ParseError(ConnectorError):
    """El HTML/JSON de la fuente no pudo parsearse (posible cambio de estructura)."""


class SourceUnavailableError(ConnectorError):
    """La fuente no está disponible (5xx, timeout, red) tras agotar reintentos."""


# --- Contrato --------------------------------------------------------------
class BaseConnector(ABC):
    """Interfaz que todo conector debe implementar.

    Atributos de clase obligatorios:
        codigo: identificador estable de la fuente (debe coincidir con `fuentes.codigo`).
        nombre: nombre legible de la fuente.
    """

    codigo: str
    nombre: str

    @abstractmethod
    def fetch(self, config: dict) -> list[RawConvocatoria]:
        """Obtiene y extrae convocatorias crudas de la fuente.

        Args:
            config: config JSONB de la fuente (keywords, max_paginas,
                rate_limit_seconds, y lo que cada conector necesite).

        Returns:
            Lista de `RawConvocatoria` (posiblemente vacía). NUNCA inventa datos:
            campos ausentes -> None.

        Raises:
            ConnectorError (o subclase) ante fallos recuperables/no recuperables.
        """
        raise NotImplementedError

    def __repr__(self) -> str:  # pragma: no cover - ayuda de depuración
        return f"<Connector {getattr(self, 'codigo', '?')}>"
