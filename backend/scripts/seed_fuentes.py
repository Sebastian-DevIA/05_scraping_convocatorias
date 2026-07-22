"""Siembra idempotente de las 5 fuentes del MVP.

REGLA DURA: este script SOLO inserta/actualiza filas en `fuentes`.
JAMÁS inserta convocatorias (esos datos vienen únicamente del scraping real).

Idempotente: upsert por `codigo`. En cada corrida refresca nombre, url_base,
tipo y config (incl. keywords desde env). `activa` solo se fija al insertar,
para no pisar un toggle manual del operador.

Ejecución: `python scripts/seed_fuentes.py` (lo llama entrypoint.sh).
"""

from app.config import settings
from app.database import SessionLocal
from app.models import Fuente

# url_base reales verificadas en el plan (21-jul-2026).
FUENTES: list[dict] = [
    {
        "codigo": "secop",
        "nombre": "SECOP II (Colombia Compra Eficiente)",
        # Dataset Socrata p6dx-8zbt en datos.gov.co (API JSON con SoQL).
        "url_base": "https://www.datos.gov.co/resource/p6dx-8zbt.json",
        "tipo": "api",
        "activa": True,
        "max_paginas": 2,
        "rate_limit_seconds": 1.0,
    },
    {
        "codigo": "pnud",
        "nombre": "PNUD - Procurement Notices",
        "url_base": "https://procurement-notices.undp.org",
        "tipo": "html",
        "activa": True,
        "max_paginas": 10,
        "rate_limit_seconds": 1.5,
    },
    {
        "codigo": "minciencias",
        "nombre": "MinCiencias - Convocatorias",
        "url_base": "https://minciencias.gov.co/convocatorias/todas",
        "tipo": "html",
        "activa": True,
        "max_paginas": 10,
        "rate_limit_seconds": 1.5,
    },
    {
        "codigo": "mintic",
        "nombre": "MinTIC - Convocatorias",
        "url_base": "https://www.mintic.gov.co/portal/inicio/Sala-de-prensa/Convocatorias/",
        "tipo": "html",
        "activa": True,
        "max_paginas": 10,
        "rate_limit_seconds": 1.5,
    },
    {
        "codigo": "ungm",
        "nombre": "UNGM (ONU) - United Nations Global Marketplace",
        "url_base": "https://www.ungm.org/Public/Notice",
        # Stub en MVP: la carga es por JS. activa=False.
        "tipo": "js",
        "activa": False,
        "max_paginas": 5,
        "rate_limit_seconds": 2.0,
    },
]


def _config(data: dict) -> dict:
    """Config JSONB de la fuente. keywords vienen del env (editables sin código)."""
    return {
        "keywords": settings.keywords,
        "max_paginas": data["max_paginas"],
        "rate_limit_seconds": data["rate_limit_seconds"],
    }


def seed() -> None:
    db = SessionLocal()
    try:
        for data in FUENTES:
            fuente = db.query(Fuente).filter_by(codigo=data["codigo"]).one_or_none()
            if fuente is None:
                fuente = Fuente(
                    codigo=data["codigo"],
                    nombre=data["nombre"],
                    url_base=data["url_base"],
                    tipo=data["tipo"],
                    activa=data["activa"],
                    config=_config(data),
                )
                db.add(fuente)
                print(f"[seed] + fuente creada: {data['codigo']}")
            else:
                # Refresca metadatos y config; preserva `activa` (toggle del operador).
                fuente.nombre = data["nombre"]
                fuente.url_base = data["url_base"]
                fuente.tipo = data["tipo"]
                fuente.config = _config(data)
                print(f"[seed] ~ fuente actualizada: {data['codigo']}")
        db.commit()
        print(f"[seed] OK: {len(FUENTES)} fuentes sembradas.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
