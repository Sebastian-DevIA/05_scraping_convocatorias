"""Conector MinTIC — tarjetas públicas de convocatorias."""

from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.connectors.base import BaseConnector, ParseError
from app.connectors.http import get_http_client
from app.schemas.raw import RawConvocatoria
from app.utils.dates import parse_spanish_date

URL = "https://www.mintic.gov.co/portal/inicio/Sala-de-prensa/Convocatorias/"


def _txt(node) -> str | None:
    if node is None:
        return None
    text = " ".join(node.get_text(" ", strip=True).split())
    return text or None


def _id_from_href(href: str) -> str:
    match = re.search(r"/(\d+):", href)
    if match:
        return match.group(1)
    return href.rstrip("/").split("/")[-1]


class MinTicConnector(BaseConnector):
    codigo = "mintic"
    nombre = "MinTIC"

    def fetch(self, config: dict) -> list[RawConvocatoria]:
        with get_http_client(pause_seconds=(config or {}).get("rate_limit_seconds")) as client:
            response = client.get(URL)
        soup = BeautifulSoup(response.text, "lxml")
        cards = soup.select(".convocatorias_container .card")
        if not cards:
            raise ParseError("MinTIC: no se encontraron tarjetas de convocatorias")

        items: list[RawConvocatoria] = []
        for card in cards:
            link = card.select_one(".titulo a")
            title = _txt(link)
            href = link.get("href") if link else None
            if not title or not href:
                continue
            fecha_text = _txt(card.select_one(".fecha"))
            tags = [_txt(tag) for tag in card.select(".tag-convocatoria span span")]
            tags = [tag for tag in tags if tag]
            estado = " ".join(tags) or "desconocido"
            url = urljoin("https://www.mintic.gov.co", href)
            items.append(
                RawConvocatoria(
                    id_externo=_id_from_href(href),
                    titulo=title,
                    descripcion=None,
                    entidad="Ministerio de Tecnologías de la Información y las Comunicaciones",
                    tipo="fondo",
                    estado_fuente=estado,
                    modalidad="Convocatoria",
                    monto=None,
                    moneda=None,
                    departamento=None,
                    ciudad=None,
                    pais="Colombia",
                    fecha_publicacion=parse_spanish_date(fecha_text),
                    fecha_apertura=None,
                    fecha_cierre=None,
                    requisitos=None,
                    url_original=url,
                    raw={"titulo": title, "fecha": fecha_text, "tags": tags, "href": href},
                )
            )
        return items
