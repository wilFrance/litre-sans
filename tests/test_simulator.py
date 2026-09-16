"""Cas de test obligatoires (gazole, 2,364 €, accise 0,6075 €) et bornes."""

import pytest

from litre_sans import (
    InvalidPriceError,
    Scenario,
    SelectedMeasure,
    Simulator,
    UnknownFuelError,
    UnknownMeasureError,
    UnknownVariantError,
)

TOL = 0.0005  # comparaison à 3 décimales près


def gazole(*ids: str, price: float | None = 2.364, variants: dict[str, str] | None = None):
    variants = variants or {}
    return Scenario(
        fuel="gazole",
        start_price=price,
        selections=[SelectedMeasure(measure_id=i, variant_id=variants.get(i)) for i in ids],
    )


@pytest.mark.parametrize(
    ("ids", "expected"),
    [
        ((), 2.364),
        (("energie",), 2.046),
        (("agences",), 2.329),
        (("ame",), 2.339),
        (("fp",), 1.669),
    ],
)
def test_reference_prices(simulator: Simulator, ids: tuple[str, ...], expected: float) -> None:
    result = simulator.simulate(gazole(*ids))
    assert result.price_after == pytest.approx(expected, abs=TOL)
    assert not result.cap_reached
    assert result.unused_savings_bn == 0


def test_all_measures_hits_cap(simulator: Simulator) -> None:
    ids = [m.id for m in simulator.catalog.measures]
    result = simulator.simulate(gazole(*ids))
    # Valeur exacte 1,2375 : on accepte 1,237 ou 1,238 selon l'arrondi.
    assert result.price_after == pytest.approx(1.2375, abs=TOL)
    assert result.cap_reached
    assert result.unused_savings_bn > 0
    assert result.breakdown_after.excise == pytest.approx(0)
    assert result.breakdown_after.vat == pytest.approx(0)
    assert result.price_after == pytest.approx(result.breakdown_after.ht)


def test_default_price_is_reference(simulator: Simulator) -> None:
    result = simulator.simulate(Scenario(fuel="gazole"))
    assert result.price_before == 2.364
    assert result.price_after == pytest.approx(2.364)
    assert result.cut_per_litre == 0


def test_fp_variant_1997(simulator: Simulator) -> None:
    default = simulator.simulate(gazole("fp"))
    other = simulator.simulate(gazole("fp", variants={"fp": "y1997"}))
    assert other.budget_savings_bn == pytest.approx(24.0)
    assert other.price_after == pytest.approx(1.859, abs=TOL)
    assert other.price_after > default.price_after


def test_taxes_cut_pro_rata(simulator: Simulator) -> None:
    before = simulator.simulate(gazole()).breakdown_after
    after = simulator.simulate(gazole("ame")).breakdown_after
    assert after.ht == pytest.approx(before.ht)
    ratio_excise = after.excise / before.excise
    ratio_vat = after.vat / before.vat
    assert ratio_excise == pytest.approx(ratio_vat)
    assert 0 < ratio_excise < 1


def test_breakdown_sums_to_total(simulator: Simulator) -> None:
    b = simulator.simulate(gazole("energie", "apd")).breakdown_after
    assert b.ht + b.excise + b.vat == pytest.approx(b.total)


def test_tank_saving(simulator: Simulator) -> None:
    result = simulator.simulate(gazole("energie"))
    assert result.tank_litres == 50
    assert result.tank_saving == pytest.approx(result.cut_per_litre * 50)


def test_unit_effect(simulator: Simulator) -> None:
    energie = simulator.catalog.measure("energie")
    ame = simulator.catalog.measure("ame")
    assert simulator.unit_effect(energie, energie.default_variant) == pytest.approx(
        0.15 + 7.983 / 47.5
    )
    assert simulator.unit_effect(ame, ame.default_variant) == pytest.approx(1.208 / 47.5)


def test_direct_component_reduces_ht_not_taxes(simulator: Simulator) -> None:
    before = simulator.simulate(gazole()).breakdown_after
    after = simulator.simulate(gazole("energie")).breakdown_after
    assert after.ht == pytest.approx(before.ht - 0.15 / 1.2)


def test_e10_uses_its_own_excise(simulator: Simulator) -> None:
    result = simulator.simulate(Scenario(fuel="e10"))
    assert result.price_before == 2.150
    assert result.breakdown_after.excise == pytest.approx(0.6702)


# ---------- Bornes ----------


def test_price_below_excise_ttc_is_rejected(simulator: Simulator) -> None:
    with pytest.raises(InvalidPriceError):
        simulator.simulate(gazole(price=0.6075 * 1.2))
    with pytest.raises(InvalidPriceError):
        simulator.simulate(gazole(price=0.5))


def test_price_just_above_minimum(simulator: Simulator) -> None:
    result = simulator.simulate(gazole(price=0.6075 * 1.2 + 0.001))
    assert result.breakdown_after.ht == pytest.approx(0, abs=1e-3)


def test_unknown_measure(simulator: Simulator) -> None:
    with pytest.raises(UnknownMeasureError):
        simulator.simulate(gazole("inconnue"))


def test_unknown_variant(simulator: Simulator) -> None:
    with pytest.raises(UnknownVariantError):
        simulator.simulate(gazole("fp", variants={"fp": "y1950"}))


def test_unknown_fuel(simulator: Simulator) -> None:
    scenario = Scenario.model_construct(fuel="kerosene", start_price=2.0, selections=[])
    with pytest.raises(UnknownFuelError):
        simulator.simulate(scenario)


def test_simulator_rejects_bad_parameters(simulator: Simulator) -> None:
    with pytest.raises(ValueError, match="litres_billions"):
        Simulator(simulator.catalog, litres_billions=0, vat_rate=0.2)
    with pytest.raises(ValueError, match="vat_rate"):
        Simulator(simulator.catalog, litres_billions=47.5, vat_rate=1.5)
