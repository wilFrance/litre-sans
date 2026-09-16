// Parité engine.js ↔ moteur Python : `node --test "tests/js/**/*.test.js"`
// Prérequis : `uv run pytest tests/test_parity_export.py` a produit tests/fixtures/cases.json.
"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..", "..");
const ENGINE_PATH = path.join(ROOT, "litre_sans", "static", "js", "engine.js");
const FIXTURE_PATH = path.join(ROOT, "tests", "fixtures", "cases.json");

const LitreSans = require(ENGINE_PATH);
const fixture = JSON.parse(fs.readFileSync(FIXTURE_PATH, "utf8"));
const TOL = 0.001;

const simulator = new LitreSans.Simulator(fixture.catalog, {
  litresBillions: fixture.params.litres_billions,
  vatRate: fixture.params.vat_rate,
  tankLitres: fixture.params.tank_litres,
});

test("la fixture contient des cas", () => {
  assert.ok(fixture.cases.length > 40);
});

for (const c of fixture.cases) {
  test(`parité : ${c.label}`, () => {
    const r = simulator.simulate(c.scenario);
    const e = c.expected;
    const close = (a, b, what) =>
      assert.ok(Math.abs(a - b) < TOL, `${what} : JS ${a} ≠ Python ${b}`);
    assert.equal(r.fuel, e.fuel);
    close(r.price_before, e.price_before, "price_before");
    close(r.breakdown_after.total, e.breakdown_after.total, "total");
    close(r.breakdown_after.ht, e.breakdown_after.ht, "ht");
    close(r.breakdown_after.excise, e.breakdown_after.excise, "excise");
    close(r.breakdown_after.vat, e.breakdown_after.vat, "vat");
    close(r.cut_per_litre, e.cut_per_litre, "cut_per_litre");
    close(r.budget_savings_bn, e.budget_savings_bn, "budget_savings_bn");
    close(r.unused_savings_bn, e.unused_savings_bn, "unused_savings_bn");
    close(r.tank_saving, e.tank_saving, "tank_saving");
    assert.equal(r.cap_reached, e.cap_reached, "cap_reached");
  });
}

for (const c of fixture.errors) {
  test(`erreur : ${c.label}`, () => {
    assert.throws(() => simulator.simulate(c.scenario), LitreSans[c.error]);
  });
}

test("le moteur du site généré est identique au source", { skip: !fs.existsSync(path.join(ROOT, "site")) }, () => {
  const built = fs.readFileSync(path.join(ROOT, "site", "static", "js", "engine.js"), "utf8");
  assert.equal(built, fs.readFileSync(ENGINE_PATH, "utf8"));
});
