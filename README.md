# Le litre sans… — simulateur taxes carburant

Combien coûterait un litre de carburant si l'on supprimait certaines dépenses publiques proposées
par des candidats à la présidentielle 2027 ? Le simulateur consacre **toute** l'économie à baisser
les taxes sur le carburant (accise et TVA), répartie sur les litres vendus en France.

Site statique publié sur GitHub Pages : le calcul tourne dans le navigateur (`engine.js`), sans
serveur. Le moteur Python (`litre_sans/simulator.py`) est la **référence** : `engine.js` en est le
portage exact et la parité est vérifiée automatiquement. Les données sont versionnées et sourcées
dans `data/measures.yaml`, validées à chaque build.

## Prérequis

- [uv](https://docs.astral.sh/uv/) (installe Python 3.12 si besoin)
- Node.js ≥ 22 (tests de parité du moteur JavaScript uniquement)

## Utilisation

```bash
uv sync                                   # première fois
uv run build-site                         # génère site/
uv run python -m http.server -d site 8080 # http://localhost:8080
```

Identique sous Windows (PowerShell). Le site utilise des chemins relatifs : il fonctionne à la
racine d'un domaine comme sous `https://<utilisateur>.github.io/<repo>/`.

```
site/
  index.html                  simulateur
  methode/index.html          méthodologie
  mentions-legales/index.html
  data/measures.json          carburants, mesures, variantes, badges, sources, paramètres
  static/                     css, js (engine.js = moteur, app.js = interface)
  .nojekyll
```

## Vérifications

```bash
uv run ruff check .
uv run pytest                          # moteur, données, générateur ; exporte tests/fixtures/cases.json
node --test "tests/js/**/*.test.js"    # engine.js reproduit les cas Python à 0,001 € près
```

## Déploiement GitHub Pages

1. **Settings → Pages → Build and deployment → Source : GitHub Actions**.
2. Pousser sur `main` : `.github/workflows/pages.yml` enchaîne ruff → pytest → `build-site` →
   tests Node → déploiement de `site/`.

## Configuration

Variables d'environnement optionnelles (préfixe `LITRE_SANS_`, voir `.env.example`) :

| Variable | Défaut | Rôle |
|---|---|---|
| `LITRE_SANS_LITRES_BILLIONS` | `47.5` | Milliards de litres de carburants routiers livrés (2025) |
| `LITRE_SANS_VAT_RATE` | `0.20` | Taux de TVA |
| `LITRE_SANS_TANK_LITRES` | `50` | Volume du plein affiché |
| `LITRE_SANS_MEASURES_PATH` | `data/measures.yaml` | Fichier de données |
| `LITRE_SANS_OUTPUT_DIR` | `site` | Dossier de sortie |

Une erreur dans `measures.yaml` (source manquante, variante sans effet, id dupliqué…) fait
échouer le build avec un message détaillé.

## Méthode de calcul

Voir la page *Méthode*. Avec `L` = litres livrés (Md) et `TVA` = 20 % :

1. `ht_base = prix_départ / (1 + TVA) − accise` (borné à 0)
2. Composantes directes (CEE) : `ht = ht_base − Σ direct_per_litre / (1 + TVA)` (borné à 0)
3. `taxes = accise + TVA × (ht + accise)`
4. Composantes budgétaires : `baisse = Σ budget_bn / L`
5. `baisse_effective = min(taxes, baisse)` — accise **et** TVA ne descendent jamais sous zéro
6. Accise et TVA baissent au prorata de leur part
7. `prix_final = ht + taxes − baisse_effective`
8. `économies_sans_effet = max(0, baisse − taxes) × L`

Le scénario est encodé dans l'URL (`?fuel=gazole&price=2.4&on=energie,fp&fp=y1997`) pour être
partagé.

## Structure

```
litre_sans/
  models.py, errors.py   entités du catalogue
  simulator.py           Scenario, SimulationResult, Simulator (référence)
  catalog.py             chargement et validation du YAML
  export.py              vue JSON du catalogue (pages + measures.json)
  build.py               générateur du site (commande build-site)
  templates/, static/    Jinja2, CSS, engine.js, app.js
data/measures.yaml
tests/                   pytest ; tests/js/ : node --test
.github/workflows/pages.yml
docs/reference/simulateur_carburant.html   prototype d'origine
```

## Évolutions possibles

- Prix moyen du jour depuis les données ouvertes de
  [prix-carburants.gouv.fr](https://www.prix-carburants.gouv.fr/) (prix de la configuration en repli).
- Scénarios préconfigurés par candidat.
