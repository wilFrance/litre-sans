// analytics.js : jamais bloquant, anti-rebond de 2 s par événement.
"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");

const { Analytics } = require(path.resolve(__dirname, "..", "..", "litre_sans", "static", "js", "analytics.js"));

test("sans GoatCounter chargé : ne fait rien et ne lève pas d'erreur", () => {
  delete globalThis.goatcounter;
  const a = new Analytics();
  assert.equal(a.ready, false);
  assert.equal(a.track("mesure-cochee-ame"), false);
});

test("avec GoatCounter : envoie l'événement une fois, puis anti-rebond", () => {
  const sent = [];
  globalThis.goatcounter = { count: (p) => sent.push(p) };
  const a = new Analytics({ minIntervalMs: 2000 });
  assert.equal(a.track("mesure-cochee-ame"), true);
  assert.equal(a.track("mesure-cochee-ame"), false); // < 2 s
  assert.equal(a.track("partage-x"), true); // autre nom : passe
  assert.deepEqual(sent, [
    { path: "mesure-cochee-ame", event: true },
    { path: "partage-x", event: true },
  ]);
  a.lastSent.set("mesure-cochee-ame", Date.now() - 2001);
  assert.equal(a.track("mesure-cochee-ame"), true);
  delete globalThis.goatcounter;
});

test("une erreur du script tiers est avalée", () => {
  globalThis.goatcounter = { count: () => { throw new Error("boom"); } };
  const a = new Analytics();
  assert.equal(a.track("scenario-charge"), false);
  delete globalThis.goatcounter;
});
