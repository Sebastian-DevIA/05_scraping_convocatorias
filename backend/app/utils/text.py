"""Utilidades pequeñas de texto para normalización determinista."""

from __future__ import annotations

import re
import unicodedata

_WS = re.compile(r"\s+")


def clean_text(value: object) -> str | None:
    """Devuelve texto limpio no vacío, o None si el dato está ausente."""
    if value is None:
        return None
    text = _WS.sub(" ", str(value)).strip()
    return text or None


def fold_text(value: object) -> str:
    """Minúsculas sin acentos para comparaciones de keywords/estados."""
    text = clean_text(value) or ""
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))
