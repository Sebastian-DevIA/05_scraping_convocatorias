"""Cliente de IA con failover entre proveedores (Ollama local -> OpenRouter).

Expone `complete(system, prompt) -> str`. Intenta cada proveedor de
`settings.ai_providers` en orden; el primero que responde gana. Si todos
fallan (o la IA está deshabilitada), lanza `AIUnavailableError` para que el
servicio degrade con gracia.

Seguridad: la `OPENROUTER_API_KEY` se envía SOLO en el header Authorization
hacia OpenRouter; nunca se loguea ni se incluye en mensajes de error.
"""

import logging

import httpx

from app.ai.errors import AIProviderError, AIUnavailableError
from app.config import Settings, settings as default_settings

logger = logging.getLogger(__name__)


def _complete_ollama(system: str, prompt: str, cfg: Settings) -> str:
    """Llama a Ollama vía /api/chat (stream=false)."""
    url = cfg.ollama_base_url.rstrip("/") + "/api/chat"
    payload = {
        "model": cfg.ollama_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        # Baja temperatura: queremos extracción/resumen fieles, no creatividad.
        "options": {"temperature": 0.1},
    }
    try:
        resp = httpx.post(url, json=payload, timeout=cfg.ai_request_timeout_seconds)
    except httpx.HTTPError as exc:
        raise AIProviderError("ollama", f"error de red: {type(exc).__name__}") from exc
    if resp.status_code >= 400:
        raise AIProviderError("ollama", f"HTTP {resp.status_code}")
    try:
        data = resp.json()
        content = data["message"]["content"]
    except (ValueError, KeyError, TypeError) as exc:
        raise AIProviderError("ollama", "respuesta ilegible") from exc
    if not isinstance(content, str) or not content.strip():
        raise AIProviderError("ollama", "respuesta vacía")
    return content.strip()


def _complete_openrouter(system: str, prompt: str, cfg: Settings) -> str:
    """Llama a OpenRouter vía API compatible con OpenAI (/chat/completions)."""
    if not cfg.openrouter_api_key:
        raise AIProviderError("openrouter", "sin OPENROUTER_API_KEY configurada")
    if not cfg.openrouter_model:
        raise AIProviderError("openrouter", "sin OPENROUTER_MODEL configurado")

    url = cfg.openrouter_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {cfg.openrouter_api_key}",
        "Content-Type": "application/json",
        # Recomendado por OpenRouter para identificar la app (no es un secreto).
        "HTTP-Referer": "https://github.com/Arca-Oexdi/scraping_convocatorias",
        "X-Title": "Convocatorias AI",
    }
    payload = {
        "model": cfg.openrouter_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }
    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=cfg.ai_request_timeout_seconds)
    except httpx.HTTPError as exc:
        raise AIProviderError("openrouter", f"error de red: {type(exc).__name__}") from exc
    if resp.status_code >= 400:
        # No incluimos el cuerpo para no arriesgar filtrar nada sensible en logs.
        raise AIProviderError("openrouter", f"HTTP {resp.status_code}")
    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise AIProviderError("openrouter", "respuesta ilegible") from exc
    if not isinstance(content, str) or not content.strip():
        raise AIProviderError("openrouter", "respuesta vacía")
    return content.strip()


_PROVIDERS = {
    "ollama": _complete_ollama,
    "openrouter": _complete_openrouter,
}


def complete(system: str, prompt: str, cfg: Settings | None = None) -> str:
    """Devuelve la respuesta del primer proveedor disponible.

    Lanza `AIUnavailableError` si la IA está deshabilitada o si todos los
    proveedores configurados fallan.
    """
    cfg = cfg or default_settings
    if not cfg.ai_enabled:
        raise AIUnavailableError("IA deshabilitada (AI_ENABLED=false)")

    errores: list[str] = []
    for nombre in cfg.ai_providers:
        fn = _PROVIDERS.get(nombre)
        if fn is None:
            logger.warning("Proveedor de IA desconocido en AI_PROVIDER_ORDER: %s", nombre)
            continue
        try:
            return fn(system, prompt, cfg)
        except AIProviderError as exc:
            # Mensaje sin secretos (ver errores.py). Seguimos con el siguiente.
            logger.warning("Proveedor de IA falló, probando siguiente: %s", exc)
            errores.append(str(exc))
            continue

    raise AIUnavailableError("todos los proveedores de IA fallaron: " + "; ".join(errores))
