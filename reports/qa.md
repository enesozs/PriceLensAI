# Data quality report (generated)

Generated 2026-11-21T12:48:28+00:00 by `uv run pricelens qa`. Source versions: 2026-10-16T23:00:00+0200, 2026-11-04T11:00:00+0100.

**Overall: PASS**

| name | status | detail |
|---|---|---|
| unique key hicp_index | PASS | 0 duplicate keys |
| positive index values (total, divisions, aggregates) | PASS | 0 negative, 0 zero at core levels |
| zero indices at detailed levels | WARN | 762 published 0.00 values (items made free or rounded to zero) in ['BE', 'BG', 'EE', 'IE', 'RO']; never used as basket components |
| no null values with flags in index | WARN | 8 rows (e.g. confidential) |
| all warehouse geos present | PASS | missing: [] |
| division weights sum to 1000 | PASS | 892 geo-years; 0 outside ±0.05; 0 with <13 divisions |
| forecast scope continuous 2001→latest | PASS | 90 series; 0 with gaps (expected 310 months) |
| YoY from I25 matches published RCH_A | PASS | max |gap| 0.050 pp over 10283 geo-months (RCH_A has 1 decimal) |
| official HICP reconstruction (forecast geos) | WARN | p95 ≤ 0.1 pp and max ≤ 0.3 pp from 2001-01; failing: []; documented exceptions: ['IT'] |
| official HICP reconstruction (all geos) | PASS | failing: []; not reconstructable: [] |
| HBS quintile bridge | PASS | 25 countries usable in ≥1 wave; not usable: ['IT', 'SE'] |

## Official HICP reconstruction

All-items HICP rebuilt from the 13 ECOICOP ver.2 division indices (I25) and PRC_HICP_IW division weights with annual chain-linking through December of the previous year, anchored each year on the published December value (see src/pricelens/reconstruction.py). Gap = reconstructed minus published annual rate, in percentage points. `chain_drift_last_pct` = level drift of the fully chained (never re-anchored) reconstruction at the latest month.

Gate: per geo, 95th percentile |gap| ≤ 0.1 pp and max |gap| ≤ 0.3 pp from 2001-01. Rationale: published indices have 2 decimals and weights are rounded to 0.01‰, so exact equality is impossible; a correct method should stay within about a tenth of a point, while a wrong link month or wrong weight year produces gaps of several tenths during price shocks.

| geo | months | from | median_abs_pp | p95_abs_pp | max_abs_pp | chain_drift_last_pct | gate |
|---|---|---|---|---|---|---|---|
| AT | 309 | 2001-01 | 0.006 | 0.016 | 0.032 | 0.000 | PASS |
| BE | 309 | 2001-01 | 0.007 | 0.022 | 0.032 | -0.001 | PASS |
| BG | 309 | 2001-01 | 0.007 | 0.025 | 0.036 | -0.002 | PASS |
| CY | 309 | 2001-01 | 0.006 | 0.018 | 0.025 | -0.003 | PASS |
| CZ | 309 | 2001-01 | 0.006 | 0.022 | 0.032 | -0.005 | PASS |
| DE | 309 | 2001-01 | 0.006 | 0.018 | 0.022 | 0.002 | PASS |
| DK | 309 | 2001-01 | 0.005 | 0.015 | 0.020 | -0.015 | PASS |
| EA | 309 | 2001-01 | 0.007 | 0.021 | 0.037 | 0.004 | PASS |
| EE | 309 | 2001-01 | 0.006 | 0.023 | 0.033 | -0.010 | PASS |
| EL | 309 | 2001-01 | 0.005 | 0.017 | 0.031 | 0.005 | PASS |
| ES | 309 | 2001-01 | 0.005 | 0.015 | 0.027 | -0.000 | PASS |
| EU27_2020 | 309 | 2001-01 | 0.005 | 0.015 | 0.025 | 0.007 | PASS |
| FI | 309 | 2001-01 | 0.007 | 0.020 | 0.030 | -0.012 | PASS |
| FR | 309 | 2001-01 | 0.005 | 0.014 | 0.022 | 0.003 | PASS |
| HR | 309 | 2001-01 | 0.007 | 0.018 | 0.036 | 0.010 | PASS |
| HU | 309 | 2001-01 | 0.008 | 0.027 | 0.036 | -0.003 | PASS |
| IE | 309 | 2001-01 | 0.007 | 0.019 | 0.029 | 0.002 | PASS |
| IT | 309 | 2001-01 | 0.057 | 0.166 | 0.296 | -0.152 | FAIL |
| LT | 309 | 2001-01 | 0.007 | 0.021 | 0.044 | 0.013 | PASS |
| LU | 309 | 2001-01 | 0.005 | 0.016 | 0.027 | 0.010 | PASS |
| LV | 309 | 2001-01 | 0.007 | 0.026 | 0.045 | -0.018 | PASS |
| MT | 309 | 2001-01 | 0.005 | 0.017 | 0.025 | -0.003 | PASS |
| NL | 309 | 2001-01 | 0.007 | 0.020 | 0.031 | -0.009 | PASS |
| PL | 309 | 2001-01 | 0.006 | 0.021 | 0.030 | -0.000 | PASS |
| PT | 309 | 2001-01 | 0.005 | 0.014 | 0.020 | -0.004 | PASS |
| RO | 297 | 2002-01 | 0.008 | 0.031 | 0.056 | 0.011 | PASS |
| SE | 309 | 2001-01 | 0.005 | 0.015 | 0.025 | 0.011 | PASS |
| SI | 309 | 2001-01 | 0.006 | 0.019 | 0.029 | -0.013 | PASS |
| SK | 309 | 2001-01 | 0.007 | 0.024 | 0.033 | -0.006 | PASS |

### Documented exceptions

- **IT**: Gap persists in every year (p95 ≈ 0.17 pp), December levels match (≈0.00%) while other months deviate ≈0.05%; price-updating the weights makes it worse (rejected). Consistent with intra-year varying weights in the Italian HICP (e.g. seasonal items) — not verified against ISTAT documentation. Italian published series are used as-is; custom baskets for IT carry a caveat.

### Hypothesis test: are the published weights already price-updated to December?

Same reconstruction with weights re-valued from average y-1 prices to December y-1. If published weights were *not* price-updated, this variant would shrink the gaps. It widens them everywhere, so the published weights are used as-is.

| geo | p95_abs_pp | p95_abs_pp_price_updated |
|---|---|---|
| AT | 0.016 | 0.038 |
| BE | 0.022 | 0.166 |
| BG | 0.025 | 0.121 |
| CY | 0.018 | 0.096 |
| CZ | 0.022 | 0.125 |
| DE | 0.018 | 0.043 |
| DK | 0.015 | 0.038 |
| EA | 0.021 | 0.038 |
| EE | 0.023 | 0.263 |
| EL | 0.017 | 0.101 |
| ES | 0.015 | 0.110 |
| EU27_2020 | 0.015 | 0.031 |
| FI | 0.020 | 0.031 |
| FR | 0.014 | 0.022 |
| HR | 0.018 | 0.045 |
| HU | 0.027 | 0.103 |
| IE | 0.019 | 0.067 |
| IT | 0.166 | 0.499 |
| LT | 0.021 | 0.212 |
| LU | 0.016 | 0.058 |
| LV | 0.026 | 0.279 |
| MT | 0.017 | 0.170 |
| NL | 0.020 | 0.127 |
| PL | 0.021 | 0.041 |
| PT | 0.014 | 0.051 |
| RO | 0.031 | 0.155 |
| SE | 0.015 | 0.237 |
| SI | 0.019 | 0.151 |
| SK | 0.024 | 0.081 |

Largest single-month gaps:

| geo | month | yoy_pub | yoy_rec | gap_pp |
|---|---|---|---|---|
| IT | 2003-03 | 3.060 | 2.763 | -0.296 |
| IT | 2002-12 | 2.913 | 3.185 | 0.273 |
| IT | 2008-10 | 3.516 | 3.708 | 0.192 |
| IT | 2001-12 | 2.318 | 2.126 | -0.192 |
| IT | 2006-11 | 1.906 | 2.096 | 0.190 |
| IT | 2015-04 | 0.000 | -0.188 | -0.188 |
| IT | 2002-03 | 2.475 | 2.663 | 0.187 |
| IT | 2003-10 | 2.844 | 2.664 | -0.180 |
| IT | 2015-01 | -0.379 | -0.557 | -0.178 |
| IT | 2001-07 | 2.508 | 2.330 | -0.178 |

## HBS quintile bridge usability (per geo × wave)

| geo | wave | usable | method | missing |
|---|---|---|---|---|
| AT | 2015 | True | bridge+cp091_fallback |  |
| AT | 2020 | True | bridge+cp091_fallback |  |
| BE | 2015 | True | bridge+cp091_fallback |  |
| BE | 2020 | True | bridge+cp091_fallback |  |
| BG | 2015 | True | bridge+cp091_fallback |  |
| BG | 2020 | True | bridge+cp091_fallback |  |
| CY | 2015 | True | bridge+cp091_fallback |  |
| CY | 2020 | True | bridge+cp091_fallback |  |
| CZ | 2015 | True | bridge+cp091_fallback |  |
| DE | 2015 | True | bridge+cp091_fallback |  |
| DE | 2020 | True | bridge+cp091_fallback |  |
| DK | 2015 | True | bridge+cp091_fallback |  |
| DK | 2020 | True | bridge+cp091_fallback |  |
| EE | 2015 | True | bridge+cp091_fallback |  |
| EE | 2020 | True | bridge+cp091_fallback |  |
| EL | 2015 | True | bridge+cp091_fallback |  |
| EL | 2020 | True | bridge+cp091_fallback |  |
| ES | 2015 | True | bridge+cp091_fallback |  |
| ES | 2020 | True | bridge+cp091_fallback |  |
| EU27_2020 | 2015 | False | bridge | CP042,CP081,CP125,CP126 |
| EU27_2020 | 2020 | False | bridge | CP042,CP081,CP125,CP126 |
| FI | 2015 | True | bridge+cp091_fallback |  |
| FI | 2020 | True | bridge+cp091_fallback |  |
| FR | 2015 | True | bridge+cp091_fallback |  |
| FR | 2020 | True | bridge+cp091_fallback |  |
| HR | 2015 | True | bridge+cp091_fallback |  |
| HR | 2020 | True | bridge+cp091_fallback |  |
| HU | 2015 | True | bridge+cp091_fallback |  |
| HU | 2020 | True | bridge+cp091_fallback |  |
| IE | 2015 | True | bridge+cp091_fallback |  |
| IE | 2020 | True | bridge+cp091_fallback |  |
| LT | 2015 | True | bridge+cp091_fallback |  |
| LT | 2020 | True | bridge+cp091_fallback |  |
| LU | 2015 | True | bridge+cp091_fallback |  |
| LU | 2020 | True | bridge+cp091_fallback |  |
| LV | 2015 | True | bridge+cp091_fallback |  |
| LV | 2020 | True | bridge+cp091_fallback |  |
| MT | 2015 | True | bridge+cp091_fallback |  |
| MT | 2020 | True | bridge+cp091_fallback |  |
| NL | 2015 | True | bridge+cp091_fallback |  |
| NL | 2020 | True | bridge+cp091_fallback |  |
| PL | 2015 | True | bridge+cp091_fallback |  |
| PL | 2020 | True | bridge+cp091_fallback |  |
| PT | 2015 | True | bridge+cp091_fallback |  |
| PT | 2020 | False | bridge | CP042,CP081,CP125,CP126 |
| RO | 2015 | True | bridge+cp091_fallback |  |
| RO | 2020 | False | bridge | CP042,CP081,CP125,CP126 |
| SE | 2015 | False | bridge+cp091_fallback |  |
| SI | 2015 | True | bridge+cp091_fallback |  |
| SI | 2020 | True | bridge+cp091_fallback |  |
| SK | 2015 | True | bridge+cp091_fallback |  |
| SK | 2020 | True | bridge+cp091_fallback |  |

## Table fingerprints

- `hicp_weights`: `1613c00874befc27`
- `coicop`: `559b2ede75ed6834`
- `hbs_quintile`: `b802de64a159a42b`
- `hicp_index_I25_total`: `9f986fbc9a46c543`
