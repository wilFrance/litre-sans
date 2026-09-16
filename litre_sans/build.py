"""Génère le site statique : `uv run build-site [--out DOSSIER]`."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from litre_sans.catalog import load_catalog
from litre_sans.config import Settings
from litre_sans.export import CatalogOut
from litre_sans.models import Catalog
from litre_sans.og_image import render_default, render_scenario
from litre_sans.simulator import Simulator

PACKAGE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"

# page -> (template, chemin publié). Les chemins sont relatifs : le site fonctionne sous /<repo>/.
PAGES: dict[str, tuple[str, str]] = {
    "index": ("index.html", ""),
    "methode": ("methode.html", "methode/"),
    "mentions": ("mentions.html", "mentions-legales/"),
}
TAGLINE = (
    "Cochez des dépenses publiques à supprimer : leur montant baisse les taxes sur le carburant."
)


def fr_number(value: float, decimals: int = 1) -> str:
    """Formate un nombre à la française (virgule décimale, sans zéros inutiles)."""
    text = f"{value:.{decimals}f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def page_context(
    catalog: Catalog,
    simulator: Simulator,
    settings: Settings,
    *,
    page: str,
    static_url: Callable[[str], str],
    page_url: Callable[[str], str],
    published: str = "",
    og: dict[str, str] | None = None,
    preset: str = "",
) -> dict[str, Any]:
    catalog_out = CatalogOut.from_domain(catalog, simulator)
    site_url = settings.site_url.strip()
    if site_url and not site_url.endswith("/"):
        site_url += "/"
    og = {
        "title": settings.site_title,
        "description": TAGLINE,
        "image": "static/og/default.png",
        **(og or {}),
    }
    return {
        "settings": settings,
        "goatcounter_code": settings.goatcounter_code.strip(),
        "page": page,
        "preset": preset,
        "static_url": static_url,
        "page_url": page_url,
        "site_url": site_url,
        "og_url": f"{site_url}{published}" if site_url else "",
        "og_image": f"{site_url}{og['image']}" if site_url else "",
        "og_title": og["title"],
        "og_description": og["description"],
        "catalog": catalog_out,
        "catalog_json": catalog_out.model_dump_json(),
        "groups": catalog.groups,
        "litres_billions_fr": fr_number(simulator.litres_billions),
        "vat_percent": round(simulator.vat_rate * 100),
        "per_billion_cents_fr": fr_number(100 / simulator.litres_billions, 1),
    }


def _fr_money(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def build(out_dir: Path, settings: Settings) -> None:
    catalog = load_catalog(settings.measures_path)
    simulator = Simulator(
        catalog,
        litres_billions=settings.litres_billions,
        vat_rate=settings.vat_rate,
        tank_litres=settings.tank_litres,
    )

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    # Données : site/data/measures.json
    data_dir = out_dir / "data"
    data_dir.mkdir()
    catalog_out = CatalogOut.from_domain(catalog, simulator)
    (data_dir / "measures.json").write_text(
        json.dumps(catalog_out.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # Fichiers statiques : site/static/
    shutil.copytree(STATIC_DIR, out_dir / "static")

    # Images d'aperçu Open Graph : une par scénario phare + une générique
    og_dir = out_dir / "static" / "og"
    og_dir.mkdir()
    render_default(site_title=settings.site_title, tagline=TAGLINE).save(og_dir / "default.png")
    fuel_label = catalog.fuels[0].label
    for sc in catalog_out.scenarios:
        render_scenario(
            title=f"{sc.title} : {_fr_money(sc.tank_saving)} € de moins sur le plein",
            price_before=sc.price_before,
            price_after=sc.price_after,
            tank_saving=sc.tank_saving,
            tank_litres=sc.tank_litres,
            fuel_label=fuel_label,
            site_title=settings.site_title,
        ).save(og_dir / f"{sc.id}.png")

    # Pages HTML
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html"]),
        keep_trailing_newline=True,
    )
    versions = {
        str(f.relative_to(STATIC_DIR)).replace("\\", "/"): _digest(f)
        for f in STATIC_DIR.rglob("*")
        if f.is_file()
    }

    # Pages fixes + une page par scénario phare (même simulateur, mesure pré-cochée)
    jobs: list[tuple[str, str, str, dict[str, str], str]] = [
        (page, template, published, {}, "") for page, (template, published) in PAGES.items()
    ]
    for sc in catalog_out.scenarios:
        og = {
            "title": f"{sc.title} : {_fr_money(sc.tank_saving)} € de moins sur le plein",
            "description": (
                f"Le litre de {fuel_label.lower()} passerait de {_fr_money(sc.price_before)} € à "
                f"{_fr_money(sc.price_after)} €. Et vous, que supprimeriez-vous ?"
            ),
            "image": f"static/og/{sc.id}.png",
        }
        jobs.append(("index", "index.html", sc.path, og, sc.measure_id))

    for page, template_name, published, og, preset in jobs:
        prefix = "../" * published.count("/")

        def static_url(path: str, prefix: str = prefix) -> str:
            # Empreinte du contenu en query string : un fichier modifié n'est jamais servi
            # depuis le cache du navigateur avec une page qui ne lui correspond pas.
            return f"{prefix}static/{path}?v={versions[path]}"

        def page_url(name: str, prefix: str = prefix) -> str:
            target = PAGES[name][1]
            return f"{prefix}{target}" if target or prefix else "./"

        context = page_context(
            catalog,
            simulator,
            settings,
            page=page,
            static_url=static_url,
            page_url=page_url,
            published=published,
            og=og,
            preset=preset,
        )
        html = env.get_template(template_name).render(context)
        target = out_dir / published / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")

    (out_dir / ".nojekyll").touch()  # GitHub Pages : servir les fichiers tels quels
    n_scenarios = len(catalog_out.scenarios)
    print(f"Site généré dans {out_dir} ({len(jobs)} pages dont {n_scenarios} scénarios)")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


def main(argv: list[str] | None = None) -> None:
    settings = Settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=settings.output_dir, help="dossier de sortie")
    args = parser.parse_args(argv)
    build(args.out.resolve(), settings)


if __name__ == "__main__":
    main()
