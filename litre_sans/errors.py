"""Erreurs métier, indépendantes de la couche web."""


class DomainError(ValueError):
    """Base des erreurs de scénario."""


class UnknownFuelError(DomainError):
    def __init__(self, code: str) -> None:
        super().__init__(f"Carburant inconnu : « {code} »")
        self.code = code


class UnknownMeasureError(DomainError):
    def __init__(self, measure_id: str) -> None:
        super().__init__(f"Mesure inconnue : « {measure_id} »")
        self.measure_id = measure_id


class UnknownVariantError(DomainError):
    def __init__(self, measure_id: str, variant_id: str) -> None:
        super().__init__(f"Variante inconnue « {variant_id} » pour la mesure « {measure_id} »")
        self.measure_id = measure_id
        self.variant_id = variant_id


class InvalidPriceError(DomainError):
    def __init__(self, price: float, minimum: float) -> None:
        super().__init__(
            f"Prix de départ {price:.3f} €/L trop bas : il doit dépasser l'accise TTC "
            f"({minimum:.3f} €/L)"
        )
        self.price = price
        self.minimum = minimum
