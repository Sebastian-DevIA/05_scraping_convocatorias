"""Conector MinCiencias — tabla pública de convocatorias."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.connectors.base import BaseConnector, ParseError
from app.connectors.http import get_http_client
from app.schemas.raw import RawConvocatoria
from app.utils.dates import parse_spanish_date

URL = "https://minciencias.gov.co/convocatorias/todas"


def _txt(node) -> str | None:
    if node is None:
        return None
    text = " ".join(node.get_text(" ", strip=True).split())
    return text or None


def _money(value: str | None) -> Decimal | None:
    if not value:
        return None
    clean = value.replace("$", "").replace(".", "").replace(",", ".").strip()
    try:
        return Decimal(clean)
    except (InvalidOperation, ValueError):
        return None


class MinCienciasConnector(BaseConnector):
    codigo = "minciencias"
    nombre = "MinCiencias"

    def fetch(self, config: dict) -> list[RawConvocatoria]:
        with get_http_client(pause_seconds=(config or {}).get("rate_limit_seconds")) as client:
            response = client.get(URL)
        soup = BeautifulSoup(response.text, "lxml")
        rows = soup.select("tbody tr")
        if not rows:
            raise ParseError("MinCiencias: no se encontraron filas en la tabla")

        items: list[RawConvocatoria] = []
        for row in rows:
            numero = _txt(row.select_one(".views-field-field-numero"))
            link = row.select_one(".views-field-title a")
            title = _txt(link)
            if not numero or not link or not title:
                continue
            descripcion = _txt(row.select_one(".views-field-body"))
            monto_text = _txt(row.select_one(".views-field-field-cuantia"))
            fecha_apertura_text = _txt(row.select_one(".views-field-field-fecha-de-apertura"))
            url = urljoin(URL, link.get("href", ""))
            items.append(
                RawConvocatoria(
                    id_externo=numero,
                    titulo=title,
                    descripcion=descripcion,
                    entidad="Ministerio de Ciencia, Tecnología e Innovación",
                    tipo="fondo",
                    estado_fuente="publicada",
                    modalidad="Convocatoria",
                    monto=_money(monto_text),
                    moneda="COP" if monto_text else None,
                    departamento=None,
                    ciudad=None,
                    pais="Colombia",
                    fecha_publicacion=None,
                    fecha_apertura=parse_spanish_date(fecha_apertura_text),
                    fecha_cierre=None,
                    requisitos=None,
                    url_original=url,
                    raw={
                        "numero": numero,
                        "titulo": title,
                        "descripcion": descripcion,
                        "cuantia": monto_text,
                        "fecha_apertura": fecha_apertura_text,
                    },
                )
            )
        return items
