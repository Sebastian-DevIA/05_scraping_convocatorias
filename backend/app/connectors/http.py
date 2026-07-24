"""Cliente HTTP compartido por los conectores.

Características (comunes a todas las fuentes, para no duplicar en cada conector):
  - timeout 30s (configurable).
  - reintentos con tenacity: 3 intentos, backoff exponencial + jitter, solo ante
    429 / 5xx / errores de red.
  - User-Agent identificable con contacto (desde config).
  - pausa entre requests (rate limiting suave, default 1.5s, override por fuente).
  - header X-App-Token (Socrata/SECOP) si SECOP_APP_TOKEN está definido.

Los errores se traducen a las excepciones tipadas de `base.py`, para que los
conectores nunca vean excepciones de httpx.

`post()` admite `json=` (cuerpo JSON), `data=` (form urlencoded) y `files=`
(multipart), porque no todas las fuentes aceptan JSON.
"""

import time

import httpx
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.config import settings
from app.connectors.base import (
    ConnectorError,
    RateLimitError,
    SourceUnavailableError,
)

# Excepciones que disparan reintento (transitorias).
_RETRYABLE = (RateLimitError, SourceUnavailableError)


class HttpClient:
    """Wrapper fino sobre httpx.Client con reintentos y rate limiting."""

    def __init__(
        self,
        *,
        pause_seconds: float | None = None,
        timeout: float | None = None,
        max_attempts: int = 3,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self._pause = (
            pause_seconds
            if pause_seconds is not None
            else settings.http_request_pause_seconds
        )
        self._max_attempts = max_attempts

        headers = {"User-Agent": settings.http_user_agent}
        # Token Socrata: se envía si existe (fuentes que no lo usan lo ignoran).
        if settings.secop_app_token:
            headers["X-App-Token"] = settings.secop_app_token
        if extra_headers:
            headers.update(extra_headers)

        self._client = httpx.Client(
            timeout=timeout if timeout is not None else settings.http_timeout_seconds,
            headers=headers,
            follow_redirects=True,
        )

    # --- API pública -------------------------------------------------------
    def get(
        self,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        """GET con reintentos. Devuelve la respuesta (2xx/3xx) o lanza ConnectorError."""
        return self._request("GET", url, params=params, headers=headers)

    def post(
        self,
        url: str,
        *,
        json: object | None = None,
        data: dict | None = None,
        files: dict | None = None,
        params: dict | None = None,
        headers: dict | None = None,
    ) -> httpx.Response:
        """POST con reintentos (para fuentes cuya API exige POST, ej. Grants.gov).

        `json` para cuerpos JSON; `data` para `application/x-www-form-urlencoded`
        y `files` para `multipart/form-data` (hay fuentes que solo aceptan
        formulario y rechazan JSON, ej. SICON del Distrito de Bogotá).

        Mismo comportamiento que `get`: pausa/rate-limit, reintentos ante 429/5xx/red,
        y traducción a excepciones tipadas de `base.py`.
        """
        return self._request(
            "POST", url, params=params, headers=headers, json=json, data=data, files=files
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # --- Interno -----------------------------------------------------------
    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
        json: object | None = None,
        data: dict | None = None,
        files: dict | None = None,
    ) -> httpx.Response:
        retryer = Retrying(
            stop=stop_after_attempt(self._max_attempts),
            wait=wait_exponential_jitter(initial=1.0, max=30.0),
            retry=retry_if_exception_type(_RETRYABLE),
            reraise=True,
        )
        return retryer(self._do_request, method, url, params, headers, json, data, files)

    def _do_request(
        self,
        method: str,
        url: str,
        params: dict | None,
        headers: dict | None,
        json: object | None = None,
        data: dict | None = None,
        files: dict | None = None,
    ) -> httpx.Response:
        # Pausa ANTES de cada intento (incluye reintentos) -> throttling.
        if self._pause > 0:
            time.sleep(self._pause)

        try:
            response = self._client.request(
                method, url, params=params, headers=headers, json=json, data=data, files=files
            )
        except httpx.TimeoutException as exc:  # transitorio -> reintento
            raise SourceUnavailableError(f"timeout en {url}: {exc}") from exc
        except httpx.TransportError as exc:  # red/DNS/conexión -> reintento
            raise SourceUnavailableError(f"error de red en {url}: {exc}") from exc

        status = response.status_code
        if status == 429:
            raise RateLimitError(f"429 Too Many Requests en {url}")
        if status >= 500:
            raise SourceUnavailableError(f"HTTP {status} en {url}")
        if status >= 400:
            # 4xx (salvo 429): error del cliente, no se reintenta.
            raise ConnectorError(f"HTTP {status} en {url}")
        return response


def get_http_client(
    *,
    pause_seconds: float | None = None,
    timeout: float | None = None,
    extra_headers: dict[str, str] | None = None,
) -> HttpClient:
    """Fábrica de conveniencia para obtener un HttpClient con la config por defecto."""
    return HttpClient(
        pause_seconds=pause_seconds,
        timeout=timeout,
        extra_headers=extra_headers,
    )
