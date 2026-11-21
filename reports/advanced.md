# Advanced forecasting experiments (generated)

All choices on validation origins 2012–2019; test = origins 2020+ (reported only). Errors are annual-rate MAE in pp.

## 1. Ablations of the pooled ridge model

Gain vs the 3-year seasonal-mean floor, by input family removed.

| model | split | h | group | mae | floor | gain_vs_floor_pct |
|---|---|---|---|---|---|---|
| no Brent or FX | test | 1 | energy | 2.196 | 3.025 | 27.411 |
| no own price momentum | test | 1 | energy | 2.254 | 3.025 | 25.489 |
| full | test | 1 | energy | 2.272 | 3.025 | 24.890 |
| no pump prices (Oil Bulletin) | test | 1 | energy | 2.517 | 3.025 | 16.779 |
| no oil, fuel or FX | test | 1 | energy | 2.875 | 3.025 | 4.942 |
| no Brent or FX | test | 1 | other series | 0.390 | 0.418 | 6.550 |
| full | test | 1 | other series | 0.393 | 0.418 | 5.895 |
| no pump prices (Oil Bulletin) | test | 1 | other series | 0.401 | 0.418 | 4.051 |
| no oil, fuel or FX | test | 1 | other series | 0.402 | 0.418 | 3.675 |
| no own price momentum | test | 1 | other series | 0.406 | 0.418 | 2.939 |
| no Brent or FX | test | 3 | energy | 5.393 | 6.525 | 17.349 |
| full | test | 3 | energy | 5.447 | 6.525 | 16.523 |
| no pump prices (Oil Bulletin) | test | 3 | energy | 5.571 | 6.525 | 14.618 |
| no own price momentum | test | 3 | energy | 5.787 | 6.525 | 11.314 |
| no oil, fuel or FX | test | 3 | energy | 5.885 | 6.525 | 9.812 |
| full | test | 3 | other series | 0.798 | 0.927 | 13.930 |
| no pump prices (Oil Bulletin) | test | 3 | other series | 0.812 | 0.927 | 12.453 |
| no Brent or FX | test | 3 | other series | 0.814 | 0.927 | 12.268 |
| no oil, fuel or FX | test | 3 | other series | 0.820 | 0.927 | 11.522 |
| no own price momentum | test | 3 | other series | 0.890 | 0.927 | 3.983 |
| no Brent or FX | validation | 1 | energy | 0.871 | 1.395 | 37.520 |
| full | validation | 1 | energy | 0.884 | 1.395 | 36.651 |
| no own price momentum | validation | 1 | energy | 0.958 | 1.395 | 31.287 |
| no pump prices (Oil Bulletin) | validation | 1 | energy | 0.977 | 1.395 | 29.919 |
| no oil, fuel or FX | validation | 1 | energy | 1.308 | 1.395 | 6.235 |
| no Brent or FX | validation | 1 | other series | 0.234 | 0.242 | 3.234 |
| no pump prices (Oil Bulletin) | validation | 1 | other series | 0.235 | 0.242 | 3.034 |
| full | validation | 1 | other series | 0.235 | 0.242 | 3.010 |
| no own price momentum | validation | 1 | other series | 0.237 | 0.242 | 2.020 |
| no oil, fuel or FX | validation | 1 | other series | 0.240 | 0.242 | 1.058 |
| no pump prices (Oil Bulletin) | validation | 3 | energy | 2.608 | 3.087 | 15.530 |
| full | validation | 3 | energy | 2.646 | 3.087 | 14.302 |
| no Brent or FX | validation | 3 | energy | 2.830 | 3.087 | 8.341 |
| no own price momentum | validation | 3 | energy | 2.831 | 3.087 | 8.313 |
| no oil, fuel or FX | validation | 3 | energy | 3.089 | 3.087 | -0.042 |
| no pump prices (Oil Bulletin) | validation | 3 | other series | 0.375 | 0.416 | 9.811 |
| full | validation | 3 | other series | 0.378 | 0.416 | 9.187 |
| no Brent or FX | validation | 3 | other series | 0.380 | 0.416 | 8.544 |
| no oil, fuel or FX | validation | 3 | other series | 0.383 | 0.416 | 7.930 |
| no own price momentum | validation | 3 | other series | 0.415 | 0.416 | 0.112 |

## 2. Hierarchical headline

Validation MAE (h=1,3): {"direct": 0.2943, "bottom_up": 0.2908, "average": 0.2893}. Best alternative `average` gains 1.7% vs the direct forecast; materiality threshold 5% → adopted: **direct**.

| split | h | direct | bottom_up | average | n |
|---|---|---|---|---|---|
| test | 1 | 0.364 | 0.369 | 0.360 | 405 |
| test | 3 | 0.868 | 0.859 | 0.857 | 395 |
| validation | 1 | 0.198 | 0.193 | 0.193 | 600 |
| validation | 3 | 0.405 | 0.406 | 0.401 | 600 |

## 3. Intervals

Chosen on validation inside `pricelens forecast`: **static** (validation Winkler {"static": 3.4923, "adaptive": 3.6589}).

| period | h | coverage80 | winkler | method |
|---|---|---|---|---|
| 2012-19 (validation) | 1 | 0.764 | 1.792 | adaptive |
| 2012-19 (validation) | 1 | 0.801 | 1.747 | static |
| 2020-21 pandemic | 1 | 0.698 | 3.340 | adaptive |
| 2020-21 pandemic | 1 | 0.622 | 3.555 | static |
| 2022-23 energy shock | 1 | 0.738 | 6.335 | adaptive |
| 2022-23 energy shock | 1 | 0.547 | 7.148 | static |
| 2024-25 normalisation | 1 | 0.783 | 3.199 | adaptive |
| 2024-25 normalisation | 1 | 0.878 | 3.293 | static |
| 2026 shock | 1 | 0.720 | 3.110 | adaptive |
| 2026 shock | 1 | 0.864 | 3.140 | static |
| 2012-19 (validation) | 3 | 0.741 | 4.078 | adaptive |
| 2012-19 (validation) | 3 | 0.804 | 3.821 | static |
| 2020-21 pandemic | 3 | 0.588 | 7.222 | adaptive |
| 2020-21 pandemic | 3 | 0.528 | 7.145 | static |
| 2022-23 energy shock | 3 | 0.670 | 15.654 | adaptive |
| 2022-23 energy shock | 3 | 0.422 | 17.351 | static |
| 2024-25 normalisation | 3 | 0.788 | 6.250 | adaptive |
| 2024-25 normalisation | 3 | 0.905 | 6.387 | static |
| 2026 shock | 3 | 0.776 | 7.971 | adaptive |
| 2026 shock | 3 | 0.896 | 7.350 | static |
