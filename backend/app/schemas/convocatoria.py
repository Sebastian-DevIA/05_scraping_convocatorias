"""Schemas Pydantic v2 de `convocatorias` (salida de la API).

Nunca se retorna el modelo SQLAlchemy directo: siempre a través de estos
schemas Response. La forma exacta del JSON está congelada en
`docs/api-contract.md` (el frontend trabaja contra ese documento).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.constants import Ambito, EstadoConvocatoria, EstadoGestion, TipoConvocatoria


class ConvocatoriaResponse(BaseModel):
    """Convocatoria en listados (`GET /convocatorias`). No incluye `raw`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    id_externo: str

    fuente_id: int
    fuente_codigo: str = Field(description="Código de la fuente (secop, pnud, ...).")
    fuente_nombre: str = Field(description="Nombre legible de la fuente.")

    titulo: str
    descripcion: str | None = None
    entidad: str | None = None

    tipo: TipoConvocatoria
    modalidad: str | None = None
    estado: EstadoConvocatoria

    monto: Decimal | None = None
    moneda: str | None = None

    departamento: str | None = None
    ciudad: str | None = None
    pais: str
    ambito: Ambito = Field(
        default="desconocido",
        description=(
            "Ámbito de la entidad convocante: nacional | territorial | "
            "internacional | desconocido. 'territorial' agrupa alcaldías, "
            "gobernaciones, distritos y autoridades regionales."
        ),
    )

    fecha_publicacion: datetime | None = None
    fecha_apertura: datetime | None = None
    fecha_cierre: datetime | None = None

    url_original: str
    keywords_match: list[str] = Field(default_factory=list)
    apto_fundaciones_nuevas: bool = Field(
        default=False,
        description=(
            "Flag DERIVADO (heurístico) de aptitud para fundaciones nuevas/"
            "primerizas. True = se hallaron señales de apertura a nuevas "
            "organizaciones sin exigencia de trayectoria. False = sin evidencia "
            "(no afirma 'no apto'). Verificar siempre en la publicación oficial."
        ),
    )

    estado_gestion: EstadoGestion | None = Field(
        default=None,
        description=(
            "Estado del histórico propio de gestión: 'postulada' (ya nos "
            "postulamos), 'descartada', o null si no se ha gestionado. Las "
            "gestionadas se excluyen del listado salvo `incluir_gestionadas=true`."
        ),
    )

    primera_vez_visto: datetime
    ultima_vez_visto: datetime
    creado_en: datetime
    actualizado_en: datetime


class ConvocatoriaDetailResponse(ConvocatoriaResponse):
    """Detalle (`GET /convocatorias/{id}`): añade requisitos y raw opcional."""

    requisitos: str | None = None
    # Solo presente si se pide `?include_raw=true`.
    raw: dict | None = Field(default=None, description="Payload íntegro de la fuente.")


class ConvocatoriaPageResponse(BaseModel):
    """Página de convocatorias: `{items, total, page, page_size}`."""

    items: list[ConvocatoriaResponse]
    total: int = Field(description="Total de filas que cumplen el filtro (sin paginar).")
    page: int = Field(description="Página actual (base 1).")
    page_size: int = Field(description="Tamaño de página.")


class ConvocatoriaExportRequest(BaseModel):
    """Cuerpo de `POST /convocatorias/export`: ids de convocatorias a exportar.

    El usuario selecciona en el frontend las convocatorias en las que quiere
    participar; se envían sus ids y la API devuelve un `.xlsx` con los datos
    necesarios para participar (incluida `url_original` para verificar que la
    convocatoria existe en la fuente oficial).
    """

    ids: list[int] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Ids de convocatorias seleccionadas (1..1000).",
    )
