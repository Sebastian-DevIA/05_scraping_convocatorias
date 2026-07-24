"""Siembra idempotente de las fuentes del sistema.

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
        "ambito_default": "Internacional",
    },
    {
        "codigo": "minciencias",
        "nombre": "MinCiencias - Convocatorias",
        "url_base": "https://minciencias.gov.co/convocatorias/todas",
        "tipo": "html",
        "activa": True,
        "max_paginas": 10,
        "rate_limit_seconds": 1.5,
        "ambito_default": "Nacional",
    },
    {
        "codigo": "mintic",
        "nombre": "MinTIC - Convocatorias",
        "url_base": "https://www.mintic.gov.co/portal/inicio/Sala-de-prensa/Convocatorias/",
        "tipo": "html",
        "activa": True,
        "max_paginas": 10,
        "rate_limit_seconds": 1.5,
        "ambito_default": "Nacional",
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
        "ambito_default": "Internacional",
    },
    {
        "codigo": "worldbank",
        "nombre": "Banco Mundial (World Bank) - Procurement Notices",
        # API JSON v2 (verificada en vivo 2026-07-23). Paginación por os/rows.
        "url_base": "https://search.worldbank.org/api/v2/procnotices",
        "tipo": "api",
        "activa": True,
        "max_paginas": 3,
        "rate_limit_seconds": 1.0,
        "ambito_default": "Internacional",
    },
    {
        "codigo": "grantsgov",
        "nombre": "Grants.gov (EE. UU.) - Subvenciones federales",
        # API JSON search2 (POST, verificada en vivo 2026-07-23).
        "url_base": "https://api.grants.gov/v1/api/search2",
        "tipo": "api",
        "activa": True,
        "max_paginas": 2,
        "rate_limit_seconds": 1.0,
        "ambito_default": "Internacional",
    },
    {
        "codigo": "sicon",
        "nombre": "SICON - Convocatorias de Cultura de Bogotá (SCRD, IDARTES, FUGA, IDPC)",
        # Plataforma ÚNICA del Distrito Capital (fomento cultural). API JSON con
        # token público. Verificada en vivo 2026-07-23. El conector reporta
        # ambito_fuente="Territorial" por registro; no necesita ambito_default.
        "url_base": "https://sicon.scrd.gov.co/crud_SCRD_pv/api/DrupalWS/convocatorias_publicadas",
        "tipo": "api",
        "activa": True,
        "max_paginas": 4,
        "rate_limit_seconds": 1.0,
    },
]


def _config(data: dict) -> dict:
    """Config JSONB de la fuente. keywords vienen del env (editables sin código).

    `ambito_default` es solo un RESPALDO para el pipeline: se aplica a los
    registros cuyo conector no reporta un `ambito_fuente` propio. SECOP sí lo
    reporta por registro (`ordenentidad`), así que no lo declara.
    """
    config = {
        "keywords": settings.keywords,
        "max_paginas": data["max_paginas"],
        "rate_limit_seconds": data["rate_limit_seconds"],
    }
    if data.get("ambito_default"):
        config["ambito_default"] = data["ambito_default"]
    return config


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
