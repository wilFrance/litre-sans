"""Configuration par variables d'environnement (préfixe LITRE_SANS_)."""

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LITRE_SANS_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    site_title: str = "Le litre sans…"
    litres_billions: float = Field(
        default=47.5, gt=0, description="Milliards de litres de carburants routiers livrés (2025)"
    )
    vat_rate: float = Field(default=0.20, ge=0, lt=1)
    tank_litres: float = Field(default=50.0, gt=0)
    measures_path: Path = PROJECT_ROOT / "data" / "measures.yaml"
    output_dir: Path = PROJECT_ROOT / "site"
    site_url: str = Field(
        default="",
        validation_alias=AliasChoices("SITE_URL", "LITRE_SANS_SITE_URL"),
        description="URL publique du site (pour les balises Open Graph), ex. https://x.github.io/y/",
    )
    goatcounter_code: str = Field(
        default="",
        validation_alias=AliasChoices("GOATCOUNTER_CODE", "LITRE_SANS_GOATCOUNTER_CODE"),
        description="Code GoatCounter (<code>.goatcounter.com). Vide : pas de mesure d'audience.",
    )
