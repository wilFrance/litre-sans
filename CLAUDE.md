# Le litre sans… — repères pour Claude Code

Simulateur public : combien coûterait un litre de carburant si des dépenses publiques proposées
par des candidats à la présidentielle 2027 étaient supprimées et **intégralement** affectées à la
baisse des taxes sur le carburant (accise + TVA). Site statique sur GitHub Pages, sans serveur.

## Architecture (voir README.md pour l'usage)

- `litre_sans/` — package Python 3.12, Pydantic v2, géré avec `uv`.
  - `models.py` : `Fuel`, `Badge`, `Source`, `MeasureVariant` (`budget_bn` Md€/an et/ou
    `direct_per_litre` €/L), `Measure` (liste de `sources`, ≥ 1 variante), `Catalog`.
  - `simulator.py` : `Scenario`, `SimulationResult`, `Simulator` — **moteur de référence**, pur Python.
  - `catalog.py` : chargement/validation de `data/measures.yaml` ; une erreur bloque le build.
  - `export.py` : vue JSON du catalogue (injectée dans les pages, écrite dans `site/data/measures.json`).
  - `build.py` : génère `site/` (commande `uv run build-site`), chemins relatifs (sous-chemin `/<repo>/`).
  - `static/js/engine.js` : **portage exact** du moteur, classe `Simulator`, UMD (navigateur + Node).
  - `static/js/app.js` : interface vanilla, état du scénario dans l'URL, calcul local via `engine.js`.
- `tests/` : pytest (moteur, données, générateur) ; `test_parity_export.py` écrit
  `tests/fixtures/cases.json`, rejoué par `tests/js/engine.test.js` (`node --test`).
- `.github/workflows/pages.yml` : ruff → pytest → build-site → node --test → deploy-pages.

## Règles

- Entités métier = modèles Pydantic gelés, jamais des dicts entre les couches.
- Agnostique de l'OS : `pathlib`, pas de chemin en dur, pas de commande shell dans le code.
- Toute modification du calcul se fait **d'abord** dans `simulator.py`, puis à l'identique dans
  `engine.js` ; la parité est testée.
- Toute mesure a ≥ 1 source (URL https) et ≥ 1 variante ; la première variante est celle par défaut.
- Pas de framework JS, pas de build front. Le site doit rester compact (une page desktop, panneau
  pompe fixé en bas sur mobile) ; les détails (porteur, fiabilité, sources) vivent dans l'infobulle ⓘ.
- Affichage en euros à 2 décimales.

## Calcul (paramètres `LITRES_BILLIONS = 47.5`, `VAT_RATE = 0.20`)

1. `ht_base = prix / (1 + TVA) − accise` (≥ 0) ; 2. `ht = ht_base − Σ direct / (1 + TVA)` (≥ 0) ;
3. `taxes = accise + TVA × (ht + accise)` ; 4. `baisse = Σ budget_bn / L` ;
5. `effective = min(taxes, baisse)` ; 6. accise et TVA au prorata ; 7. `prix = ht + taxes − effective` ;
8. `sans_effet = max(0, baisse − taxes) × L`. Effet unitaire d'une variante : `direct + budget / L`.

Cas de référence (gazole 2,364 €, accise 0,6075 €) : aucune mesure 2,364 · énergie 2,046 ·
agences 2,329 · AME 2,339 · fonction publique (33 Md€) 1,669 · tout coché 1,2375 ± 0,0005 avec
plafond atteint et `unused_savings_bn > 0`.

## Données (`data/measures.yaml`)

8 mesures : `energie` (CEE 0,15 €/L + ENR 7,983 Md€), `agences` (ADEME + ARS + HCSP = 1,664),
`ame` (1,208), `pnc` (9 / 17,5 / 6,1), `apd` (14,827), `av` (4,029), `ville` (7,971),
`fp` (ratio d'agents publics par habitant, hors santé/police/justice : 1995 → 33 Md€ par défaut,
1997 → 24 Md€ ; 50 000 €/agent). Les effectifs 1995 sont une estimation à vérifier.

## Points d'attention

- Le plafond (taxes à zéro) est atteint dès ~46 Md€ : au-delà, décocher une petite mesure ne
  change pas le prix — c'est voulu et affiché dans la pompe.
- Le prototype d'origine est conservé dans `docs/reference/` pour mémoire.
