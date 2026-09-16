"""Exporte les cas de référence du moteur Python vers tests/fixtures/cases.json.

Le test Node (tests/js/engine.test.js) rejoue ces cas avec engine.js.
"""

import json
from itertools import combinations
from pathlib import Path

from litre_sans import Catalog, Scenario, SelectedMeasure, Simulator
from litre_sans.export import CatalogOut

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "cases.json"


def _scenarios(catalog: Catalog) -> list[tuple[str, Scenario]]:
    ids = [m.id for m in catalog.measures]
    cases: list[tuple[str, Scenario]] = [
        ("gazole sans mesure", Scenario(fuel="gazole")),
        ("e10 sans mesure", Scenario(fuel="e10")),
        ("gazole prix modifié", Scenario(fuel="gazole", start_price=1.99)),
        (
            "gazole prix minimal + epsilon",
            Scenario(fuel="gazole", start_price=0.6075 * 1.2 + 0.001),
        ),
    ]
    cases += [
        (f"gazole {i} seul", Scenario(fuel="gazole", selections=[SelectedMeasure(measure_id=i)]))
        for i in ids
    ]
    cases += [
        (
            f"gazole {a}+{b}",
            Scenario(
                fuel="gazole",
                selections=[SelectedMeasure(measure_id=a), SelectedMeasure(measure_id=b)],
            ),
        )
        for a, b in combinations(ids, 2)
    ]
    for m in catalog.measures:
        for v in m.variants[1:]:
            cases.append(
                (
                    f"e10 {m.id}/{v.id}",
                    Scenario(
                        fuel="e10", selections=[SelectedMeasure(measure_id=m.id, variant_id=v.id)]
                    ),
                )
            )
    cases.append(
        (
            "gazole tout (défaut)",
            Scenario(fuel="gazole", selections=[SelectedMeasure(measure_id=i) for i in ids]),
        )
    )
    cases.append(
        (
            "e10 tout, variante FP 1997, prix 2.60",
            Scenario(
                fuel="e10",
                start_price=2.60,
                selections=[
                    SelectedMeasure(
                        measure_id=i,
                        variant_id=("y1997" if i == "fp" else None),
                    )
                    for i in ids
                ],
            ),
        )
    )
    return cases


def test_export_cases(catalog: Catalog, simulator: Simulator) -> None:
    cases = []
    for label, scenario in _scenarios(catalog):
        result = simulator.simulate(scenario)
        cases.append(
            {
                "label": label,
                "scenario": scenario.model_dump(mode="json"),
                "expected": result.model_dump(mode="json"),
            }
        )
    payload = {
        "catalog": CatalogOut.from_domain(catalog, simulator).model_dump(mode="json"),
        "params": {
            "litres_billions": simulator.litres_billions,
            "vat_rate": simulator.vat_rate,
            "tank_litres": simulator.tank_litres,
        },
        "errors": [
            {
                "label": "mesure inconnue",
                "scenario": {"fuel": "gazole", "selections": [{"measure_id": "x"}]},
                "error": "UnknownMeasureError",
            },
            {
                "label": "variante inconnue",
                "scenario": {
                    "fuel": "gazole",
                    "selections": [{"measure_id": "fp", "variant_id": "y1950"}],
                },
                "error": "UnknownVariantError",
            },
            {
                "label": "carburant inconnu",
                "scenario": {"fuel": "kerosene"},
                "error": "UnknownFuelError",
            },
            {
                "label": "prix trop bas",
                "scenario": {"fuel": "gazole", "start_price": 0.5},
                "error": "InvalidPriceError",
            },
        ],
        "cases": cases,
    }
    FIXTURE.parent.mkdir(exist_ok=True)
    FIXTURE.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    assert len(cases) > 40
