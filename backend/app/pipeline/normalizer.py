"""Normalización de `RawConvocatoria` a campos persistibles."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from app.constants import (
    PAIS_DEFAULT,
    SEÑALES_EXPERIENCIA_REQUERIDA,
    SEÑALES_FUNDACIONES_NUEVAS,
)
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
    if any(x in estado for x in ("adjudic", "seleccionado", "awarded", "award")):
        return "adjudicada"
    if any(
        x in estado
        for x in ("cerrad", "closed", "cancelad", "terminad", "archiv", "expired")
    ):
        return "cerrada"
    if any(
        x in estado
        for x in (
            "abiert",
            "publicad",
            "convocad",
            "open",
            "published",
            "posted",
            "forecast",
            "vigente",
            "active",
        )
    ):
        return "abierta"
    return "desconocido"


def map_ambito(ambito_fuente: str | None) -> str:
    """Mapea el `ambito_fuente` crudo al ámbito canónico.

    Trabaja sobre texto libre de cada fuente (ej. el `ordenentidad` de SECOP II,
    cuyos valores reales son 'Territorial', 'Nacional', 'Corporación Autónoma' y
    'No Definido'). Las Corporaciones Autónomas Regionales son autoridades de
    alcance regional, por eso caen en `territorial`.

    Sin señal reconocible -> 'desconocido' (nunca se adivina).
    """
    if not ambito_fuente:
        return "desconocido"
    texto = fold_text(ambito_fuente)
    if any(
        x in texto
        for x in ("territorial", "municipal", "departamental", "distrital", "corporacion autonoma", "regional")
    ):
        return "territorial"
    if any(x in texto for x in ("internacional", "international", "multilateral")):
        return "internacional"
    if any(x in texto for x in ("nacional", "national", "federal")):
        return "nacional"
    return "desconocido"


def es_apto_fundaciones_nuevas(raw: RawConvocatoria) -> bool:
    """Flag DERIVADO: ¿la convocatoria parece accesible a fundaciones nuevas?

    Heurística determinista y trazable sobre el CONTENIDO REAL (título +
    descripción + requisitos + modalidad). True solo si hay ≥1 señal positiva y
    NINGUNA señal descalificante (exigencia de trayectoria/experiencia). Nunca
    inventa datos: si no hay evidencia, devuelve False (no afirma "no apto").
    """
    texto = fold_text(
        " ".join(
            filter(None, [raw.titulo, raw.descripcion, raw.requisitos, raw.modalidad])
        )
    )
    if not texto:
        return False
    if any(fold_text(s) in texto for s in SEÑALES_EXPERIENCIA_REQUERIDA):
        return False
    return any(fold_text(s) in texto for s in SEÑALES_FUNDACIONES_NUEVAS)


def keywords_match(raw: RawConvocatoria, keywords: list[str]) -> list[str]:
    texto = fold_text(" ".join(filter(None, [raw.titulo, raw.descripcion, raw.entidad])))
    matches: list[str] = []
    for keyword in keywords:
        if fold_text(keyword) and fold_text(keyword) in texto:
            matches.append(keyword)
    return matches


def normalizar(
    raw: RawConvocatoria,
    codigo_fuente: str,
    keywords: list[str],
    ambito_default: str | None = None,
) -> dict[str, Any]:
    """Convierte una convocatoria cruda en dict listo para upsert.

    `ambito_default` es el ámbito declarado en la config de la fuente (ej.
    'Internacional' para PNUD o Banco Mundial); solo se usa como respaldo cuando
    el registro no trae `ambito_fuente` propio.
    """
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
        "ambito": map_ambito(raw.ambito_fuente or ambito_default),
        "fecha_publicacion": _utc(raw.fecha_publicacion),
        "fecha_apertura": _utc(raw.fecha_apertura),
        "fecha_cierre": _utc(raw.fecha_cierre),
        "requisitos": clean_text(raw.requisitos),
        "url_original": raw.url_original,
        "keywords_match": keywords_match(raw, keywords),
        "apto_fundaciones_nuevas": es_apto_fundaciones_nuevas(raw),
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
            "ambito",
            "fecha_publicacion",
            "fecha_apertura",
            "fecha_cierre",
            "requisitos",
            "url_original",
            "keywords_match",
            "apto_fundaciones_nuevas",
        )
    }
    data["hash_dedupe"] = hash_dedupe(codigo_fuente, raw.id_externo)
    data["hash_contenido"] = hash_contenido(contenido)
    return data
