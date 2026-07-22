"""Normalización de `RawConvocatoria` a campos persistibles."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.constants import PAIS_DEFAULT
from app.pipeline.dedupe import hash_contenido, hash_dedupe
from app.schemas.raw import RawConvocatoria
from app.utils.text import clean_text, fold_text


def _utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def map_estado(estado_fuente: str) -> str:
    estado = fold_text(estado_fuente)
    if any(x in estado for x in ("adjudic", "seleccionado", "awarded")):
        return "adjudicada"
    if any(x in estado for x in ("cerrad", "closed", "cancelad", "terminad")):
        return "cerrada"
    if any(x in estado for x in ("abiert", "publicad", "convocad", "open", "published")):
        return "abierta"
    return "desconocido"


def keywords_match(raw: RawConvocatoria, keywords: list[str]) -> list[str]:
    texto = fold_text(" ".join(filter(None, [raw.titulo, raw.descripcion, raw.entidad])))
    matches: list[str] = []
    for keyword in keywords:
        if fold_text(keyword) and fold_text(keyword) in texto:
            matches.append(keyword)
    return matches


def normalizar(raw: RawConvocatoria, codigo_fuente: str, keywords: list[str]) -> dict[str, Any]:
    """Convierte una convocatoria cruda en dict listo para upsert."""
    data = {
        "id_externo": raw.id_externo,
        "titulo": raw.titulo,
        "descripcion": clean_text(raw.descripcion),
        "entidad": clean_text(raw.entidad),
        "tipo": raw.tipo,
        "modalidad": clean_text(raw.modalidad),
        "estado": map_estado(raw.estado_fuente),
        "monto": raw.monto if isinstance(raw.monto, Decimal) else raw.monto,
        "moneda": clean_text(raw.moneda),
        "departamento": clean_text(raw.departamento),
        "ciudad": clean_text(raw.ciudad),
        "pais": clean_text(raw.pais) or PAIS_DEFAULT,
        "fecha_publicacion": _utc(raw.fecha_publicacion),
        "fecha_apertura": _utc(raw.fecha_apertura),
        "fecha_cierre": _utc(raw.fecha_cierre),
        "requisitos": clean_text(raw.requisitos),
        "url_original": raw.url_original,
        "keywords_match": keywords_match(raw, keywords),
        "raw": raw.raw or {},
    }
    contenido = {
        key: data[key]
        for key in (
            "titulo",
            "descripcion",
            "entidad",
            "tipo",
            "modalidad",
            "estado",
            "monto",
            "moneda",
            "departamento",
            "ciudad",
            "pais",
            "fecha_publicacion",
            "fecha_apertura",
            "fecha_cierre",
            "requisitos",
            "url_original",
            "keywords_match",
        )
    }
    data["hash_dedupe"] = hash_dedupe(codigo_fuente, raw.id_externo)
    data["hash_contenido"] = hash_contenido(contenido)
    return data
