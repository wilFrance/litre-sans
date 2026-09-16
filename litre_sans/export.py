"""Vue JSON du catalogue : injectée dans les pages et écrite dans site/data/measures.json."""

from pydantic import BaseModel, ConfigDict, Field

from litre_sans.models import (
    Badge,
    BadgeLevel,
    Catalog,
    Fuel,
    FuelCode,
    Measure,
    MeasureVariant,
    Source,
)
from litre_sans.simulator import Simulator


class FuelOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: FuelCode
    label: str
    reference_price: float
    excise: float
    minimum_price: float = Field(description="Prix de départ minimal accepté (accise TTC, €/L)")

    @classmethod
    def from_domain(cls, fuel: Fuel, simulator: Simulator) -> "FuelOut":
        return cls(
            code=fuel.code,
            label=fuel.label,
            reference_price=fuel.reference_price,
            excise=fuel.excise,
            minimum_price=simulator.minimum_price(fuel.code),
        )


class BadgeOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    level: BadgeLevel
    label: str

    @classmethod
    def from_domain(cls, badge: Badge) -> "BadgeOut":
        return cls(level=badge.level, label=badge.label)


class SourceOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    url: str

    @classmethod
    def from_domain(cls, source: Source) -> "SourceOut":
        return cls(label=source.label, url=str(source.url))


class VariantOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    label: str
    budget_bn: float
    direct_per_litre: float
    badge: BadgeOut
    is_default: bool
    unit_effect_per_litre: float = Field(
        description="Baisse du prix attribuable, hors plafond (€/L)"
    )

    @classmethod
    def from_domain(
        cls, measure: Measure, variant: MeasureVariant, simulator: Simulator
    ) -> "VariantOut":
        return cls(
            id=variant.id,
            label=variant.label,
            budget_bn=variant.budget_bn,
            direct_per_litre=variant.direct_per_litre,
            badge=BadgeOut.from_domain(variant.badge),
            is_default=variant is measure.default_variant,
            unit_effect_per_litre=simulator.unit_effect(measure, variant),
        )


class MeasureOut(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    group: str
    name: str
    sponsors: str
    note: str
    sources: list[SourceOut]
    variants: list[VariantOut]

    @classmethod
    def from_domain(cls, measure: Measure, simulator: Simulator) -> "MeasureOut":
        return cls(
            id=measure.id,
            group=measure.group,
            name=measure.name,
            sponsors=measure.sponsors,
            note=measure.note,
            sources=[SourceOut.from_domain(src) for src in measure.sources],
            variants=[VariantOut.from_domain(measure, v, simulator) for v in measure.variants],
        )


class CatalogOut(BaseModel):
    """Vue complète du catalogue, injectée dans la page pour le premier rendu."""

    model_config = ConfigDict(frozen=True)

    fuels: list[FuelOut]
    measures: list[MeasureOut]
    litres_billions: float
    vat_rate: float
    tank_litres: float

    @classmethod
    def from_domain(cls, catalog: Catalog, simulator: Simulator) -> "CatalogOut":
        return cls(
            fuels=[FuelOut.from_domain(f, simulator) for f in catalog.fuels],
            measures=[MeasureOut.from_domain(m, simulator) for m in catalog.measures],
            litres_billions=simulator.litres_billions,
            vat_rate=simulator.vat_rate,
            tank_litres=simulator.tank_litres,
        )
