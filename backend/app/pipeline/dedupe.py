"""Hashes de deduplicación y contenido."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any


def hash_dedupe(codigo_fuente: str, id_externo: str) -> str:
    return hashlib.sha256(f"{codigo_fuente}:{id_externo}".encode("utf-8")).hexdigest()


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def hash_contenido(data: dict[str, Any]) -> str:
    payload = json.dumps(
        data,
        default=_json_default,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
