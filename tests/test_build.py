"""Le générateur produit un site complet avec des chemins relatifs."""

import json
import re
from pathlib import Path

import pytest

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


def test_build_without_goatcounter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GOATCOUNTER_CODE", raising=False)
    monkeypatch.delenv("LITRE_SANS_GOATCOUNTER_CODE", raising=False)
    out = tmp_path / "site"
    build(out, Settings(goatcounter_code=""))
    for page in out.rglob("*.html"):
        assert "goatcounter" not in page.read_text(encoding="utf-8").lower(), page


def test_build_with_goatcounter(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOATCOUNTER_CODE", "mon-site")
    settings = Settings()
    assert settings.goatcounter_code == "mon-site"
    out = tmp_path / "site"
    build(out, settings)
    pages = list(out.rglob("*.html"))
    assert len(pages) == 3 + 8  # pages fixes + une par scénario
    for page in pages:
        html = page.read_text(encoding="utf-8")
        assert 'data-goatcounter="https://mon-site.goatcounter.com/count"' in html, page
        assert 'src="//gc.zgo.at/count.js"' in html, page
    assert "analytics.js?v=" in (out / "index.html").read_text(encoding="utf-8")


def test_scenario_pages_and_og(tmp_path: Path) -> None:
    out = tmp_path / "site"
    build(out, Settings(site_url="https://example.org/litre-sans", goatcounter_code=""))
    ame = (out / "s" / "ame" / "index.html").read_text(encoding="utf-8")
    assert 'data-preset="ame"' in ame
    assert 'data-site-url="https://example.org/litre-sans/"' in ame
    assert '<meta property="og:url" content="https://example.org/litre-sans/s/ame/">' in ame
    og_image = (
        '<meta property="og:image" content="https://example.org/litre-sans/static/og/ame.png?v='
    )
    assert og_image in ame
    assert "1,27 € de moins sur le plein" in ame
    assert 'href="../../static/css/style.css?v=' in ame
    assert 'href="../../methode/"' in ame
    index = (out / "index.html").read_text(encoding="utf-8")
    assert 'content="https://example.org/litre-sans/static/og/default.png?v=' in index
    assert "data-preset" not in index
    # Carte générique : le prix plancher (toutes mesures cochées), pas seulement le nom du site
    assert "Le litre de gazole à 1,24 €, c&#39;est possible. Voici comment !" in index
    assert "Aujourd&#39;hui 2,36 €" in index
    for sc in json.loads((out / "data" / "measures.json").read_text(encoding="utf-8"))["scenarios"]:
        img = out / "static" / "og" / f"{sc['id']}.png"
        assert img.is_file() and img.stat().st_size > 10_000, sc["id"]
        assert (out / sc["path"] / "index.html").is_file()


def test_og_image_dimensions(tmp_path: Path) -> None:
    from PIL import Image

    out = tmp_path / "site"
    build(out, Settings(goatcounter_code=""))
    with Image.open(out / "static" / "og" / "default.png") as img:
        assert img.size == (1200, 630)
