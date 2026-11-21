# PriceLens AI — Data Contract

## Source and grain

**Indices** (`prc_hicp_minr` → curated table `hicp_index`):
- **Grain:** one observation per `(geo, coicop, date, unit)`, where `unit` is the index reference base (`I25` = 2025=100, `I15` = 2015=100).
- **Fields:** `value`, `flag` (Eurostat observation status), `level` in the classification and `source_version` (Eurostat's data timestamp).
- **Classification:** ECOICOP ver. 2 throughout; Eurostat back-calculates its history to 1996.
- **Rates:** published monthly and annual rates are kept separately (`hicp_rates`) for validation.

**Weights** (`prc_hicp_iw` → `hicp_weights`):
- **Grain:** one observation per `(geo, coicop, year)`.
- **Fields:** `weight_per_1000` (price-updated to December of the previous year), `flag`, `level`, `source_version`.
- The discontinued `prc_hicp_inw` (old classification) is not used.

**Quintile weights** (`hbs_str_t223`):
- **Grain:** one observation per `(geo, income_quintile, coicop1999_code, survey_wave)`.
- **Fields:** `share_per_1000` (raw). Mapped, curated table `hbs_quintile`: ver. 2 `division`, `share` (renormalized ex. imputed rent), `method` and diagnostics.
- **Bridge:** `configs/hbs_to_ecoicop2.csv`. Start from the 12 division totals, then remove CP042 and apply moves and weight-proportional splits.
  - Eurostat publishes no 4-digit CP091 detail, so the old CP091 part that moves to ver. 2 CP08 is split using the country's ver. 2 class weights (`bridge+cp091_fallback`).
- **Usable geo-wave:** all required codes present, and the HBS division total within 1000 ± 6‰ (integer rounding). SE and IT are not usable.
- **Flags:** note waves that were imputed or price-converted (for example the 2020 figures for CY, FR and MT) and countries with no data.

**Mappings:**
- The ECOICOP ver. 2 hierarchy and labels (`coicop`, from Eurostat's codelist).
- A COICOP 1999 → ECOICOP ver. 2 bridge at division level, for the HBS shares.

Never double count parent and child categories. Handle rebasing and classification changes explicitly.

**Source manifest:** one row per fetched file, recording:
- URL (and request parameters for API sources) and retrieval timestamp;
- the source's own data version where it publishes one;
- content hash (SHA-256) and size;
- licence identifier.

## Basket formulas

All baskets require disjoint, exhaustive categories at one hierarchy level. Reject negative or invalid weights. Either require coverage that sums to 1, or renormalize explicitly and show a notice.

- **Fixed-base:** `100 * sum_i(w_i * I_{i,t}/I_{i,b})`, with output type `custom_fixed_basket`.
- **Chained annual:** for months `t` in year `y`, compute the link `L_t = sum_i(w_{i,y} * I_{i,t}/I_{i,Dec(y-1)})` and chain the links. The output type is `custom_chained_basket`, or `hbs_quintile_basket` when the weights come from the HBS.

Every displayed basket result states:
- the method (fixed-base or chained);
- the base month;
- the weight source and any rescaling;
- the measure type.

Baskets are computed client-side, and user baskets are never persisted server-side.

## Quality and reproducibility

**Per-source checks:**
- positive index values and a unique key;
- required base-month coverage and index-base metadata;
- weight sums of 1000 per country and year at the chosen level;
- country and category coverage;
- flag handling and snapshot versioning;
- no accidental mixing of HICP and CPI;
- table fingerprints recorded on every run; a full rebuild from the same snapshots reproduces the forecasts and scores exactly.

**Reconstruction gate:** rebuild the all-items HICP from division indices and weights using the chained formula. Report the annual-rate gap in percentage points by country and year.

**Tolerance:** from 2001-01, per geo, the 95th percentile of |gap| must be ≤ 0.10 pp and the maximum ≤ 0.30 pp.

**Result:** 28 of 29 geos pass, with 95th-percentile gaps of 0.014–0.031 pp. Italy is a documented source-side exception (`pricelens.qa.KNOWN_EXCEPTIONS`; evidence in `reports/qa.md`). Any new exception requires diagnostic evidence in the report.

**Rebase check:** the 2025=100 and 2015=100 series must give the same rates within rounding.

## Forecast policy

- Never train on future months, and never claim operational historical forecasting from data that would not have been available at the time.
- Every forecast is keyed by its origin month and horizon. The run records the information cutoff (`issued_as_of`), the data versions and the chosen model with its tuning results.
- Benchmarks (the Eurostat flash estimate and ECB/Eurosystem staff projections) are compared only at matching target months, horizons and aggregates.
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

Every source has a licence record before first use; the public summary is [DATA_LICENSES.md](../DATA_LICENSES.md). Each record covers:
- the licence;
- attribution text;
- modification notice;
- commercial use and redistribution terms;
- automated-access terms;
- derived-data rules.
