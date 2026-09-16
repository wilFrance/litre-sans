"""Moteur de calcul « tout sur le carburant ». Pur Python, référence pour engine.js."""

from pydantic import BaseModel, ConfigDict, Field

from litre_sans.errors import InvalidPriceError
from litre_sans.models import Catalog, FuelCode, Measure, MeasureVariant

CAP_EPSILON_BN = 0.005  # en dessous de 5 M€, on ne parle pas de plafond


class SelectedMeasure(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    measure_id: str
    variant_id: str | None = Field(default=None, description="None : variante par défaut")


class Scenario(BaseModel):
    """Ce que l'utilisateur choisit : carburant, prix de départ, mesures cochées."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fuel: FuelCode
    start_price: float | None = Field(
        default=None, gt=0, description="Prix TTC de départ en €/L ; None : prix de référence"
    )
    selections: list[SelectedMeasure] = Field(default_factory=list)


class PriceBreakdown(BaseModel):
    model_config = ConfigDict(frozen=True)

    ht: float = Field(description="Produit, raffinage, distribution, CEE (€/L)")
    excise: float = Field(description="Accise sur les énergies (€/L)")
    vat: float = Field(description="TVA (€/L)")
    total: float = Field(description="Prix TTC (€/L)")


class SimulationResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    fuel: FuelCode
    price_before: float = Field(description="Prix de départ (€/L)")
    breakdown_after: PriceBreakdown
    cut_per_litre: float = Field(description="Baisse obtenue (€/L)")
    budget_savings_bn: float = Field(description="Économies budgétaires cochées (Md€/an)")
    unused_savings_bn: float = Field(
        description="Économies sans effet sur le litre car les taxes sont déjà à zéro (Md€/an)"
    )
    cap_reached: bool = Field(description="Vrai si le plafond (taxes à zéro) est atteint")
    tank_saving: float = Field(description="Gain sur un plein (€)")
    tank_litres: float = Field(description="Volume du plein retenu (L)")

    @property
    def price_after(self) -> float:
        return self.breakdown_after.total


class Simulator:
    def __init__(
        self,
        catalog: Catalog,
        *,
        litres_billions: float,
        vat_rate: float,
        tank_litres: float = 50.0,
    ) -> None:
        if litres_billions <= 0:
            raise ValueError("litres_billions doit être strictement positif")
        if not 0 <= vat_rate < 1:
            raise ValueError("vat_rate doit être compris entre 0 et 1")
        self.catalog = catalog
        self.litres_billions = litres_billions
        self.vat_rate = vat_rate
        self.tank_litres = tank_litres

    def unit_effect(self, measure: Measure, variant: MeasureVariant) -> float:
        return measure.unit_effect(variant, self.litres_billions)

    def minimum_price(self, fuel_code: str) -> float:
        """Prix de départ minimal : l'accise TTC."""
        return self.catalog.fuel(fuel_code).excise * (1 + self.vat_rate)

    def simulate(self, scenario: Scenario) -> SimulationResult:
        fuel = self.catalog.fuel(scenario.fuel)
        price = fuel.reference_price if scenario.start_price is None else scenario.start_price
        minimum = self.minimum_price(fuel.code)
        if price <= minimum:
            raise InvalidPriceError(price, minimum)

        vat_factor = 1 + self.vat_rate
        direct_total = 0.0
        budget_total_bn = 0.0
        for selection in scenario.selections:
            measure = self.catalog.measure(selection.measure_id)
            variant = measure.variant(selection.variant_id)
            direct_total += variant.direct_per_litre
            budget_total_bn += variant.budget_bn

        # 1-2. Hors taxes, avant puis après les composantes directes.
        ht_base = max(0.0, price / vat_factor - fuel.excise)
        ht = max(0.0, ht_base - direct_total / vat_factor)

        # 3. Taxes = accise + TVA sur (HT + accise).
        vat = self.vat_rate * (ht + fuel.excise)
        taxes = fuel.excise + vat

        # 4-5. Baisse budgétaire par litre, plafonnée aux taxes.
        budget_cut = budget_total_bn / self.litres_billions
        effective_cut = min(taxes, budget_cut)

        # 6. Prorata entre accise et TVA.
        keep_ratio = (taxes - effective_cut) / taxes if taxes > 0 else 0.0

        # 7-8. Prix final et économies sans effet.
        price_after = ht + taxes - effective_cut
        unused_bn = max(0.0, budget_cut - taxes) * self.litres_billions
        cut = price - price_after

        return SimulationResult(
            fuel=fuel.code,
            price_before=price,
            breakdown_after=PriceBreakdown(
                ht=ht, excise=fuel.excise * keep_ratio, vat=vat * keep_ratio, total=price_after
            ),
            cut_per_litre=cut,
            budget_savings_bn=budget_total_bn,
            unused_savings_bn=unused_bn,
            cap_reached=unused_bn > CAP_EPSILON_BN,
            tank_saving=cut * self.tank_litres,
            tank_litres=self.tank_litres,
        )
