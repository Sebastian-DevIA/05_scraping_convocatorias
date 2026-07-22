"""Auto-registro de conectores (plugins).

Descubre por pkgutil todas las subclases de `BaseConnector` definidas en los
módulos de este paquete (excepto `base` y `http`) y las expone por `codigo`.

Agregar una fuente = crear `connectors/<fuente>.py` con una subclase de
`BaseConnector`. Nadie toca este archivo (cero conflictos entre agentes).
"""

import importlib
import inspect
import pkgutil

from app.connectors.base import (
    BaseConnector,
    ConnectorError,
    ParseError,
    RateLimitError,
    SourceUnavailableError,
)
from app.connectors.http import HttpClient, get_http_client

# Módulos que NO contienen conectores (infraestructura compartida).
_EXCLUIR = {"base", "http"}

_registry: dict[str, BaseConnector] | None = None


def _descubrir() -> dict[str, BaseConnector]:
    registro: dict[str, BaseConnector] = {}
    for modinfo in pkgutil.iter_modules(__path__):
        nombre = modinfo.name
        if nombre in _EXCLUIR or nombre.startswith("_"):
            continue
        modulo = importlib.import_module(f"{__name__}.{nombre}")
        for _, obj in inspect.getmembers(modulo, inspect.isclass):
            # Solo clases definidas en ESTE módulo (no BaseConnector importado).
            if (
                issubclass(obj, BaseConnector)
                and obj is not BaseConnector
                and obj.__module__ == modulo.__name__
                and not inspect.isabstract(obj)
            ):
                instancia = obj()
                registro[instancia.codigo] = instancia
    return registro


def get_connectors() -> dict[str, BaseConnector]:
    """Devuelve `{codigo: instancia}` de todos los conectores registrados (cacheado)."""
    global _registry
    if _registry is None:
        _registry = _descubrir()
    return _registry


def get_connector(codigo: str) -> BaseConnector | None:
    """Devuelve el conector con ese código, o None si no existe."""
    return get_connectors().get(codigo)


__all__ = [
    "BaseConnector",
    "ConnectorError",
    "RateLimitError",
    "ParseError",
    "SourceUnavailableError",
    "HttpClient",
    "get_http_client",
    "get_connectors",
    "get_connector",
]
