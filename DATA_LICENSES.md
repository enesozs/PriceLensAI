# Data licences and attributions

The [MIT License](LICENSE) covers the source code only. The data in this repository is **derived from third-party sources and stays under their own terms**. This applies to:
- the published site data in `app/public/data`;
- the figures in `reports/`;
- the screenshots in `docs/screenshots`.

Raw source files are never committed. The pipeline downloads them into `data/raw/`, which is kept out of git, and records each file with its source, retrieval time, content hash and licence.

PriceLens is a non-commercial project. It is not affiliated with or endorsed by any of the organisations below. Their data is reused as published and then adapted (re-weighted, aggregated, decomposed and modelled), as described for each source. The organisations are not responsible for the adapted figures.

Terms were checked against each source's published terms on 2026-11-21.

## Eurostat

- **Licence:** [Eurostat copyright notice](https://ec.europa.eu/eurostat/help/copyright-notice).
  - Statistical data may be reused, commercially or not, provided the source is acknowledged.
  - Modified data must be stated as such, together with a disclaimer of Eurostat's non-responsibility.
  - Logos and trademarks are excluded.
- **Source:** Eurostat, © European Union.
  - `prc_hicp_minr`: HICP monthly indices and rates of change, ECOICOP ver. 2.
  - `prc_hicp_iw`: HICP item weights.
  - `prc_hicp_fpd` and `prc_hicp_fp`: HICP first-released data (flash and final).
  - `hbs_str_t223`: Household Budget Survey, structure of consumption expenditure by income quintile.
- **Published as is:** official indices, annual rates and flash estimates, labelled "Official".
- **Adapted (Eurostat bears no responsibility for these figures):**
  - contributions to annual inflation;
  - the reconstruction of the all-items index used as a quality check;
  - income-group indices, built from HBS shares with imputed rent removed, mapped from COICOP 1999 to ECOICOP ver. 2 and chained with HICP indices;
  - user baskets;
  - forecasts and their evaluation.

## European Commission — Weekly Oil Bulletin

- **Licence:** [European Commission legal notice](https://commission.europa.eu/legal-notice_en).
  - EU-owned content is licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) (Commission Decision 2011/833/EU).
  - Reuse is allowed with appropriate credit and an indication of changes.
- **Source:** European Commission, Directorate-General for Energy, [Weekly Oil Bulletin](https://energy.ec.europa.eu/data-and-analysis/weekly-oil-bulletin_en), consumer prices of petroleum products with taxes (price history).
- **Adapted:** monthly and early-month averages of petrol, diesel and heating-oil prices, used as forecast inputs. No Oil Bulletin prices are published in this repository.

## U.S. Energy Information Administration — Brent spot price

- **Licence:** public domain as a US government work ([EIA copyrights and reuse](https://www.eia.gov/about/copyrights_reuse.php)). EIA asks for an acknowledgment that includes the publication date. The EIA logo is a registered trademark and is not used.
- **Source:** U.S. Energy Information Administration, Europe Brent Spot Price FOB (series RBRTE, daily). The release date of the file used appears on the site's Method page, for example "Source: U.S. Energy Information Administration (Nov 2026)".
- **Adapted:** converted to euros with the ECB reference rate and averaged by month, as a forecast input. No Brent prices are published in this repository.

## European Central Bank

- **Licence:**
  - Statistics: [ESCB policy on the reuse of statistics](https://www.ecb.europa.eu/stats/ecb_statistics/governance_and_quality_framework/html/usage_policy.en.html). They are free to reuse if the source is quoted ("Source: ECB statistics") and the statistics are not modified.
  - Other website content, including the staff projections: the [ECB copyright notice](https://www.ecb.europa.eu/services/disclaimer/html/index.en.html). It may be reproduced accurately with the ECB cited as the source, and any modification must be stated explicitly.
- **Sources:**
  - EUR/USD reference exchange rate (`EXR`).
  - Eurosystem/ECB staff macroeconomic projections for the euro area HICP and its main components (`MPD`).
- **Adapted:**
  - The exchange rate is used only to convert Brent into euros; it is not published.
  - The staff projections are not republished. PriceLens publishes only its own calculation of their forecast errors, comparing projected and outcome quarterly annual rates, labelled as computed by PriceLens.

## U.S. Bureau of Labor Statistics — Consumer Price Index

- **Licence:**
  - BLS material is in the public domain, and reuse is permitted with credit ([BLS linking and copyright information](https://www.bls.gov/opub/copyright-information.htm)).
  - Data was retrieved through the public API under the [BLS API terms of service](https://www.bls.gov/developers/termsOfService.htm).
  - The BLS emblem is a trademark and is not used.
- **Source:** U.S. Bureau of Labor Statistics, CPI-U, U.S. city average, not seasonally adjusted (series `CUUR0000…`).
- **Published as is:** index levels turned into annual rates, labelled "Official · BLS CPI-U".
- **Adapted:** contributions of energy, food, core goods and core services. These use December weights *derived* by PriceLens from the published indices; they are not the official BLS relative importances.
- **Required statement:** BLS.gov cannot vouch for the data or analyses derived from these data after the data have been retrieved from BLS.gov.

## Country boundaries: Natural Earth via world-atlas

- **Package:** the map uses the TopoJSON from [world-atlas](https://github.com/topojson/world-atlas) 2.0.2 (ISC licence, © 2013–2019 Michael Bostock), bundled into the built site; see [LICENSES/world-atlas-ISC.txt](LICENSES/world-atlas-ISC.txt).
- **Data:** it is derived from [Natural Earth](https://www.naturalearthdata.com/) Admin 0 1:50m, which is in the [public domain](https://www.naturalearthdata.com/about/terms-of-use/). Made with Natural Earth.

## Fonts

- [Inter](https://github.com/rsms/inter) and [Newsreader](https://github.com/productiontype/Newsreader) are bundled into the built site through `@fontsource`.
- Both are under the SIL Open Font License 1.1; see [LICENSES/Inter-OFL-1.1.txt](LICENSES/Inter-OFL-1.1.txt) and [LICENSES/Newsreader-OFL-1.1.txt](LICENSES/Newsreader-OFL-1.1.txt).

## Software dependencies

Python and JavaScript dependencies are installed from their registries and keep their own licences (mainly MIT, BSD and ISC). The libraries bundled into the built site are React, React Router, Observable Plot, d3 and topojson-client, all under MIT or ISC.
