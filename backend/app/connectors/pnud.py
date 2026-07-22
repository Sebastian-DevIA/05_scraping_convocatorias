"""Conector PNUD — Procurement Notices HTML.

La página oficial incluye los avisos como filas `<a class="vacanciesTable__row">`
con celdas etiquetadas. Se parsea solo esa tabla pública; campos ausentes quedan
en None y `url_original` apunta al detalle oficial.
"""

from __future__ import annotations

from datetime import datetime, timezone

from bs4 import BeautifulSoup

from app.connectors.base import BaseConnector, ParseError
from app.connectors.http import get_http_client
from app.schemas.raw import RawConvocatoria

URL = "https://procurement-notices.undp.org/"


def _txt(node) -> str | None:
    if node is None:
        return None
    value = " ".join(node.get_text(" ", strip=True).split())
    return value or None


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    clean = value.split("(")[0].strip()
    for fmt in ("%d-%b-%y %I:%M %p", "%d-%b-%y"):
        try:
            return datetime.strptime(clean, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _tipo(procurement_process: str | None) -> str:
    value = (procurement_process or "").casefold()
    if "rfp" in value or "request for proposal" in value:
        return "rfp"
    if "eoi" in value or "expression of interest" in value:
        return "eoi"
    if "grant" in value or "proposal" in value:
        return "subvencion"
    return "otro"


class PnudConnector(BaseConnector):
    codigo = "pnud"
    nombre = "PNUD"

    def _row_data(self, row) -> dict[str, str | None]:
        data: dict[str, str | None] = {}
        for cell in row.select(".vacanciesTable__cell"):
            label = _txt(cell.select_one(".vacanciesTable__cell__label"))
            span = _txt(cell.select_one("span"))
            if label:
                data[label.casefold()] = span
        return data

    def fetch(self, config: dict) -> list[RawConvocatoria]:
        pause = (config or {}).get("rate_limit_seconds")
        with get_http_client(pause_seconds=pause) as client:
            response = client.get(URL)
        soup = BeautifulSoup(response.text, "lxml")
        rows = soup.select("a.vacanciesTable__row")
        if not rows:
            raise ParseError("PNUD: no se encontraron filas de convocatorias")

        items: list[RawConvocatoria] = []
        for row in rows:
            href = row.get("href")
            data = self._row_data(row)
            ref = data.get("ref no")
            title = data.get("title")
            if not href or not ref or not title:
                continue
            url = href if str(href).startswith("http") else URL + str(href).lstrip("/")
            office_country = data.get("undp office/country")
            process = data.get("procurement process") or data.get("process")
            items.append(
                RawConvocatoria(
                    id_externo=ref,
                    titulo=title,
                    descripcion=None,
                    entidad=office_country,
                    tipo=_tipo(process),
                    estado_fuente="open",
                    modalidad=process,
                    monto=None,
                    moneda=None,
                    departamento=None,
                    ciudad=None,
                    pais=(office_country or "").split("/")[-1].strip() or "Global",
                    fecha_publicacion=_parse_date(data.get("posted")),
                    fecha_apertura=None,
                    fecha_cierre=_parse_date(data.get("deadline")),
                    requisitos=None,
                    url_original=url,
                    raw=data | {"href": href},
                )
            )
        return items
