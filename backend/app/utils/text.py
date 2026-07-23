"""Utilidades pequeñas de texto para normalización determinista."""

from __future__ import annotations

import re
import unicodedata

from bs4 import BeautifulSoup

_WS = re.compile(r"\s+")

# Etiquetas de bloque que deben introducir un salto de línea al aplanar HTML.
_BLOQUES = ("div", "p", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "li", "ul", "ol")


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


def html_to_text(value: object) -> str | None:
    """Convierte HTML (o texto plano) a texto legible multilínea.

    Algunas fuentes entregan la descripción como fragmento HTML (ej. el
    `notice_text` del Banco Mundial: `<b>Project:</b>...<br/>...`). Guardar ese
    marcado crudo hace que la ficha se vea como etiquetas escapadas ilegibles.
    Aquí se APLANA a texto: los `<br>` y las etiquetas de bloque se vuelven
    saltos de línea, el resto de etiquetas se elimina y cada línea se limpia de
    espacios redundantes. No inventa datos: solo quita el marcado de la fuente.

    Devuelve None si tras aplanar no queda contenido.
    """
    if value is None:
        return None
    raw = str(value)
    if not raw.strip():
        return None

    soup = BeautifulSoup(raw, "lxml")
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for bloque in soup.find_all(_BLOQUES):
        bloque.append("\n")

    # Separador " ": mantiene "<b>Etiqueta:</b>valor" en la misma línea.
    texto = soup.get_text(" ")
    lineas = [" ".join(linea.split()) for linea in texto.splitlines()]
    limpio = "\n".join(linea for linea in lineas if linea)
    return limpio or None
