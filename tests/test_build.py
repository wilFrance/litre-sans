"""Le générateur produit un site complet avec des chemins relatifs."""

import json
import re
from pathlib import Path

from litre_sans.build import STATIC_DIR, build
from litre_sans.config import Settings


def test_build(tmp_path: Path) -> None:
    out = tmp_path / "site"
    build(out, Settings())
    assert (out / ".nojekyll").exists()
    index = (out / "index.html").read_text(encoding="utf-8")
    methode = (out / "methode" / "index.html").read_text(encoding="utf-8")
    mentions = (out / "mentions-legales" / "index.html").read_text(encoding="utf-8")
    assert re.search(r'src="static/js/engine\.js\?v=[0-9a-f]{10}"', index)
    assert re.search(r'href="static/css/style\.css\?v=[0-9a-f]{10}"', index)
    assert re.search(r'href="\.\./static/css/style\.css\?v=[0-9a-f]{10}"', methode)
    assert 'href="../"' in methode and 'href="../mentions-legales/"' in methode
    assert "GitHub" in mentions
    assert "/static/" not in index  # aucun chemin absolu
    data = json.loads((out / "data" / "measures.json").read_text(encoding="utf-8"))
    assert data["litres_billions"] == 47.5 and data["vat_rate"] == 0.2
    assert len(data["measures"]) == 8
    assert (out / "static" / "js" / "engine.js").read_text(encoding="utf-8") == (
        (STATIC_DIR / "js" / "engine.js").read_text(encoding="utf-8")
    )
