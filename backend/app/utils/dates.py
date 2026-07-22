"""Parseo tolerante de fechas públicas en español/inglés."""

from __future__ import annotations

from datetime import datetime, timezone

MONTHS_ES = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def parse_spanish_date(value: str | None) -> datetime | None:
    """Parsea fechas como `02 de julio de 2025` o `2026-07-21` a UTC."""
    if not value:
        return None
    text = " ".join(value.replace(",", " ").split()).strip().casefold()
    if not text:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    parts = text.split()
    if len(parts) >= 5 and parts[1] == "de" and parts[3] == "de":
        try:
            day = int(parts[0])
            month = MONTHS_ES[parts[2]]
            year = int(parts[4])
            return datetime(year, month, day, tzinfo=timezone.utc)
        except (KeyError, ValueError):
            return None
    if len(parts) >= 3 and parts[0] in MONTHS_ES:
        try:
            month = MONTHS_ES[parts[0]]
            day = int(parts[1])
            year = int(parts[2])
            return datetime(year, month, day, tzinfo=timezone.utc)
        except ValueError:
            return None
    return None
