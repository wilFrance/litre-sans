from pathlib import Path

import pytest

from litre_sans import Catalog, Simulator, load_catalog
from litre_sans.config import PROJECT_ROOT

MEASURES_PATH = PROJECT_ROOT / "data" / "measures.yaml"


@pytest.fixture(scope="session")
def catalog() -> Catalog:
    return load_catalog(MEASURES_PATH)


@pytest.fixture(scope="session")
def simulator(catalog: Catalog) -> Simulator:
    return Simulator(catalog, litres_billions=47.5, vat_rate=0.20, tank_litres=50)


@pytest.fixture
def tmp_yaml(tmp_path: Path):
    def write(content: str) -> Path:
        p = tmp_path / "measures.yaml"
        p.write_text(content, encoding="utf-8")
        return p

    return write
