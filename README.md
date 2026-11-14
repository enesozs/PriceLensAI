# PriceLens AI
### Inflation, purchasing-power, and cost-of-living intelligence

**Status: M2 complete — the Inflation Atlas runs locally as a static site (not deployed).** PriceLens AI is a proposed visual and analytical platform for understanding **what is getting more expensive, for whom, in which places, and with what uncertainty**. It combines official inflation indices, expenditure weights, official household-survey spending structures, reproducible forecasting, and transparent household-basket simulations.

> **Core idea:** Inflation is reported as one headline percentage, but people buy different things. PriceLens helps users explore category-level price movements and understand how different spending weights — official income-quintile weights or a user's own illustrative basket — change the inflation that basket experiences.

## The experience

A visitor opens an inflation atlas, chooses a country or the euro area, and examines food, housing, transport, energy and other price-index histories. They can see which components drive the headline rate, compare inflation for the lowest- and highest-income households using official survey weights, review ML forecasts with uncertainty, or enter an anonymous hypothetical monthly spending basket to compute a **custom basket price index**, not an official household CPI.

For example, a hypothetical household spends 40% on rent, 25% on food, 15% on transport and 20% elsewhere. PriceLens reweights **published category indices** relative to a declared base period and shows how that basket's price level changes over time. If the spending categories are not comparable to the HICP classification, the app refuses or requires an explicit mapping disclaimer. The basket is computed in the browser; it never leaves the user's device.

## Main modules

- **Inflation Atlas:** headline and category inflation for all EU countries and the euro area: contribution charts, category heatstrips, country rankings and a map; units, index base and publication date always visible.
- **Basket Studio:** sliders or amounts for user-defined category weights; fixed-base and annually-chained modes; transparent formula; comparison to the official aggregate. Includes **scenarios** (an explicit assumed path for a category, labelled hypothetical).
- **Quintile Lab:** inflation experienced by each income quintile, using **official Eurostat Household Budget Survey expenditure structures**, with wave, coverage and classification-mapping caveats shown.
- **Forecast Laboratory:** 1- and 3-month category forecasts with rolling backtests and empirical intervals, benchmarked against naïve baselines **and published official/professional forecasts**.
- **Research Workbench:** documented datasets, model comparisons, evaluation reports, exportable charts and, eventually, a tool-grounded LLM analyst.

## Data and scope

**Market: EU27 + euro area.** All countries and aggregates are ingested (it costs the same); forecasting starts with a smaller set (e.g. euro area, DE, FR, IT, ES), frozen at M0.

Core (Eurostat, CC BY 4.0 — attribution, note modifications, no-endorsement disclaimer):
- [Eurostat HICP portal](https://ec.europa.eu/eurostat/web/hicp) — official indices, methodology, classifications.
- Monthly indices and rates: **`prc_hicp_minr`** (ECOICOP ver. 2). The older ECOICOP datasets (`prc_hicp_midx`, `prc_hicp_manr`, `prc_hicp_mmor`) are treated as legacy and used only for a documented bridge; M0 confirms their status.
- Annual item weights: **`prc_hicp_iw`** (ECOICOP ver. 2, per 1000). `prc_hicp_inw` (1996–2025) is discontinued.
- Household Budget Survey expenditure structure by income quintile: `hbs_str_t223` (2015 and 2020 waves).
- Since January 2026 data, the HICP uses **ECOICOP ver. 2 (= COICOP 2018, 13 divisions)** with index reference period **2025=100**. Eurostat also publishes 2015=100 for continuity.

Candidate extensions, each requiring a licence check before use:
- Forecast features: EU Weekly Oil Bulletin (fuel prices), EIA Brent price, ECB Data Portal exchange rates.
- Forecast benchmarks: the Eurostat flash estimate, ECB/Eurosystem staff projections and the ECB Survey of Professional Forecasters.
- Late, optional US extension: [BLS CPI](https://www.bls.gov/cpi/) with relative-importance weights. It uses a different methodology and is never mixed with HICP.

## Scientific boundaries

- Price indices track *relative price change*, not a directly observed current euro cost of every item in a household's cart.
- **HICP excludes owner-occupied housing costs and mortgage interest.** Housing (division 04) covers actual rents, maintenance, water and household energy. A homeowner's "housing spending" is not what the HICP measures.
- Different baskets produce custom comparisons, **not official inflation statistics**.
- Item weights change across years. A fixed basket and an annually reweighted, chain-linked official index answer different questions; do not equate their methodologies.
- Income-quintile weights are survey averages for a group, not any real household.
- Forecasted inflation does not establish its causes. SHAP or feature importance describe predictive associations, not causal contributions.
- A hypothetical energy-price shock is a scenario, not a verified policy counterfactual.

## Proposed technical stack

**Static-first.** HICP updates once a month, so the pipeline exports compact versioned JSON/Parquet and a static site reads them. A server is added only when a feature needs on-demand compute.

- **Pipeline:** Python 3.12, uv, Polars + DuckDB, Parquet, Pydantic, pytest, ruff. Direct Eurostat API requests, with raw snapshots and a source manifest.
- **Models:** statsmodels (ETS/SARIMA), scikit-learn (Ridge/ElasticNet), LightGBM; empirical or conformal intervals; a simple run ledger instead of MLflow.
- **Frontend:** Vite + React + TypeScript, Tailwind v4, Base UI, Observable Plot + D3, DuckDB-WASM for in-browser basket and quintile computations.
- **Delivery:** GitHub Actions (CI, plus a monthly refresh after each Eurostat release) and static hosting.

## Roadmap

| Milestone | Outcome |
|---|---|
| M0 | Source, weights, classification and licence feasibility audit |
| M1 | Versioned EU27 + euro-area inflation warehouse, with official-HICP reconstruction QA |
| M2 | Polished Inflation Atlas — first MVP |
| M3 | Basket Studio + Quintile Lab + scenarios, with verified index math |
| M4 | Forecast Lab with robust backtests and official benchmarks |
| M5 | Hardening: CI, monthly refresh, docs, release |
| M6–M8 | Advanced/hierarchical ML, tool-grounded LLM analyst, optional US extension |

See [`docs/DATA_CONTRACT.md`](docs/DATA_CONTRACT.md) for the data contract.

## Installation and demo status

**M0 (source audit), M1 (warehouse) and M2 (Inflation Atlas) complete.** Nothing is deployed. What works:

```bash
uv sync                      # Python 3.12 environment
uv run pricelens fetch       # Eurostat bulk snapshots -> data/raw/ (+ manifest with sha256 and licence)
uv run pricelens audit       # M0 coverage / flags / weights / HBS report -> reports/m0_source_audit.md
uv run pricelens curate      # normalized Parquet tables -> data/curated/
uv run pricelens qa          # data-contract checks + official-HICP reconstruction -> reports/m1_qa.md
uv run pricelens export      # compact JSON for the site -> app/public/data (committed)
uv run pytest                # unit tests (connector, chain-linking, contributions, HBS bridge)

cd app && npm install && npm run dev     # the site at http://127.0.0.1:5174
npm run build                            # static build -> app/dist
```

The Atlas covers the 27 EU countries, the euro area and the EU. It has:
- the headline rate, with the flash estimate when one exists;
- contributions of energy, food, goods and services;
- a 3-year category heatstrip;
- a country ranking and a map;
- 13-category small multiples against the euro area.

Light and dark themes, phone layouts and table views are included.

The official all-items HICP is reproduced from published division indices and weights within a 95th-percentile annual-rate gap of 0.014–0.031 pp for 28 of 29 geos. Italy is a documented exception; see [`reports/m1_qa.md`](reports/m1_qa.md).


## Data attribution

Source: Eurostat (HICP, Household Budget Survey). PriceLens transforms and recombines these data; Eurostat bears no responsibility for the results. Map boundaries use public-domain or permissively licensed data (Natural Earth / world-atlas), not GISCO.

## What a finished portfolio release demonstrates

A technically defensible economic dataset and data lineage; correct basket index math validated by reconstructing the official index; official distributional inflation; no-lookahead forecasting measured against professional forecasts; uncertainty and explanation; a polished visual product; automated tests and monthly refresh; transparent assumptions and limitations. The project's ambition is high, but each milestone should stand alone.
