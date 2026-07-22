"""CONTRATO conector -> pipeline.

`RawConvocatoria` es lo que TODO conector devuelve en `fetch()`. Es un objeto
"crudo pero tipado": ya extraído de la fuente, todavía SIN normalizar
(el `estado_fuente` es texto libre de la fuente; el pipeline lo mapea a estado
canónico, calcula hashes y keywords_match).

Regla dura: si un dato no existe o no se puede parsear -> None. NUNCA inventar.
El único campo obligatorio de contenido es `url_original` (enlace a la fuente real).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.constants import PAIS_DEFAULT, TipoConvocatoria


class RawConvocatoria(BaseModel):
    """Convocatoria cruda entregada por un conector al pipeline."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_externo: str = Field(
        ...,
        description="Identificador de la convocatoria dentro de su fuente (crudo, estable).",
    )
    titulo: str = Field(
        ...,
        description="Título de la convocatoria tal como aparece en la fuente.",
    )
    descripcion: str | None = Field(
        default=None,
        description="Descripción/objeto de la convocatoria. None si la fuente no lo provee.",
    )
    entidad: str | None = Field(
        default=None,
        description="Entidad convocante (ordenadora del gasto / organismo). None si no aplica.",
    )
    tipo: TipoConvocatoria = Field(
        ...,
        description="Tipo canónico: licitacion|subvencion|fondo|rfp|eoi|otro.",
    )
    estado_fuente: str = Field(
        ...,
        description=(
            "Estado tal cual lo reporta la fuente (texto libre, ej. 'Convocado', "
            "'Cerrada', 'Adjudicado'). El pipeline lo mapea a estado canónico."
        ),
    )
    modalidad: str | None = Field(
        default=None,
        description=(
            "Modalidad de contratación/participación tal como la reporta la "
            "fuente (ej. 'Licitación pública', 'Concurso de méritos'). "
            "None si la fuente no la provee."
        ),
    )
    monto: Decimal | None = Field(
        default=None,
        description="Monto/presupuesto. None si la fuente no lo provee o es imparseable.",
    )
    moneda: str | None = Field(
        default=None,
        description="Código de moneda (ej. 'COP', 'USD'). None si no aplica.",
    )
    departamento: str | None = Field(
        default=None,
        description="Departamento/región. None si no aplica.",
    )
    ciudad: str | None = Field(
        default=None,
        description="Ciudad/municipio. None si no aplica.",
    )
    pais: str = Field(
        default=PAIS_DEFAULT,
        description="País de la convocatoria. Default 'Colombia'.",
    )
    fecha_publicacion: datetime | None = Field(
        default=None,
        description="Fecha de publicación (datetime en UTC). None si imparseable/ausente.",
    )
    fecha_apertura: datetime | None = Field(
        default=None,
        description="Fecha de apertura (datetime en UTC). None si imparseable/ausente.",
    )
    fecha_cierre: datetime | None = Field(
        default=None,
        description="Fecha de cierre (datetime en UTC). None si imparseable/ausente.",
    )
    requisitos: str | None = Field(
        default=None,
        description="Requisitos de participación (texto). None si la fuente no los expone.",
    )
    url_original: str = Field(
        ...,
        description="OBLIGATORIA. URL a la publicación original en la fuente.",
    )
    raw: dict = Field(
        default_factory=dict,
        description="Payload íntegro de la fuente (dict serializable) para auditoría.",
    )
