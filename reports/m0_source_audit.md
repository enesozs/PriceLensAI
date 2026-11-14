# M0 source audit (generated)

Generated 2026-11-14T18:25:17+00:00 by `uv run pricelens audit`.

## PRC_HICP_MINR — snapshot `2026-11-04T110000+0100`

Rows (warehouse geos × units ['I25', 'I15', 'RCH_M', 'RCH_A']): 14,096,076. Codes in codelist: 555.

Published I25 codes by level:

| level | len |
|---|---|
| digits_2 | 13 |
| digits_3 | 50 |
| digits_4 | 141 |
| digits_5 | 291 |
| digits_6 | 11 |
| special_aggregate | 48 |
| total | 1 |

### Coverage of index (2025=100) by geo

| geo | first | last | last_flag | all_13_divisions_from | ecb_4_aggregates_from | forecast_scope |
|---|---|---|---|---|---|---|
| EA | 1996-01 | 2026-10 | e | 1996-01 | 1999-12 | True |
| EU27_2020 | 1999-12 | 2026-09 |  | 1999-12 | 1999-12 | False |
| BE | 1996-01 | 2026-10 | e | 1999-12 | 1998-12 | False |
| BG | 1996-12 | 2026-10 | e | 1999-12 | 1996-12 | False |
| CZ | 1996-01 | 2026-09 |  | 1996-01 | 1999-12 | False |
| DK | 1996-01 | 2026-09 |  | 1996-01 | 1999-12 | False |
| DE | 1996-01 | 2026-10 | e | 1996-01 | 1996-01 | True |
| EE | 1996-01 | 2026-10 | e | 1997-12 | 2000-12 | False |
| IE | 1996-01 | 2026-10 | e | 1996-01 | 1999-12 | False |
| EL | 1996-01 | 2026-10 | e | 1996-01 | 1996-01 | False |
| ES | 1996-01 | 2026-10 | e | 1996-01 | 2000-12 | True |
| FR | 1996-01 | 2026-10 | e | 1996-01 | 1996-01 | True |
| HR | 1997-12 | 2026-10 | e | 1997-12 | 1998-01 | False |
| IT | 1996-01 | 2026-10 | e | 1996-01 | 1999-12 | True |
| CY | 1996-01 | 2026-10 | e | 1996-01 | 1996-01 | False |
| LV | 1996-01 | 2026-10 | e | 1996-01 | 1997-12 | False |
| LT | 1996-01 | 2026-10 | e | 1996-01 | 1996-01 | False |
| LU | 1996-01 | 2026-10 | e | 1996-01 | 1999-12 | False |
| HU | 1996-01 | 2026-09 |  | 1996-01 | 2000-12 | False |
| MT | 1996-01 | 2026-10 | e | 1996-01 | 1996-01 | False |
| NL | 1996-01 | 2026-10 | e | 1996-01 | 1999-12 | False |
| AT | 1996-01 | 2026-10 | e | 1996-01 | 1999-12 | False |
| PL | 1996-01 | 2026-09 |  | 1996-01 | 1996-01 | False |
| PT | 1996-01 | 2026-10 | e | 1996-01 | 1999-12 | False |
| RO | 1996-01 | 2026-09 |  | 2000-12 | 2000-12 | False |
| SI | 1996-01 | 2026-10 |  | 1996-01 | 2000-12 | False |
| SK | 1996-12 | 2026-10 | e | 1996-12 | 1996-01 | False |
| FI | 1996-01 | 2026-10 | e | 1996-01 | 1999-12 | False |
| SE | 1996-01 | 2026-09 |  | 1996-01 | 1999-12 | False |

### Observation flags

| unit | flag | len |
|---|---|---|
| I15 |  | 3134263 |
| I15 | b | 1324 |
| I15 | d | 297294 |
| I15 | e | 133481 |
| I15 | u | 2372 |
| I25 |  | 3134273 |
| I25 | b | 1324 |
| I25 | d | 297294 |
| I25 | e | 133691 |
| I25 | u | 2372 |
| RCH_A |  | 2966791 |
| RCH_A | b | 2646 |
| RCH_A | d | 295827 |
| RCH_A | e | 133771 |
| RCH_A | u | 4359 |
| RCH_M |  | 3118901 |
| RCH_M | b | 2646 |
| RCH_M | d | 295959 |
| RCH_M | e | 134237 |
| RCH_M | u | 3251 |

Estimated (`e`) I25 observations by period. The flash estimate for the latest month is published inside this dataset for codes ['FOOD', 'FOOD_NP', 'FOOD_P', 'IGD_NNRG', 'NRG', 'SERV', 'TOTAL', 'TOT_X_NRG', 'TOT_X_NRG_FOOD', 'TOT_X_NRG_FOOD_NP']; the older `e` rows are ECOICOP ver.2 back-calculations.

| period | rows | geos | codes | first | last |
|---|---|---|---|---|---|
| back-calculated history (< 2025-05) | 133481 | ES,FR,MT,PT | 435 | 1996-01 | 2025-04 |
| latest month 2026-10 (flash) | 210 | AT,BE,BG,CY,DE,EA,EE,EL,ES,FI,FR,HR,IE,IT,LT,LU,LV,MT,NL,PT,SK | 10 | 2026-10 | 2026-10 |

### Precision check: all-items YoY recomputed from published indices vs published annual rate

Published rates are computed from unrounded indices. Indices are published with 2 decimals, so low index levels (early years, high-inflation countries) lose precision when rates are recomputed.

| era | months | max_gap_I25 | max_gap_I15 | share_I25_gt_0p05 |
|---|---|---|---|---|
| <2005 | 2692 | 0.05 | 0.813 | 0.0004 |
| >=2005 | 7569 | 0.05 | 0.229 | 0.0001 |

Worst cases:

| geo | time | I25 | RCH_A | yoy25 | gap25 |
|---|---|---|---|---|---|
| SE | 2020-02 | 81.0 | 1.3 | 1.25 | 0.05 |
| CY | 2000-04 | 63.51 | 5.9 | 5.85 | 0.05 |
| CY | 1999-08 | 59.73 | -0.5 | -0.45 | 0.05 |
| EL | 2000-11 | 59.09 | 4.1 | 4.05 | 0.05 |
| ES | 2013-10 | 80.02 | 0.1 | 0.05 | 0.05 |

## PRC_HICP_IW — snapshot `2026-10-16T230000+0200`

Division weights per geo-year: 892 geo-years; n_divisions==13 in 1.000 of them; |sum−1000| max = 0.03, share > 0.05 = 0.000 (rounding of published weights).

| geo | first_year | last_year |
|---|---|---|
| EA | 1996 | 2026 |
| EU27_2020 | 2000 | 2026 |
| BE | 1996 | 2026 |
| BG | 1997 | 2026 |
| CZ | 1996 | 2026 |
| DK | 1996 | 2026 |
| DE | 1996 | 2026 |
| EE | 1996 | 2026 |
| IE | 1996 | 2026 |
| EL | 1996 | 2026 |
| ES | 1996 | 2026 |
| FR | 1996 | 2026 |
| HR | 1998 | 2026 |
| IT | 1996 | 2026 |
| CY | 1996 | 2026 |
| LV | 1996 | 2026 |
| LT | 1996 | 2026 |
| LU | 1996 | 2026 |
| HU | 1996 | 2026 |
| MT | 1996 | 2026 |
| NL | 1996 | 2026 |
| AT | 1996 | 2026 |
| PL | 1996 | 2026 |
| PT | 1996 | 2026 |
| RO | 1996 | 2026 |
| SI | 1996 | 2026 |
| SK | 1996 | 2026 |
| FI | 1996 | 2026 |
| SE | 1996 | 2026 |

### Weight flags

| flag | len |
|---|---|
|  | 339630 |
| d | 24912 |
| e | 9586 |
| m | 3 |

## HBS_STR_T223 — snapshot `2025-10-22T152800+0200`

Complete quintile × 12-division coverage per wave (True = usable):

| geo | 2015 | 2020 |
|---|---|---|
| EU27_2020 | True | True |
| BE | True | True |
| BG | True | True |
| CZ | True |  |
| DK | True | True |
| DE | True | True |
| EE | True | True |
| IE | True | True |
| EL | True | True |
| ES | True | True |
| FR | True | True |
| HR | True | True |
| IT |  |  |
| CY | True | True |
| LV | True | True |
| LT | True | True |
| LU | True | True |
| HU | True | True |
| MT | True | True |
| NL | True | True |
| AT | True | True |
| PL | True | True |
| PT | True | True |
| RO | True | True |
| SI | True | True |
| SK | True | True |
| FI | True | True |
| SE | True |  |

Incomplete geo-waves (diagnosis):

none

Imputed rent (CP042, ‰ of total expenditure) — outside HICP scope, must be removed and the rest renormalised:

| geo | time | QU1 | QU2 | QU3 | QU4 | QU5 |
|---|---|---|---|---|---|---|
| DE | 2015 | 46.0 | 91.0 | 130.0 | 159.0 | 163.0 |
| DE | 2020 | 49.0 | 92.0 | 136.0 | 153.0 | 165.0 |
| ES | 2015 | 197.0 | 218.0 | 218.0 | 206.0 | 207.0 |
| ES | 2020 | 206.0 | 235.0 | 228.0 | 230.0 | 250.0 |
| FR | 2015 | 69.0 | 125.0 | 154.0 | 167.0 | 169.0 |
| FR | 2020 | 69.0 | 125.0 | 154.0 | 167.0 | 169.0 |

CP042 availability (geos with a value) by wave:

| time | geos |
|---|---|
| 1988 | 9 |
| 1994 | 14 |
| 1999 | 16 |
| 2005 | 30 |
| 2010 | 33 |
| 2015 | 34 |
| 2020 | 26 |

### HBS flags

| flag | len |
|---|---|
|  | 45494 |
| e | 1546 |
| u | 1891 |
