"""Tests de `html_to_text`: aplanado de HTML de fuente a texto legible.

El fragmento de entrada es HTML REAL del `notice_text` del Banco Mundial (aviso
de adjudicación), tal como lo entrega la API. No se inventan datos: se verifica
que el marcado se convierte en texto ordenado y multilínea, sin etiquetas.
"""

from __future__ import annotations

from app.utils.text import html_to_text

# Fragmento REAL de notice_text del Banco Mundial (recortado del aviso Somalia).
HTML_REAL = (
    "<div class='row col-sm-12'><h4>Contract Award</h4><p>"
    "<b>Project:</b>P172434-Somalia Education for Human Capital Development Project<br/>"
    "<b>Bid/Contract Reference No:</b>SO-MOES-532815-GO-RFQ-GEMS<br/>"
    "<b>Procurement Method:</b>RFQ-Request for Quotations<br/>"
    "<b>Scope of Contract:</b><span class='desc-word-wrap'>"
    "Supply and Delivery of IT and Communication Equipment</span><br/>"
    "</p></div>"
)


def test_aplana_html_real_a_texto_legible() -> None:
    texto = html_to_text(HTML_REAL)
    assert texto is not None
    # No quedan etiquetas HTML.
    assert "<" not in texto and ">" not in texto
    # El contenido real se conserva y queda ordenado por líneas.
    assert "Contract Award" in texto
    assert "Project: P172434-Somalia Education for Human Capital Development Project" in texto
    assert "Procurement Method: RFQ-Request for Quotations" in texto
    # Cada par etiqueta:valor va en su propia línea (los <br/> son saltos).
    lineas = texto.splitlines()
    assert any(l.startswith("Project:") for l in lineas)
    assert any(l.startswith("Scope of Contract:") for l in lineas)


def test_texto_plano_se_devuelve_igual() -> None:
    assert html_to_text("Convocatoria sin HTML") == "Convocatoria sin HTML"


def test_vacio_o_none_devuelve_none() -> None:
    assert html_to_text(None) is None
    assert html_to_text("") is None
    assert html_to_text("   ") is None
    assert html_to_text("<div>  </div>") is None
