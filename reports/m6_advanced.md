# M6 advanced forecasting report (generated)

All choices on validation origins 2012–2019; test = origins 2020+ (reported only). Errors are annual-rate MAE in pp.

## 1. Ablations of the pooled ridge model

Gain vs the 3-year seasonal-mean floor, by input family removed.

| model | split | h | group | mae | floor | gain_vs_floor_pct |
|---|---|---|---|---|---|---|
| no Brent or FX | test | 1 | energy | 2.194 | 3.024 | 27.458 |
| no own price momentum | test | 1 | energy | 2.252 | 3.024 | 25.523 |
| full | test | 1 | energy | 2.271 | 3.024 | 24.903 |
| no pump prices (Oil Bulletin) | test | 1 | energy | 2.500 | 3.024 | 17.340 |
| no oil, fuel or FX | test | 1 | energy | 2.877 | 3.024 | 4.859 |
| no Brent or FX | test | 1 | other series | 0.391 | 0.419 | 6.726 |
| full | test | 1 | other series | 0.394 | 0.419 | 6.009 |
| no pump prices (Oil Bulletin) | test | 1 | other series | 0.402 | 0.419 | 4.110 |
| no oil, fuel or FX | test | 1 | other series | 0.404 | 0.419 | 3.775 |
| no own price momentum | test | 1 | other series | 0.407 | 0.419 | 3.063 |
| no Brent or FX | test | 3 | energy | 5.415 | 6.478 | 16.400 |
| full | test | 3 | energy | 5.455 | 6.478 | 15.787 |
| no pump prices (Oil Bulletin) | test | 3 | energy | 5.571 | 6.478 | 13.995 |
| no own price momentum | test | 3 | energy | 5.769 | 6.478 | 10.946 |
| no oil, fuel or FX | test | 3 | energy | 5.880 | 6.478 | 9.234 |
| full | test | 3 | other series | 0.803 | 0.933 | 13.959 |
| no pump prices (Oil Bulletin) | test | 3 | other series | 0.815 | 0.933 | 12.744 |
| no Brent or FX | test | 3 | other series | 0.817 | 0.933 | 12.491 |
| no oil, fuel or FX | test | 3 | other series | 0.822 | 0.933 | 11.970 |
| no own price momentum | test | 3 | other series | 0.897 | 0.933 | 3.941 |
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
| test | 1 | 0.365 | 0.369 | 0.361 | 400 |
| test | 3 | 0.872 | 0.861 | 0.860 | 390 |
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
| 2026 shock | 1 | 0.733 | 3.054 | adaptive |
| 2026 shock | 1 | 0.862 | 3.136 | static |
| 2012-19 (validation) | 3 | 0.741 | 4.078 | adaptive |
| 2012-19 (validation) | 3 | 0.804 | 3.821 | static |
| 2020-21 pandemic | 3 | 0.588 | 7.222 | adaptive |
| 2020-21 pandemic | 3 | 0.528 | 7.145 | static |
| 2022-23 energy shock | 3 | 0.670 | 15.654 | adaptive |
| 2022-23 energy shock | 3 | 0.422 | 17.351 | static |
| 2024-25 normalisation | 3 | 0.788 | 6.250 | adaptive |
| 2024-25 normalisation | 3 | 0.905 | 6.387 | static |
| 2026 shock | 3 | 0.751 | 8.264 | adaptive |
| 2026 shock | 3 | 0.889 | 7.521 | static |
