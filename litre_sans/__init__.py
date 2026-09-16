"""Le litre sans… — moteur de calcul de référence et générateur de site statique."""

from litre_sans.catalog import CatalogError, load_catalog
from litre_sans.errors import (
    DomainError,
    InvalidPriceError,
    UnknownFuelError,
    UnknownMeasureError,
    UnknownVariantError,
)
from litre_sans.models import Badge, Catalog, Fuel, Measure, MeasureVariant, Source
from litre_sans.simulator import (
    PriceBreakdown,
    Scenario,
    SelectedMeasure,
    SimulationResult,
    Simulator,
)

__all__ = [
    "Badge",
    "Catalog",
    "CatalogError",
    "DomainError",
    "Fuel",
    "InvalidPriceError",
    "Measure",
    "MeasureVariant",
    "PriceBreakdown",
    "Scenario",
    "SelectedMeasure",
    "SimulationResult",
    "Simulator",
    "Source",
    "UnknownFuelError",
    "UnknownMeasureError",
    "UnknownVariantError",
    "load_catalog",
]
