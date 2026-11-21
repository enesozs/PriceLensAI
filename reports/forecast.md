# Forecast evaluation (generated)

Generated 2026-11-21T12:49:12+00:00 by `uv run pricelens forecast`. Latest origin 2026-09-01, issued as of 2026-10-15. Scores are annual-rate errors of the target month, in percentage points, over the euro area, DE, FR, IT and ES × headline, energy, food, non-energy industrial goods and services.

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
| Ridge + gradient boosting average | 1 | 0.754 | 1.719 | 2000 |
| Ridge, pooled | 1 | 0.770 | 1.723 | 2000 |
| Gradient boosting, pooled | 1 | 0.793 | 1.777 | 2000 |
| SARIMA per series | 1 | 0.850 | 2.047 | 2000 |
| Seasonal mean, 3 years (floor) | 1 | 0.940 | 2.097 | 2000 |
| Seasonal naïve (floor) | 1 | 1.045 | 2.397 | 2000 |
| No change (floor) | 1 | 1.091 | 2.191 | 2000 |
| Ridge + gradient boosting average | 3 | 1.722 | 3.660 | 1950 |
| Ridge, pooled | 3 | 1.734 | 3.652 | 1950 |
| SARIMA per series | 3 | 1.763 | 3.736 | 1950 |
| Gradient boosting, pooled | 3 | 1.836 | 3.807 | 1950 |
| Seasonal mean, 3 years (floor) | 3 | 2.042 | 4.059 | 1950 |
| Seasonal naïve (floor) | 3 | 2.205 | 4.682 | 1950 |
| No change (floor) | 3 | 2.330 | 4.037 | 1950 |

### By series type

| code | h | ridge | seasonal_mean | no_change |
|---|---|---|---|---|
| FOOD | 1 | 0.412 | 0.503 | 0.516 |
| IGD_NNRG | 1 | 0.508 | 0.462 | 1.288 |
| NRG | 1 | 2.271 | 3.024 | 2.538 |
| SERV | 1 | 0.291 | 0.278 | 0.570 |
| TOTAL | 1 | 0.365 | 0.436 | 0.542 |
| FOOD | 3 | 0.993 | 1.309 | 1.333 |
| IGD_NNRG | 3 | 0.813 | 0.887 | 2.488 |
| NRG | 3 | 5.455 | 6.478 | 5.386 |
| SERV | 3 | 0.535 | 0.551 | 1.235 |
| TOTAL | 3 | 0.872 | 0.986 | 1.206 |

### By period (validation and test)

| period | h | ridge | seasonal_mean |
|---|---|---|---|
| 2012-19 (validation) | 1 | 0.385 | 0.489 |
| 2020-21 pandemic | 1 | 0.610 | 0.738 |
| 2022-23 energy shock | 1 | 1.170 | 1.378 |
| 2024-25 normalisation | 1 | 0.572 | 0.699 |
| 2026 shock | 1 | 0.617 | 0.890 |
| 2012-19 (validation) | 3 | 0.885 | 0.997 |
| 2020-21 pandemic | 3 | 1.291 | 1.608 |
| 2022-23 energy shock | 3 | 2.753 | 2.972 |
| 2024-25 normalisation | 3 | 1.075 | 1.509 |
| 2026 shock | 3 | 1.719 | 1.721 |

### Interval calibration (empirical intervals from the model's own past errors)

Interval method chosen on validation (mean Winkler score of the 80% range, h = 1 and 3; lower is better): **static** — {"static": 3.4923, "adaptive": 3.6589}.

| h | period | cov80 | cov95 | width80 | n |
|---|---|---|---|---|---|
| 1 | 2020-21 pandemic | 0.612 | 0.807 | 0.730 | 575 |
| 1 | 2022-23 energy shock | 0.547 | 0.817 | 1.180 | 600 |
| 1 | 2024-25 normalisation | 0.878 | 0.980 | 1.459 | 600 |
| 1 | 2026 shock | 0.862 | 0.978 | 1.343 | 225 |
| 2 | 2020-21 pandemic | 0.560 | 0.780 | 1.046 | 550 |
| 2 | 2022-23 energy shock | 0.475 | 0.720 | 1.846 | 600 |
| 2 | 2024-25 normalisation | 0.890 | 0.987 | 2.424 | 600 |
| 2 | 2026 shock | 0.911 | 0.973 | 2.240 | 225 |
| 3 | 2020-21 pandemic | 0.495 | 0.733 | 1.240 | 525 |
| 3 | 2022-23 energy shock | 0.422 | 0.655 | 2.253 | 600 |
| 3 | 2024-25 normalisation | 0.905 | 0.978 | 3.139 | 600 |
| 3 | 2026 shock | 0.889 | 0.982 | 2.905 | 225 |
| 4 | 2020-21 pandemic | 0.490 | 0.704 | 1.340 | 500 |
| 4 | 2022-23 energy shock | 0.375 | 0.620 | 2.600 | 600 |
| 4 | 2024-25 normalisation | 0.892 | 0.965 | 3.728 | 600 |
| 4 | 2026 shock | 0.920 | 0.982 | 3.409 | 225 |
| 5 | 2020-21 pandemic | 0.484 | 0.699 | 1.465 | 475 |
| 5 | 2022-23 energy shock | 0.345 | 0.560 | 2.759 | 600 |
| 5 | 2024-25 normalisation | 0.850 | 0.930 | 4.454 | 600 |
| 5 | 2026 shock | 0.951 | 0.996 | 4.389 | 225 |
| 6 | 2020-21 pandemic | 0.489 | 0.658 | 1.513 | 450 |
| 6 | 2022-23 energy shock | 0.340 | 0.493 | 2.821 | 600 |
| 6 | 2024-25 normalisation | 0.808 | 0.910 | 5.173 | 600 |
| 6 | 2026 shock | 0.973 | 0.996 | 4.806 | 225 |

## Benchmarks

### Eurostat flash estimate (h = 1)

The flash for month T+1 is published at the end of T+1, about two weeks after our forecast is issued, with most of the month's prices. It is the bar to beat, not a floor. Flash rates have 1 decimal.

| code | n | ours_mae | flash_mae | from |
|---|---|---|---|---|
| FOOD | 432 | 0.371 | 0.083 | 2017-08 |
| IGD_NNRG | 432 | 0.435 | 0.078 | 2017-08 |
| NRG | 432 | 1.718 | 0.152 | 2017-08 |
| SERV | 432 | 0.279 | 0.066 | 2017-08 |
| TOTAL | 548 | 0.313 | 0.051 | 2017-08 |

### ECB/Eurosystem staff projections (quarterly annual rate, euro area, test exercises)

Q0 = quarter of the projection exercise (we know its first month), Q1 = next quarter. Staff projections typically also use the flash for the month before publication: an information edge for the ECB.

| horizon | code | n | ours_mae | ecb_mae |
|---|---|---|---|---|
| Q0 | FOOD | 14 | 0.178 | 0.117 |
| Q0 | IGD_NNRG | 3 | 0.168 | 0.044 |
| Q0 | NRG | 14 | 1.130 | 0.454 |
| Q0 | SERV | 3 | 0.086 | 0.053 |
| Q0 | TOTAL | 27 | 0.237 | 0.104 |
| Q1 | FOOD | 13 | 0.720 | 0.309 |
| Q1 | IGD_NNRG | 2 | 0.427 | 0.139 |
| Q1 | NRG | 13 | 3.660 | 1.914 |
| Q1 | SERV | 2 | 0.051 | 0.080 |
| Q1 | TOTAL | 26 | 0.984 | 0.582 |
