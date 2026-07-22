"""Configuración de la aplicación (pydantic-settings).

Lee las variables de entorno (o el `.env` en desarrollo local). Los nombres de
campo se corresponden con las variables en MAYÚSCULAS de `.env.example`
(pydantic-settings es case-insensitive).
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignora POSTGRES_*, DB_PORT, etc. que no usa la app
    )

    # --- Base de datos ---
    database_url: str = "postgresql+psycopg2://convocatorias:convocatorias@db:5432/convocatorias"

    # --- Scraping ---
    scrape_interval_minutes: int = 360
    # Lista separada por comas; se expone ya parseada en `keywords`.
    scrape_keywords: str = (
        "tecnología,TIC,inclusión digital,población vulnerable,"
        "innovación social,educación,transformación digital,software"
    )

    # --- SECOP II (Socrata) ---
    secop_app_token: str | None = None

    # --- HTTP ---
    http_user_agent: str = "ConvocatoriasBot/0.1 (+contacto: sebastian.miranda@arcaoexdi.com)"
    http_timeout_seconds: float = 30.0
    # Pausa por defecto entre requests de un mismo conector (rate limiting suave).
    http_request_pause_seconds: float = 1.5

    # --- Logging ---
    log_level: str = "INFO"

    # --- IA (capa opcional, degradable) ---------------------------------
    # Interruptor maestro. Si es False, los endpoints /ai/* NO tocan la red y
    # responden siempre con el fallback controlado (ia_disponible=false).
    ai_enabled: bool = False
    # Orden de proveedores a intentar (lista por comas). Ollama local primero,
    # OpenRouter como respaldo. Se expone ya parseado en `ai_providers`.
    ai_provider_order: str = "ollama,openrouter"
    # Timeout corto por request a cada proveedor (segundos). Degrada rápido.
    ai_request_timeout_seconds: float = 20.0
    # Límite de caracteres de la `pregunta` del usuario (acota el prompt).
    ai_max_pregunta_len: int = 500

    # --- Ollama (local, dentro de la red de compose) ---
    ollama_base_url: str = "http://ollama:11434"
    # Modelo liviano que corre en CPU normal. Cambiable por env.
    ollama_model: str = "llama3.2:3b"

    # --- OpenRouter (respaldo remoto, API compatible con OpenAI) ---
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # SIN default de modelo: el catálogo `:free` rota. El usuario debe fijar un
    # modelo vigente de https://openrouter.ai/models?max_price=0 en el .env.
    openrouter_model: str = ""

    @property
    def keywords(self) -> list[str]:
        """`scrape_keywords` parseado a lista, sin vacíos ni espacios sobrantes."""
        return [k.strip() for k in self.scrape_keywords.split(",") if k.strip()]

    @property
    def ai_providers(self) -> list[str]:
        """`ai_provider_order` parseado a lista de proveedores en minúsculas."""
        return [p.strip().lower() for p in self.ai_provider_order.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    """Devuelve la instancia única de configuración (cacheada)."""
    return Settings()


# Instancia compartida para importación directa: `from app.config import settings`.
settings = get_settings()
