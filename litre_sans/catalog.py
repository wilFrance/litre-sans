"""Chargement et validation du catalogue YAML."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from litre_sans.models import Catalog


class CatalogError(RuntimeError):
    """Le fichier de données est absent ou invalide : l'application ne doit pas démarrer."""


def load_catalog(path: Path) -> Catalog:
    if not path.is_file():
        raise CatalogError(f"Fichier de mesures introuvable : {path}")
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CatalogError(f"YAML invalide dans {path} : {exc}") from exc
    if not isinstance(raw, dict):
        raise CatalogError(
            f"{path} : le document doit être un mapping avec « fuels » et « measures »"
        )
    try:
        return Catalog.model_validate(raw)
    except ValidationError as exc:
        raise CatalogError(f"Données invalides dans {path} :\n{_format(exc)}") from exc


def _format(exc: ValidationError) -> str:
    lines = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "<racine>"
        lines.append(f"  - {loc} : {err['msg']}")
    return "\n".join(lines)
