# PriceLens AI — Data Contract

## Source and grain

**Indices** (`prc_hicp_minr`):
- **Grain:** one observation per `(geo, coicop_code, time_month, index_reference_base, unit, classification_version, snapshot_version)`.
- **Fields:** `index_value`, status flags and source metadata.
- **Bases:** store both 2025=100 and 2015=100 where published.
- **Classification:** `classification_version` is `ecoicop_v2` for current data. A legacy `ecoicop_v1` bridge is used only when explicitly documented.

**Weights** (`prc_hicp_iw`):
- **Grain:** one observation per `(geo, coicop_code, calendar_year, classification_version)`.
- **Fields:** `item_weight_per_1000` and metadata.
- **Legacy:** the discontinued `prc_hicp_inw` is used only as an explicitly documented historical bridge.

**Quintile weights** (`hbs_str_t223`):
- **Grain:** one observation per `(geo, income_quintile, coicop1999_code, survey_wave)`.
- **Fields:** `share_per_1000` (raw). Mapped, curated table `hbs_quintile`: ver. 2 `division`, `share` (renormalized ex. imputed rent), `method` and diagnostics.
- **Bridge:** `configs/hbs_to_ecoicop2.csv`. Start from the 12 division totals, then remove CP042 and apply moves and weight-proportional splits.
  - Eurostat publishes no 4-digit CP091 detail, so the old CP091 part that moves to ver. 2 CP08 is split using the country's ver. 2 class weights (`bridge+cp091_fallback`).
- **Usable geo-wave:** all required codes present, and the HBS division total within 1000 ± 6‰ (integer rounding). SE and IT are not usable.
- **Flags:** note waves that were imputed or price-converted (for example the 2020 figures for CY, FR and MT) and countries with no data.

**Mappings:**
- The ECOICOP ver. 2 hierarchy and labels.
- An ECOICOP v1 → v2 bridge.
- A COICOP 1999 → ECOICOP v2 bridge at division level.

Never double count parent and child categories. Handle rebasing and classification changes explicitly.

**Source manifest:** one row per fetched file, recording:
- URL, request parameters and retrieval timestamp;
- content hash and row count;
- licence identifier.

## Basket formulas

All baskets require disjoint, exhaustive categories at one hierarchy level. Reject negative or invalid weights. Either require coverage that sums to 1, or renormalize explicitly and show a notice.

- **Fixed-base:** `100 * sum_i(w_i * I_{i,t}/I_{i,b})`, with output type `custom_fixed_basket`.
- **Chained annual:** for months `t` in year `y`, compute the link `L_t = sum_i(w_{i,y} * I_{i,t}/I_{i,Dec(y-1)})` and chain the links (see src/pricelens/reconstruction.py). The output type is `custom_chained_basket`, or `hbs_quintile_basket` when the weights come from the HBS.

Every result returns:
- the formula and mode;
- the base or link months;
- coverage and the weight source;
- the type label.

Baskets are computed client-side, and user baskets are never persisted server-side.

## Quality and reproducibility

**Per-source checks:**
- positive index values and a unique key;
- required base-month coverage and index-base metadata;
- weight sums of 1000 per country and year at the chosen level;
- country and category coverage;
- flag handling and snapshot versioning;
- no accidental mixing of HICP and CPI;
- byte-identical rebuilds from the same snapshot.

**Reconstruction gate:** rebuild the all-items HICP from division indices and weights using the chained formula. Report the annual-rate gap in percentage points by country and year.

**Tolerance (fixed at M1):** from 2001-01, per geo, the 95th percentile of |gap| must be ≤ 0.10 pp and the maximum ≤ 0.30 pp.

**M1 result:** 28 of 29 geos pass, with 95th-percentile gaps of 0.014–0.031 pp. Italy is a documented source-side exception (`pricelens.qa.KNOWN_EXCEPTIONS`; evidence in `reports/m1_qa.md`). Any new exception requires diagnostic evidence in the report.

**Rebase check:** the 2025=100 and 2015=100 series must give the same rates within rounding.

## Forecast policy

- Never train on future months, and never claim operational historical forecasting from data that would not have been available at the time.
- Every forecast carries `issued_at`, `target_month`, `observed_release_cutoff`, `source_version`, `model_id` and fold provenance.
- Benchmarks (flash, ECB staff projections, SPF) are stored with their own publication dates and are compared only at matching horizon and aggregate.
- Missing values are never silently forward-filled as actual HICP values.

## Labeling

Always distinguish these measure types; they are not interchangeable:
- `official_observed`
- `official_flash`
- `custom_fixed_basket`
- `custom_chained_basket`
- `hbs_quintile_basket`
- `model_forecast`
- `benchmark_forecast`
- `hypothetical_scenario`

## Licence record

Every source has a licence record before first use. Each record covers:
- the licence;
- attribution text;
- modification notice;
- commercial use and redistribution terms;
- automated-access terms;
- derived-data rules.
