"""Tests de la capa de IA. Mockean el cliente de IA: NO dependen de que Ollama
u OpenRouter estén disponibles (importante para CI).

Cubren: extracción de filtros válida, JSON inválido -> fallback de texto plano,
enum inválido -> fallback, proveedor caído -> ia_disponible=false sin romper el
endpoint, 404 de resumen, degradación de resumen/soporte, límite de longitud
(422) y rate-limit (429).
"""

from types import SimpleNamespace

import pytest

from app.ai.errors import AIUnavailableError
from app.api.routers import ai as ai_router
from app.api.services import ai as ai_service


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    """Aísla el rate-limit global entre tests."""
    ai_router._hits.clear()
    yield
    ai_router._hits.clear()


def _patch_complete(monkeypatch, fn):
    """Sustituye app.ai.client.complete (lo usan service.buscar/resumir/soporte)."""
    monkeypatch.setattr("app.ai.client.complete", fn)


# --------------------------------------------------------------- /ai/buscar
def test_buscar_extraccion_valida(client, monkeypatch):
    _patch_complete(
        monkeypatch,
        lambda system, prompt: '{"q": "software", "fuente": "secop", "estado": "abierta"}',
    )
    r = client.post("/api/v1/ai/buscar", json={"pregunta": "convocatorias de software abiertas en secop"})
    assert r.status_code == 200
    body = r.json()
    assert body["ia_disponible"] is True
    assert body["fallback"] is False
    assert body["filtros_interpretados"] == {"q": "software", "fuente": "secop", "estado": "abierta"}
    assert "items" in body["resultado"] and "total" in body["resultado"]


def test_buscar_json_invalido_cae_a_texto_plano(client, monkeypatch):
    _patch_complete(monkeypatch, lambda system, prompt: "esto no es json")
    r = client.post("/api/v1/ai/buscar", json={"pregunta": "algo de energia"})
    assert r.status_code == 200
    body = r.json()
    # El proveedor respondió (ia_disponible=True) pero su salida no valida:
    assert body["ia_disponible"] is True
    assert body["fallback"] is True
    assert body["filtros_interpretados"] == {"q": "algo de energia"}


def test_buscar_enum_invalido_cae_a_texto_plano(client, monkeypatch):
    _patch_complete(monkeypatch, lambda system, prompt: '{"estado": "no_existe"}')
    r = client.post("/api/v1/ai/buscar", json={"pregunta": "cosas raras"})
    assert r.status_code == 200
    body = r.json()
    assert body["fallback"] is True
    assert body["filtros_interpretados"] == {"q": "cosas raras"}


def test_buscar_proveedor_caido_no_rompe(client, monkeypatch):
    def _down(system, prompt):
        raise AIUnavailableError("todos los proveedores fallaron")

    _patch_complete(monkeypatch, _down)
    r = client.post("/api/v1/ai/buscar", json={"pregunta": "inclusion digital"})
    assert r.status_code == 200
    body = r.json()
    assert body["ia_disponible"] is False
    assert body["fallback"] is True
    assert body["filtros_interpretados"] == {"q": "inclusion digital"}


def test_buscar_pregunta_muy_larga_422(client):
    r = client.post("/api/v1/ai/buscar", json={"pregunta": "x" * 501})
    assert r.status_code == 422


def test_buscar_pregunta_vacia_422(client):
    r = client.post("/api/v1/ai/buscar", json={"pregunta": ""})
    assert r.status_code == 422


# ------------------------------------------ /ai/convocatorias/{id}/resumen
def test_resumen_404_si_no_existe(client, monkeypatch):
    monkeypatch.setattr(
        "app.api.services.ai.conv_service.obtener_convocatoria",
        lambda db, cid, include_raw: None,
    )
    r = client.post("/api/v1/ai/convocatorias/999999999/resumen")
    assert r.status_code == 404


def test_resumen_ok(client, monkeypatch):
    fake = SimpleNamespace(
        titulo="Fondo de innovación",
        entidad="MinCiencias",
        descripcion="Apoyo a proyectos de base tecnológica.",
        requisitos="Ser persona jurídica colombiana.",
    )
    monkeypatch.setattr(
        "app.api.services.ai.conv_service.obtener_convocatoria",
        lambda db, cid, include_raw: fake,
    )
    _patch_complete(monkeypatch, lambda system, prompt: "Resumen: fondo para innovación tecnológica.")
    r = client.post("/api/v1/ai/convocatorias/1/resumen")
    assert r.status_code == 200
    body = r.json()
    assert body["ia_disponible"] is True
    assert "innovación" in body["resumen"]


def test_resumen_proveedor_caido(client, monkeypatch):
    fake = SimpleNamespace(titulo="T", entidad=None, descripcion="d", requisitos=None)
    monkeypatch.setattr(
        "app.api.services.ai.conv_service.obtener_convocatoria",
        lambda db, cid, include_raw: fake,
    )

    def _down(system, prompt):
        raise AIUnavailableError("caido")

    _patch_complete(monkeypatch, _down)
    r = client.post("/api/v1/ai/convocatorias/1/resumen")
    assert r.status_code == 200
    body = r.json()
    assert body["ia_disponible"] is False
    assert body["resumen"] is None
    assert body["mensaje"]


# --------------------------------------------------------------- /ai/soporte
def test_soporte_ok(client, monkeypatch):
    _patch_complete(monkeypatch, lambda system, prompt: "Usa el botón 'Actualizar ahora'.")
    r = client.post("/api/v1/ai/soporte", json={"pregunta": "como disparo un scraping?"})
    assert r.status_code == 200
    body = r.json()
    assert body["ia_disponible"] is True
    assert "Actualizar" in body["respuesta"]


def test_soporte_proveedor_caido(client, monkeypatch):
    def _down(system, prompt):
        raise AIUnavailableError("caido")

    _patch_complete(monkeypatch, _down)
    r = client.post("/api/v1/ai/soporte", json={"pregunta": "hola"})
    assert r.status_code == 200
    body = r.json()
    assert body["ia_disponible"] is False
    assert body["respuesta"]


# --------------------------------------------------------------- rate limit
def test_rate_limit_429(client, monkeypatch):
    _patch_complete(monkeypatch, lambda system, prompt: "ok")
    limite = ai_router._RATE_MAX
    for _ in range(limite):
        assert client.post("/api/v1/ai/soporte", json={"pregunta": "hola"}).status_code == 200
    # La siguiente supera la ventana -> 429.
    assert client.post("/api/v1/ai/soporte", json={"pregunta": "hola"}).status_code == 429


# --------------------------------------------------- unit: parseo de JSON del modelo
def test_extraer_json_tolera_cercas_markdown():
    assert ai_service._extraer_json('```json\n{"q": "x"}\n```') == {"q": "x"}
    assert ai_service._extraer_json('Aquí tienes: {"q": "y"} listo') == {"q": "y"}


def test_extraer_json_falla_sin_json():
    with pytest.raises(ValueError):
        ai_service._extraer_json("sin llaves aquí")
