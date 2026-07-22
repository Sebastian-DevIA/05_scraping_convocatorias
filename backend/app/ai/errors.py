"""Errores tipados de la capa de IA."""


class AIError(Exception):
    """Base de todos los errores de la capa de IA."""


class AIProviderError(AIError):
    """Un proveedor concreto falló (timeout, HTTP != 2xx, respuesta ilegible)."""

    def __init__(self, provider: str, message: str) -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")


class AIUnavailableError(AIError):
    """Todos los proveedores fallaron o la IA está deshabilitada.

    El servicio la traduce a una respuesta degradada (nunca a un 500 crudo).
    """
