/*
 * Moteur de calcul « Le litre sans… » — portage exact de app/domain/simulator.py.
 * Aucune dépendance. Utilisable dans le navigateur (globalThis.LitreSans) et depuis Node (require).
 * Les clés du résultat sont celles de SimulationResult (snake_case) pour rester interchangeables.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.LitreSans = factory();
  }
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const CAP_EPSILON_BN = 0.005; // en dessous de 5 M€, on ne parle pas de plafond

  class DomainError extends Error {}
  class UnknownFuelError extends DomainError {
    constructor(code) { super(`Carburant inconnu : « ${code} »`); this.code = code; }
  }
  class UnknownMeasureError extends DomainError {
    constructor(id) { super(`Mesure inconnue : « ${id} »`); this.measureId = id; }
  }
  class UnknownVariantError extends DomainError {
    constructor(measureId, variantId) {
      super(`Variante inconnue « ${variantId} » pour la mesure « ${measureId} »`);
      this.measureId = measureId; this.variantId = variantId;
    }
  }
  class InvalidPriceError extends DomainError {
    constructor(price, minimum) {
      super(`Prix de départ ${price.toFixed(3)} €/L trop bas : il doit dépasser l'accise TTC (${minimum.toFixed(3)} €/L)`);
      this.price = price; this.minimum = minimum;
    }
  }

  class Catalog {
    /** @param {{fuels: Array, measures: Array}} data — format de site/data/measures.json */
    constructor(data) {
      this.fuels = data.fuels;
      this.measures = data.measures;
      this._fuels = new Map(this.fuels.map((f) => [f.code, f]));
      this._measures = new Map(this.measures.map((m) => [m.id, m]));
    }
    fuel(code) {
      const f = this._fuels.get(code);
      if (!f) throw new UnknownFuelError(code);
      return f;
    }
    measure(id) {
      const m = this._measures.get(id);
      if (!m) throw new UnknownMeasureError(id);
      return m;
    }
    static defaultVariant(measure) {
      return measure.variants.find((v) => v.is_default) || measure.variants[0];
    }
    static variant(measure, variantId) {
      if (variantId === null || variantId === undefined) return Catalog.defaultVariant(measure);
      const v = measure.variants.find((x) => x.id === variantId);
      if (!v) throw new UnknownVariantError(measure.id, variantId);
      return v;
    }
  }

  class Simulator {
    /**
     * @param {Catalog|object} catalog
     * @param {{litresBillions: number, vatRate: number, tankLitres?: number}} params
     */
    constructor(catalog, { litresBillions, vatRate, tankLitres = 50 }) {
      if (!(litresBillions > 0)) throw new RangeError("litresBillions doit être strictement positif");
      if (!(vatRate >= 0 && vatRate < 1)) throw new RangeError("vatRate doit être compris entre 0 et 1");
      this.catalog = catalog instanceof Catalog ? catalog : new Catalog(catalog);
      this.litresBillions = litresBillions;
      this.vatRate = vatRate;
      this.tankLitres = tankLitres;
    }

    /** Baisse du prix en €/L attribuable à une variante, hors plafond. */
    unitEffect(measure, variant) {
      return (variant.direct_per_litre || 0) + (variant.budget_bn || 0) / this.litresBillions;
    }

    /** Prix de départ minimal : l'accise TTC. */
    minimumPrice(fuelCode) {
      return this.catalog.fuel(fuelCode).excise * (1 + this.vatRate);
    }

    /**
     * @param {{fuel: string, start_price?: number|null, selections?: Array<{measure_id: string, variant_id?: string|null}>}} scenario
     */
    simulate(scenario) {
      const fuel = this.catalog.fuel(scenario.fuel);
      const price = scenario.start_price === null || scenario.start_price === undefined
        ? fuel.reference_price
        : scenario.start_price;
      const minimum = this.minimumPrice(fuel.code);
      if (!(price > minimum)) throw new InvalidPriceError(price, minimum);

      const vatFactor = 1 + this.vatRate;
      let directTotal = 0;
      let budgetTotalBn = 0;
      for (const sel of scenario.selections || []) {
        const measure = this.catalog.measure(sel.measure_id);
        const variant = Catalog.variant(measure, sel.variant_id);
        directTotal += variant.direct_per_litre || 0;
        budgetTotalBn += variant.budget_bn || 0;
      }

      // 1-2. Hors taxes, avant puis après les mesures « direct ».
      const htBase = Math.max(0, price / vatFactor - fuel.excise);
      const ht = Math.max(0, htBase - directTotal / vatFactor);

      // 3. Taxes = accise + TVA sur (HT + accise).
      const vat = this.vatRate * (ht + fuel.excise);
      const taxes = fuel.excise + vat;

      // 4-5. Baisse budgétaire par litre, plafonnée aux taxes.
      const budgetCut = budgetTotalBn / this.litresBillions;
      const effectiveCut = Math.min(taxes, budgetCut);

      // 6. Prorata entre accise et TVA.
      const keepRatio = taxes > 0 ? (taxes - effectiveCut) / taxes : 0;
      const exciseAfter = fuel.excise * keepRatio;
      const vatAfter = vat * keepRatio;

      // 7-8. Prix final et économies sans effet.
      const priceAfter = ht + taxes - effectiveCut;
      const unusedBn = Math.max(0, budgetCut - taxes) * this.litresBillions;
      const cut = price - priceAfter;

      return {
        fuel: fuel.code,
        price_before: price,
        breakdown_after: { ht, excise: exciseAfter, vat: vatAfter, total: priceAfter },
        cut_per_litre: cut,
        budget_savings_bn: budgetTotalBn,
        unused_savings_bn: unusedBn,
        cap_reached: unusedBn > CAP_EPSILON_BN,
        tank_saving: cut * this.tankLitres,
        tank_litres: this.tankLitres,
      };
    }
  }

  return {
    Catalog,
    Simulator,
    DomainError,
    UnknownFuelError,
    UnknownMeasureError,
    UnknownVariantError,
    InvalidPriceError,
    CAP_EPSILON_BN,
  };
});
