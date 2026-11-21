# Forecast evaluation (generated)

Generated 2026-11-21T12:52:57+00:00 by `uv run pricelens forecast`. Latest origin 2026-10-01, issued as of 2026-11-15. Scores are annual-rate errors of the target month, in percentage points, over the euro area, DE, FR, IT and ES × headline, energy, food, non-energy industrial goods and services.

## Model selection (validation origins 2012–2019 only; h = 1 and 3)

| model | mae |
|---|---|
| Ridge, pooled | 0.598 |
| Ridge + gradient boosting average | 0.601 |
| SARIMA per series | 0.618 |
| Gradient boosting, pooled | 0.646 |
| Seasonal mean, 3 years (floor) | 0.711 |
| Seasonal naïve (floor) | 0.726 |
| No change (floor) | 1.245 |

Chosen model: **Ridge, pooled**. Tuning grids: {"ridge": [{"params": {"alpha": 1.0}, "val_mae": 0.5991}, {"params": {"alpha": 10.0}, "val_mae": 0.5986}, {"params": {"alpha": 100.0}, "val_mae": 0.598}, {"params": {"alpha": 1000.0}, "val_mae": 0.6073}], "gbm": [{"params": {"max_iter": 200, "learning_rate": 0.03, "max_leaf_nodes": 7, "min_samples_leaf": 40}, "val_mae": 0.6461}, {"params": {"max_iter": 400, "learning_rate": 0.03, "max_leaf_nodes": 15, "min_samples_leaf": 40}, "val_mae": 0.6457}, {"params": {"max_iter": 300, "learning_rate": 0.05, "max_leaf_nodes": 7, "min_samples_leaf": 80}, "val_mae": 0.6641}]}

## Test period (origins 2020-01 onward, untouched during tuning)

| model | h | mae | rmse | n |
|---|---|---|---|---|
| Ridge + gradient boosting average | 1 | 0.754 | 1.715 | 2025 |
| Ridge, pooled | 1 | 0.769 | 1.720 | 2025 |
| Gradient boosting, pooled | 1 | 0.794 | 1.774 | 2025 |
| SARIMA per series | 1 | 0.848 | 2.041 | 2025 |
| Seasonal mean, 3 years (floor) | 1 | 0.939 | 2.095 | 2025 |
| Seasonal naïve (floor) | 1 | 1.044 | 2.393 | 2025 |
| No change (floor) | 1 | 1.090 | 2.188 | 2025 |
| Ridge + gradient boosting average | 3 | 1.722 | 3.660 | 1975 |
| Ridge, pooled | 3 | 1.728 | 3.641 | 1975 |
| SARIMA per series | 3 | 1.770 | 3.748 | 1975 |
| Gradient boosting, pooled | 3 | 1.840 | 3.817 | 1975 |
| Seasonal mean, 3 years (floor) | 3 | 2.047 | 4.072 | 1975 |
| Seasonal naïve (floor) | 3 | 2.212 | 4.697 | 1975 |
| No change (floor) | 3 | 2.342 | 4.056 | 1975 |

### By series type

| code | h | ridge | seasonal_mean | no_change |
|---|---|---|---|---|
| FOOD | 1 | 0.410 | 0.499 | 0.516 |
| IGD_NNRG | 1 | 0.505 | 0.459 | 1.281 |
| NRG | 1 | 2.272 | 3.025 | 2.543 |
| SERV | 1 | 0.293 | 0.277 | 0.566 |
| TOTAL | 1 | 0.364 | 0.436 | 0.542 |
| FOOD | 3 | 0.984 | 1.297 | 1.325 |
| IGD_NNRG | 3 | 0.809 | 0.879 | 2.499 |
| NRG | 3 | 5.447 | 6.525 | 5.448 |
| SERV | 3 | 0.531 | 0.547 | 1.224 |
| TOTAL | 3 | 0.868 | 0.987 | 1.213 |

### By period (validation and test)

| period | h | ridge | seasonal_mean |
|---|---|---|---|
| 2012-19 (validation) | 1 | 0.385 | 0.489 |
| 2020-21 pandemic | 1 | 0.610 | 0.738 |
| 2022-23 energy shock | 1 | 1.170 | 1.378 |
| 2024-25 normalisation | 1 | 0.572 | 0.699 |
| 2026 shock | 1 | 0.627 | 0.886 |
| 2012-19 (validation) | 3 | 0.885 | 0.997 |
| 2020-21 pandemic | 3 | 1.291 | 1.608 |
| 2022-23 energy shock | 3 | 2.753 | 2.972 |
| 2024-25 normalisation | 3 | 1.075 | 1.509 |
| 2026 shock | 3 | 1.676 | 1.789 |

### Interval calibration (empirical intervals from the model's own past errors)

Interval method chosen on validation (mean Winkler score of the 80% range, h = 1 and 3; lower is better): **static** — {"static": 3.4923, "adaptive": 3.6589}.

| h | period | cov80 | cov95 | width80 | n |
|---|---|---|---|---|---|
| 1 | 2020-21 pandemic | 0.612 | 0.807 | 0.730 | 575 |
| 1 | 2022-23 energy shock | 0.547 | 0.817 | 1.180 | 600 |
| 1 | 2024-25 normalisation | 0.878 | 0.980 | 1.459 | 600 |
| 1 | 2026 shock | 0.864 | 0.980 | 1.343 | 250 |
| 2 | 2020-21 pandemic | 0.560 | 0.780 | 1.046 | 550 |
| 2 | 2022-23 energy shock | 0.475 | 0.720 | 1.846 | 600 |
| 2 | 2024-25 normalisation | 0.890 | 0.987 | 2.424 | 600 |
| 2 | 2026 shock | 0.916 | 0.976 | 2.240 | 250 |
| 3 | 2020-21 pandemic | 0.495 | 0.733 | 1.240 | 525 |
| 3 | 2022-23 energy shock | 0.422 | 0.655 | 2.253 | 600 |
| 3 | 2024-25 normalisation | 0.905 | 0.978 | 3.139 | 600 |
| 3 | 2026 shock | 0.896 | 0.984 | 2.905 | 250 |
| 4 | 2020-21 pandemic | 0.490 | 0.704 | 1.340 | 500 |
| 4 | 2022-23 energy shock | 0.375 | 0.620 | 2.600 | 600 |
| 4 | 2024-25 normalisation | 0.892 | 0.965 | 3.728 | 600 |
| 4 | 2026 shock | 0.920 | 0.984 | 3.409 | 250 |
| 5 | 2020-21 pandemic | 0.484 | 0.699 | 1.465 | 475 |
| 5 | 2022-23 energy shock | 0.345 | 0.560 | 2.759 | 600 |
| 5 | 2024-25 normalisation | 0.850 | 0.930 | 4.454 | 600 |
| 5 | 2026 shock | 0.952 | 0.996 | 4.388 | 250 |
| 6 | 2020-21 pandemic | 0.489 | 0.658 | 1.513 | 450 |
| 6 | 2022-23 energy shock | 0.340 | 0.493 | 2.821 | 600 |
| 6 | 2024-25 normalisation | 0.808 | 0.910 | 5.173 | 600 |
| 6 | 2026 shock | 0.976 | 0.996 | 4.806 | 250 |

## Benchmarks

### Eurostat flash estimate (h = 1)

The flash for month T+1 is published at the end of T+1, about two weeks after our forecast is issued, with most of the month's prices. It is the bar to beat, not a floor. Flash rates have 1 decimal.

| code | n | ours_mae | flash_mae | from |
|---|---|---|---|---|
| FOOD | 437 | 0.370 | 0.082 | 2017-08 |
| IGD_NNRG | 437 | 0.432 | 0.078 | 2017-08 |
| NRG | 437 | 1.726 | 0.153 | 2017-08 |
| SERV | 437 | 0.281 | 0.066 | 2017-08 |
| TOTAL | 553 | 0.313 | 0.051 | 2017-08 |

### ECB/Eurosystem staff projections (quarterly annual rate, euro area, test exercises)

Q0 = quarter of the projection exercise (we know its first month), Q1 = next quarter. Staff projections typically also use the flash for the month before publication: an information edge for the ECB.

| horizon | code | n | ours_mae | ecb_mae |
|---|---|---|---|---|
| Q0 | FOOD | 14 | 0.178 | 0.117 |
| Q0 | IGD_NNRG | 3 | 0.168 | 0.044 |
| Q0 | NRG | 14 | 1.132 | 0.456 |
| Q0 | SERV | 3 | 0.086 | 0.053 |
| Q0 | TOTAL | 27 | 0.237 | 0.104 |
| Q1 | FOOD | 13 | 0.720 | 0.309 |
| Q1 | IGD_NNRG | 2 | 0.427 | 0.139 |
| Q1 | NRG | 13 | 3.662 | 1.915 |
| Q1 | SERV | 2 | 0.051 | 0.080 |
| Q1 | TOTAL | 26 | 0.984 | 0.581 |
