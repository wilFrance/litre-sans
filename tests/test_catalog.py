"""Le fichier data/measures.yaml doit être complet, cohérent, et strictement validé."""

from pathlib import Path

import pytest

from litre_sans import Catalog, CatalogError, load_catalog


def test_every_measure_has_source_and_variant(catalog: Catalog) -> None:
    for m in catalog.measures:
        assert m.sources, f"{m.id} : source manquante"
        for src in m.sources:
            assert str(src.url).startswith("https://"), f"{m.id} : URL non https"
        assert len(m.variants) >= 1, f"{m.id} : aucune variante"
        for v in m.variants:
            assert v.badge.label, f"{m.id}/{v.id} : badge sans libellé"
            assert v.budget_bn > 0 or v.direct_per_litre > 0, f"{m.id}/{v.id} : sans effet"


def test_expected_ids(catalog: Catalog) -> None:
    ids = {m.id for m in catalog.measures}
    assert ids == {"energie", "agences", "ame", "pnc", "apd", "av", "ville", "fp"}
    assert {f.code for f in catalog.fuels} == {"gazole", "e10"}


def test_default_variants(catalog: Catalog) -> None:
    assert catalog.measure("pnc").default_variant.budget_bn == 9
    assert catalog.measure("fp").default_variant.budget_bn == 33.0
    energie = catalog.measure("energie").default_variant
    assert energie.direct_per_litre == 0.15 and energie.budget_bn == 7.983
    assert len(catalog.measure("agences").sources) == 3


def test_groups_in_order(catalog: Catalog) -> None:
    assert catalog.groups == [
        "Énergie",
        "Agences et organismes",
        "Immigration",
        "Autres dépenses",
        "Fonction publique",
    ]


# ---------- Chargement : une erreur de données doit bloquer le build ----------

VALID = """
fuels:
  - {code: gazole, label: Gazole, reference_price: 2.364, excise: 0.6075}
measures:
  - id: ame
    group: Immigration
    name: Supprimer l'AME
    sponsors: X
    share_label: sans l'AME
    sources:
      - {label: AN, url: https://example.org/ame}
    variants:
      - {id: default, label: "1,2 Md€", budget_bn: 1.208, badge: {level: ok, label: Budget 2026}}
"""


def test_valid_file(tmp_yaml) -> None:
    catalog = load_catalog(tmp_yaml(VALID))
    assert catalog.measure("ame").default_variant.budget_bn == 1.208


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(CatalogError, match="introuvable"):
        load_catalog(tmp_path / "nope.yaml")


def test_invalid_yaml(tmp_yaml) -> None:
    with pytest.raises(CatalogError, match="YAML invalide"):
        load_catalog(tmp_yaml("fuels: [\nmeasures"))


def test_not_a_mapping(tmp_yaml) -> None:
    with pytest.raises(CatalogError, match="mapping"):
        load_catalog(tmp_yaml("- 1\n- 2\n"))


def test_missing_source(tmp_yaml) -> None:
    content = VALID.replace("      - {label: AN, url: https://example.org/ame}\n", "").replace(
        "    sources:\n", "    sources: []\n"
    )
    with pytest.raises(CatalogError, match=r"measures\.0\.sources"):
        load_catalog(tmp_yaml(content))


def test_no_variant(tmp_yaml) -> None:
    content = VALID.split("    variants:")[0] + "    variants: []\n"
    with pytest.raises(CatalogError, match="variants"):
        load_catalog(tmp_yaml(content))


def test_variant_without_effect(tmp_yaml) -> None:
    with pytest.raises(CatalogError, match="budget_bn ou direct_per_litre"):
        load_catalog(tmp_yaml(VALID.replace("budget_bn: 1.208", "budget_bn: 0")))


def test_bad_badge_level(tmp_yaml) -> None:
    with pytest.raises(CatalogError, match=r"badge\.level"):
        load_catalog(tmp_yaml(VALID.replace("level: ok", "level: maybe")))


def test_duplicate_measure_id(tmp_yaml) -> None:
    measure_block = VALID.split("measures:\n")[1]
    with pytest.raises(CatalogError, match="dupliqués : ame"):
        load_catalog(tmp_yaml(VALID + measure_block))


def test_unknown_field_is_rejected(tmp_yaml) -> None:
    with pytest.raises(CatalogError, match="Extra inputs"):
        load_catalog(tmp_yaml(VALID.replace("sponsors: X", "sponsors: X\n    porteur: Y")))
