"""Tests del flag derivado `apto_fundaciones_nuevas` y de `map_estado`.

Sin red ni BD: se ejercita la heurística pura del normalizador sobre objetos
`RawConvocatoria` construidos con TEXTOS realistas (los mismos patrones que
aparecen en convocatorias reales). No se inventan datos de fuentes: se prueba la
LÓGICA de derivación, que es determinista y trazable.
"""

from __future__ import annotations

from app.pipeline.normalizer import (
    es_apto_fundaciones_nuevas,
    map_estado,
    normalizar,
)
from app.schemas.raw import RawConvocatoria


def _raw(**kw) -> RawConvocatoria:
    base = dict(
        id_externo="X1",
        titulo="Convocatoria",
        descripcion=None,
        entidad=None,
        tipo="subvencion",
        estado_fuente="open",
        modalidad=None,
        monto=None,
        moneda=None,
        departamento=None,
        ciudad=None,
        pais="Colombia",
        fecha_publicacion=None,
        fecha_apertura=None,
        fecha_cierre=None,
        requisitos=None,
        url_original="https://example.org/x1",
        raw={},
    )
    base.update(kw)
    return RawConvocatoria(**base)


# --- apto: señales positivas -----------------------------------------------
def test_apto_true_con_senal_positiva_en_descripcion() -> None:
    raw = _raw(descripcion="Fondo de capital semilla para emprendimiento social.")
    assert es_apto_fundaciones_nuevas(raw) is True


def test_apto_true_con_acentos_y_mayusculas() -> None:
    # 'Organizaciones Recién Creadas' -> fold_text normaliza acentos/caso.
    raw = _raw(titulo="Apoyo a Organizaciones Recién Creadas")
    assert es_apto_fundaciones_nuevas(raw) is True


def test_apto_true_ingles_small_grant() -> None:
    raw = _raw(descripcion="Seed grant for first-time applicant organizations.")
    assert es_apto_fundaciones_nuevas(raw) is True


# --- apto: señal descalificante gana ---------------------------------------
def test_apto_false_si_exige_experiencia_pese_a_senal_positiva() -> None:
    raw = _raw(
        descripcion="Emprendimiento social",
        requisitos="Se exige experiencia mínima de 5 años como organización.",
    )
    assert es_apto_fundaciones_nuevas(raw) is False


def test_apto_false_sin_evidencia() -> None:
    raw = _raw(
        titulo="Licitación de obra pública",
        descripcion="Construcción de puente vehicular en la vía nacional.",
    )
    assert es_apto_fundaciones_nuevas(raw) is False


def test_apto_false_texto_vacio() -> None:
    raw = _raw(titulo="x", descripcion=None, requisitos=None, modalidad=None)
    # 'x' no contiene señales -> False (no inventa aptitud).
    assert es_apto_fundaciones_nuevas(raw) is False


# --- integración con normalizar() ------------------------------------------
def test_normalizar_incluye_apto_y_entra_en_hash_contenido() -> None:
    apto = _raw(descripcion="Capital semilla para nuevas organizaciones.")
    no_apto = _raw(descripcion="Adquisición de vehículos para la entidad.")

    d_apto = normalizar(apto, "grantsgov", keywords=[])
    d_no = normalizar(no_apto, "grantsgov", keywords=[])

    assert d_apto["apto_fundaciones_nuevas"] is True
    assert d_no["apto_fundaciones_nuevas"] is False
    # El flag participa en hash_contenido: dos convocatorias idénticas salvo el
    # flag producen hashes distintos (un cambio de aptitud se detecta en upsert).
    assert d_apto["hash_contenido"] != d_no["hash_contenido"]


# --- map_estado: vocabulario de las fuentes nuevas -------------------------
def test_map_estado_grantsgov_posted_forecast() -> None:
    assert map_estado("posted") == "abierta"
    assert map_estado("forecasted") == "abierta"
    assert map_estado("archived") == "cerrada"


def test_map_estado_worldbank_published() -> None:
    assert map_estado("Published") == "abierta"


def test_map_estado_desconocido() -> None:
    assert map_estado("algo raro") == "desconocido"
