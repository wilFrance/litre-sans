"""Entités du catalogue : carburants, mesures, variantes, sources."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from litre_sans.errors import UnknownFuelError, UnknownMeasureError, UnknownVariantError

FuelCode = Literal["gazole", "e10"]
BadgeLevel = Literal["ok", "warn"]

DEFAULT_VARIANT_ID = "default"


class Entity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Fuel(Entity):
    code: FuelCode
    label: str = Field(min_length=1)
    reference_price: float = Field(gt=0, description="Prix TTC de référence, en €/L")
    excise: float = Field(ge=0, description="Accise sur les énergies, en €/L")


class Badge(Entity):
    level: BadgeLevel
    label: str = Field(min_length=1)


class Source(Entity):
    label: str = Field(min_length=1)
    url: HttpUrl


class MeasureVariant(Entity):
    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    label: str = Field(min_length=1)
    budget_bn: float = Field(default=0, ge=0, description="Économie budgétaire, Md€ par an")
    direct_per_litre: float = Field(
        default=0, ge=0, description="Baisse directe du prix TTC, €/L (ex. CEE)"
    )
    badge: Badge

    @model_validator(mode="after")
    def _has_effect(self) -> Self:
        if self.budget_bn == 0 and self.direct_per_litre == 0:
            raise ValueError(f"variante « {self.id} » : budget_bn ou direct_per_litre requis")
        return self


class Measure(Entity):
    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    group: str = Field(min_length=1)
    name: str = Field(min_length=1)
    sponsors: str = Field(min_length=1, description="Porteur(s) de la mesure")
    note: str = ""
    sources: list[Source] = Field(min_length=1)
    variants: list[MeasureVariant] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_variant_ids(self) -> Self:
        ids = [v.id for v in self.variants]
        if len(ids) != len(set(ids)):
            raise ValueError(f"mesure « {self.id} » : identifiants de variantes dupliqués")
        return self

    @property
    def default_variant(self) -> MeasureVariant:
        return self.variants[0]

    @property
    def has_choices(self) -> bool:
        return len(self.variants) > 1

    def variant(self, variant_id: str | None) -> MeasureVariant:
        if variant_id is None:
            return self.default_variant
        for v in self.variants:
            if v.id == variant_id:
                return v
        raise UnknownVariantError(self.id, variant_id)

    def unit_effect(self, variant: MeasureVariant, litres_billions: float) -> float:
        """Baisse du prix en €/L attribuable à cette variante, hors plafond."""
        return variant.direct_per_litre + variant.budget_bn / litres_billions


class Catalog(Entity):
    fuels: list[Fuel] = Field(min_length=1)
    measures: list[Measure] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique_ids(self) -> Self:
        fuel_codes = [f.code for f in self.fuels]
        if len(fuel_codes) != len(set(fuel_codes)):
            raise ValueError("codes de carburants dupliqués")
        measure_ids = [m.id for m in self.measures]
        if len(measure_ids) != len(set(measure_ids)):
            dupes = sorted({i for i in measure_ids if measure_ids.count(i) > 1})
            raise ValueError(f"identifiants de mesures dupliqués : {', '.join(dupes)}")
        return self

    def fuel(self, code: str) -> Fuel:
        for f in self.fuels:
            if f.code == code:
                return f
        raise UnknownFuelError(code)

    def measure(self, measure_id: str) -> Measure:
        for m in self.measures:
            if m.id == measure_id:
                return m
        raise UnknownMeasureError(measure_id)

    @property
    def groups(self) -> list[str]:
        """Groupes dans l'ordre d'apparition."""
        seen: dict[str, None] = {}
        for m in self.measures:
            seen.setdefault(m.group, None)
        return list(seen)
