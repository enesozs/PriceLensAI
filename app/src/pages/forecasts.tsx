import * as Plot from "@observablehq/plot";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Badge } from "@/components/badge";
import { ChartCard, DataTable, Segmented, Select } from "@/components/chart-card";
import { GRID, PlotFigure } from "@/components/plot-figure";
import { RATE_PIVOT } from "@/lib/colors";
import { type GeoData, type Meta, type Rates, rateOf, useJson } from "@/lib/data";
import { inGeo, monthLabel, num, pct, toDate } from "@/lib/format";

// Shape written by src/pricelens/forecast.py export()
type Row = Record<string, string | number | null>;
type ForecastData = {
  meta: {
    chosen_model: string;
    chosen_label: string;
    latest_origin: string;
    issued_as_of: string;
    test_from: string;
    valid: [string, string];
    generated_at: string;
  };
  labels: Record<string, string>;
  by_model: { model: string; h: number; mae: number; rmse: number; n: number }[];
  by_regime: Row[];
  coverage: { h: number; period: string; cov80: number; cov95: number; width80: number; n: number }[];
  flash: { code: string; n: number; ours_mae: number; flash_mae: number; from_: string }[];
  flash_rows: Record<string, { target: string[]; ours: (number | null)[]; flash: (number | null)[]; true: (number | null)[] }>;
  staff: { horizon: string; code: string; n: number; ours_mae: number; ecb_mae: number }[];
  series: Record<string, Record<string, { target: string[]; pred: (number | null)[]; lo80: (number | null)[]; hi80: (number | null)[]; true: (number | null)[] }>>;
  live: { geo: string; code: string; h: number; target: string; pred: number; lo80: number | null; hi80: number | null; lo95: number | null; hi95: number | null }[];
};

const CODES = ["TOTAL", "NRG", "FOOD", "IGD_NNRG", "SERV"];
const FLOORS = ["no_change", "seasonal_naive", "seasonal_mean"];

export function ForecastsPage({ meta, rates }: { meta: Meta; rates: Rates }) {
  const { data: fd, error } = useJson<ForecastData>("forecast.json");
  const [params, setParams] = useSearchParams();
  const geos = ["EA", "DE", "FR", "IT", "ES"];
  const geo = geos.includes(params.get("geo") ?? "") ? params.get("geo")! : "EA";
  const setGeo = (g: string) => setParams((p) => (p.set("geo", g), p), { replace: true });
  const { data: gd } = useJson<GeoData>(`geo/${geo}.json`);
  const name = meta.geos.find((g) => g.code === geo)?.name ?? geo;
  if (error) return <p className="py-16 text-sm">Forecasts not available ({error}). Run `uv run pricelens forecast && uv run pricelens export`.</p>;
  if (!fd || !gd) return <div className="py-16 text-sm text-muted">Loading…</div>;
  return (
    <div className="pt-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1.5">
          <Badge type="forecast" />
          <Badge type="benchmark" />
        </div>
        <Select label="Country or area" value={geo} onChange={setGeo} options={geos.map((g) => ({ value: g, label: meta.geos.find((x) => x.code === g)?.name ?? g }))} />
      </div>
      <Live meta={meta} rates={rates} fd={fd} gd={gd} geo={geo} name={inGeo(geo, name)} />
      <TrackRecord meta={meta} fd={fd} geo={geo} name={inGeo(geo, name)} />
      <Scoreboard fd={fd} />
      <Benchmarks meta={meta} fd={fd} />
      <Calibration fd={fd} />
      <Experiments />
      <section className="border-t border-rule pt-6 pb-4 text-sm leading-relaxed text-ink-2">
        <h2 className="mb-2 font-serif text-xl text-ink">How these forecasts are made and tested</h2>
        <ul className="max-w-3xl list-disc space-y-1.5 pl-5">
          <li>
            Each forecast is made as if on the 15th of the month after the latest full HICP release: it uses official prices up to that release, Brent
            crude and the euro–dollar rate up to the 15th, and EU Weekly Oil Bulletin pump prices published by then. Nothing later is used.
          </li>
          <li>
            Models learn how far each month deviates from its usual seasonal pattern, using recent price momentum, oil, pump prices and the exchange rate.
            They are compared with three simple rules that any forecast should beat: no change, last year's same-month change, and the average same-month
            change of the last three years.
          </li>
          <li>
            All settings were chosen on forecasts for {fd.meta.valid[0]}–{fd.meta.valid[1]}; the scores here are for forecasts from {fd.meta.test_from}{" "}
            onward, which were never used to choose anything. History is the current published data (the HICP is rarely revised).
          </li>
          <li>
            Ranges are the forecast plus the spread of the model's own past errors (last five years). Forecasts are statistical predictions, not
            explanations of why prices change.
          </li>
        </ul>
      </section>
    </div>
  );
}

function Live({ meta, rates, fd, gd, geo, name }: { meta: Meta; rates: Rates; fd: ForecastData; gd: GeoData; geo: string; name: string }) {
  const [code, setCode] = useState("TOTAL");
  const live = fd.live.filter((r) => r.geo === geo && r.code === code).sort((a, b) => a.h - b.h);
  const end = gd.months.indexOf(fd.meta.latest_origin.slice(0, 7));
  const hist = gd.months.slice(Math.max(0, end - 35), end + 1).map((m) => ({ date: toDate(m), m, v: gd.yoy[code][gd.months.indexOf(m)] }));
  const flashM = meta.flash_month;
  const flashV = flashM ? rateOf(rates, geo, code, flashM) : null;
  const fc = [{ date: hist[hist.length - 1].date, m: hist[hist.length - 1].m, pred: hist[hist.length - 1].v, lo80: hist[hist.length - 1].v, hi80: hist[hist.length - 1].v, lo95: hist[hist.length - 1].v, hi95: hist[hist.length - 1].v }, ...live.map((r) => ({ date: toDate(r.target), m: r.target, pred: r.pred, lo80: r.lo80, hi80: r.hi80, lo95: r.lo95, hi95: r.hi95 }))];
  const first = live[0];
  return (
    <>
      <h1 className="mt-3 max-w-4xl font-serif text-4xl leading-[1.1] font-medium tracking-tight text-ink sm:text-5xl">
        Where inflation in {name} is heading
      </h1>
      <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-ink-2">
        {first && (
          <>
            The model expects {meta.labels[code].toLowerCase()} inflation of <span className="num text-ink">{pct(first.pred)}</span> in {monthLabel(first.target)} (80% range{" "}
            {pct(first.lo80)} to {pct(first.hi80)}), as forecast on {fd.meta.issued_as_of}.{" "}
          </>
        )}
        {flashM && flashV != null && first?.target === flashM && (
          <>
            Eurostat's flash estimate, published two weeks later, came in at <span className="num text-ink">{pct(flashV)}</span>.
          </>
        )}
      </p>
      <ChartCard
        badges={["forecast", "official"]}
        title="The next six months"
        subtitle={<>Annual inflation: published data (solid), the model's central forecast (dashed) with 80% and 95% ranges, and the latest flash estimate where available.</>}
        controls={<Select label="Measure" value={code} onChange={setCode} options={CODES.map((c) => ({ value: c, label: meta.labels[c] }))} />}
        footnote={`Model: ${fd.meta.chosen_label}, chosen on ${fd.meta.valid[0]}–${fd.meta.valid[1]} forecasts. Issued as of ${fd.meta.issued_as_of} from data to ${monthLabel(fd.meta.latest_origin.slice(0, 7))}. Ranges from the model's past errors. Not an official forecast.`}
        table={<DataTable head={["Month", "Forecast", "80% range", "95% range"]} rows={live.map((r) => [monthLabel(r.target), pct(r.pred), `${pct(r.lo80)} to ${pct(r.hi80)}`, `${pct(r.lo95)} to ${pct(r.hi95)}`])} />}
      >
        <PlotFigure
          label={`Forecast of ${meta.labels[code]} inflation, ${name}`}
          deps={[geo, code, fd.meta.generated_at]}
          make={(width) => ({
            width,
            height: 320,
            x: { type: "utc", label: null },
            y: { label: "% vs a year earlier", grid: true },
            marks: [
              Plot.gridY({ ...GRID }),
              Plot.ruleY([0], { stroke: "var(--ink-2)" }),
              Plot.ruleY([RATE_PIVOT], { stroke: "var(--muted)", strokeOpacity: 0.6 }),
              Plot.areaY(fc, { x: "date", y1: "lo95", y2: "hi95", fill: "var(--c-neig)", fillOpacity: 0.12, curve: "monotone-x" }),
              Plot.areaY(fc, { x: "date", y1: "lo80", y2: "hi80", fill: "var(--c-neig)", fillOpacity: 0.22, curve: "monotone-x" }),
              Plot.lineY(hist, { x: "date", y: "v", stroke: "var(--ink)", strokeWidth: 2 }),
              Plot.lineY(fc, { x: "date", y: "pred", stroke: "var(--c-neig)", strokeWidth: 2, strokeDasharray: "5,4" }),
              Plot.dot(fc.slice(1), { x: "date", y: "pred", fill: "var(--c-neig)", r: 3 }),
              ...(flashM && flashV != null
                ? [
                    Plot.dot([{ date: toDate(flashM), v: flashV }], { x: "date", y: "v", symbol: "diamond", r: 6, fill: "var(--ink)", stroke: "var(--surface)", strokeWidth: 2 }),
                    Plot.text([{ date: toDate(flashM), v: flashV }], { x: "date", y: "v", text: () => "Flash", dy: -14, fill: "var(--ink)", fontWeight: 600 }),
                  ]
                : []),
              Plot.tip(fc.slice(1), Plot.pointerX({ x: "date", y: "pred", title: (d: (typeof fc)[number]) => `${monthLabel(d.m)}\nForecast ${pct(d.pred)}\n80%: ${pct(d.lo80)} to ${pct(d.hi80)}\n95%: ${pct(d.lo95)} to ${pct(d.hi95)}` })),
            ],
          })}
        />
      </ChartCard>
    </>
  );
}

function TrackRecord({ meta, fd, geo, name }: { meta: Meta; fd: ForecastData; geo: string; name: string }) {
  const [h, setH] = useState("1");
  const data = CODES.flatMap((c) => {
    const s = fd.series[`${geo}|${c}`]?.[h];
    if (!s) return [];
    return s.target.map((t, i) => ({ code: meta.labels[c], c, date: toDate(t), m: t, pred: s.pred[i], lo80: s.lo80[i], hi80: s.hi80[i], true: s.true[i] })).filter((d) => d.m >= fd.meta.test_from);
  });
  return (
    <ChartCard
      badges={["forecast", "official"]}
      title="Track record: forecasts against what happened"
      subtitle={<>Each dot is a forecast made {h === "1" ? "one month" : "three months"} ahead, out of sample; the line is the published rate. The shaded band is the 80% range given at the time.</>}
      controls={<Segmented label="Horizon" value={h} onChange={setH} options={[{ value: "1", label: "1 month ahead" }, { value: "3", label: "3 months ahead" }]} />}
      footnote={`${name}. Forecasts from ${fd.meta.test_from} onward were never used to choose models or settings. All panels share one axis.`}
    >
      <PlotFigure
        label={`Out-of-sample forecasts vs outcomes, ${name}`}
        deps={[geo, h]}
        make={(width) => {
          const cols = width < 700 ? 1 : 2;
          const idx = (c: string) => CODES.indexOf(c);
          const d2 = data.map((d) => ({ ...d, fx: idx(d.c) % cols, fy: Math.floor(idx(d.c) / cols) }));
          const titles = CODES.map((c, i) => ({ fx: i % cols, fy: Math.floor(i / cols), t: meta.labels[c], c }));
          return {
            width,
            height: Math.ceil(CODES.length / cols) * 200 + 20,
            marginTop: 22,
            fx: { axis: null, padding: 0.08 },
            fy: { axis: null, padding: 0.25 },
            x: { type: "utc", label: null, ticks: 4 },
            y: { label: null, grid: true, tickFormat: (v: number) => `${v}%` },
            marks: [
              Plot.gridY({ ...GRID }),
              Plot.ruleY([0], { stroke: "var(--ink-2)", strokeWidth: 0.75 }),
              Plot.text(titles, { fx: "fx", fy: "fy", text: "t", frameAnchor: "top-left", dy: -16, fontWeight: 600, fill: "var(--ink)" }),
              Plot.areaY(d2, { fx: "fx", fy: "fy", x: "date", y1: "lo80", y2: "hi80", fill: "var(--c-neig)", fillOpacity: 0.16 }),
              Plot.lineY(d2, { fx: "fx", fy: "fy", x: "date", y: "true", stroke: "var(--ink)", strokeWidth: 1.75 }),
              Plot.dot(d2, { fx: "fx", fy: "fy", x: "date", y: "pred", r: 2.2, fill: "var(--c-neig)" }),
              Plot.tip(d2, Plot.pointerX({ fx: "fx", fy: "fy", x: "date", y: "pred", title: (d: (typeof d2)[number]) => `${d.code}, ${monthLabel(d.m)}\nForecast ${pct(d.pred)} (80%: ${pct(d.lo80)} to ${pct(d.hi80)})\nOutcome ${pct(d.true)}` })),
            ],
          };
        }}
      />
    </ChartCard>
  );
}

function Scoreboard({ fd }: { fd: ForecastData }) {
  const [h, setH] = useState("1");
  const rows = fd.by_model.filter((r) => String(r.h) === h).sort((a, b) => a.mae - b.mae);
  const label = (m: string) => fd.labels[m] ?? m;
  const chosen = rows.find((r) => r.model === fd.meta.chosen_model);
  const bestFloor = rows.filter((r) => FLOORS.includes(r.model)).sort((a, b) => a.mae - b.mae)[0];
  const gain = chosen && bestFloor ? 100 * (1 - chosen.mae / bestFloor.mae) : null;
  return (
    <ChartCard
      badges={["forecast"]}
      title={gain != null && gain > 0 ? `The model beats the simple rules by ${Math.round(gain)}%` : "How the models score"}
      subtitle={<>Average error of the annual inflation rate, in percentage points, across 25 series (euro area and four largest economies × headline and four components). Lower is better. Grey bars are the simple rules any model should beat.</>}
      controls={<Segmented label="Horizon" value={h} onChange={setH} options={[{ value: "1", label: "1 month" }, { value: "3", label: "3 months" }]} />}
      footnote={`Mean absolute error over forecasts from ${fd.meta.test_from} onward (out of sample). The model used on this page (${fd.meta.chosen_label}) was chosen on ${fd.meta.valid[0]}–${fd.meta.valid[1]} forecasts, before looking at these scores.`}
      table={<DataTable head={["Model", "MAE (pp)", "RMSE (pp)", "Forecasts"]} rows={rows.map((r) => [label(r.model), num(r.mae, 3), num(r.rmse, 3), r.n])} />}
    >
      <PlotFigure
        label="Forecast error by model"
        deps={[h]}
        make={(width) => ({
          width,
          height: 30 * rows.length + 40,
          marginLeft: width < 600 ? 170 : 240,
          marginRight: 50,
          x: { label: "mean absolute error, pp", grid: true },
          y: { domain: rows.map((r) => label(r.model)), label: null, tickSize: 0 },
          marks: [
            Plot.gridX({ ...GRID }),
            Plot.barX(rows, {
              x: "mae",
              y: (r: (typeof rows)[number]) => label(r.model),
              fill: (r: (typeof rows)[number]) => (r.model === fd.meta.chosen_model ? "var(--c-neig)" : FLOORS.includes(r.model) ? "var(--muted)" : "var(--ink-2)"),
              fillOpacity: (r: (typeof rows)[number]) => (FLOORS.includes(r.model) ? 0.5 : 1),
              insetTop: 4,
              insetBottom: 4,
              rx: 2,
            }),
            Plot.text(rows, { x: "mae", y: (r: (typeof rows)[number]) => label(r.model), text: (r: (typeof rows)[number]) => num(r.mae, 2), textAnchor: "start", dx: 5, fill: "var(--ink-2)" }),
          ],
        })}
      />
    </ChartCard>
  );
}

function Benchmarks({ meta, fd }: { meta: Meta; fd: ForecastData }) {
  const fl = fd.flash.flatMap((r) => [
    { code: meta.labels[r.code], who: "PriceLens (2 weeks earlier)", mae: r.ours_mae, n: r.n },
    { code: meta.labels[r.code], who: "Eurostat flash", mae: r.flash_mae, n: r.n },
  ]);
  const st = fd.staff;
  const ea = fd.flash_rows["EA|TOTAL"];
  const pts = ea ? ea.target.map((t, i) => ({ date: toDate(t), m: t, ours: ea.ours[i], flash: ea.flash[i], true: ea.true[i] })) : [];
  return (
    <>
      <ChartCard
        badges={["forecast", "flash"]}
        title={(() => {
          const t = fd.flash.find((r) => r.code === "TOTAL");
          return t ? `The official flash is still about ${Math.round(t.ours_mae / t.flash_mae)}× more accurate` : "Against the official flash estimate";
        })()}
        subtitle={<>Eurostat publishes a flash estimate at the end of each month, with most of the month's prices already collected. PriceLens forecasts the same month about two weeks earlier. The flash is the bar to beat, not a floor.</>}
        footnote={`Mean absolute error of the annual rate against the final figure, one month ahead, same months for both (flash history from Eurostat first-release data: euro area from 2017-08, member states from 2018). Flash rates are rounded to one decimal.`}
        table={<DataTable head={["Measure", "Months", "PriceLens MAE (pp)", "Flash MAE (pp)"]} rows={fd.flash.map((r) => [meta.labels[r.code], r.n, num(r.ours_mae, 3), num(r.flash_mae, 3)])} />}
      >
        <PlotFigure
          label="Forecast error versus the flash estimate"
          deps={[fd.meta.generated_at]}
          make={(width) => ({
            width,
            height: 58 * fd.flash.length + 60,
            marginLeft: width < 600 ? 150 : 210,
            marginRight: 50,
            x: { label: "mean absolute error, pp", grid: true },
            y: { domain: ["PriceLens (2 weeks earlier)", "Eurostat flash"], axis: null },
            fy: { domain: fd.flash.map((r) => meta.labels[r.code]), label: null, padding: 0.15 },
            color: { domain: ["PriceLens (2 weeks earlier)", "Eurostat flash"], range: ["var(--c-neig)", "var(--muted)"], legend: true },
            marks: [
              Plot.gridX({ ...GRID }),
              Plot.barX(fl, { x: "mae", y: "who", fy: "code", fill: "who", insetTop: 1, insetBottom: 1, rx: 2 }),
              Plot.text(fl, { x: "mae", y: "who", fy: "code", text: (d: (typeof fl)[number]) => num(d.mae, 2), textAnchor: "start", dx: 5, fill: "var(--ink-2)" }),
            ],
          })}
        />
        {pts.length > 0 && (
          <div className="mt-6">
            <p className="mb-2 text-sm text-ink-2">Euro area headline, month by month: outcome (line), flash (grey diamonds) and PriceLens one month ahead (blue dots).</p>
            <PlotFigure
              label="Euro area headline: outcome, flash and forecast"
              deps={[fd.meta.generated_at]}
              make={(width) => ({
                width,
                height: 240,
                x: { type: "utc", label: null },
                y: { label: "% vs a year earlier", grid: true },
                marks: [
                  Plot.gridY({ ...GRID }),
                  Plot.ruleY([0], { stroke: "var(--ink-2)" }),
                  Plot.lineY(pts, { x: "date", y: "true", stroke: "var(--ink)", strokeWidth: 1.75 }),
                  Plot.dot(pts, { x: "date", y: "flash", symbol: "diamond", r: 3.5, fill: "var(--muted)" }),
                  Plot.dot(pts, { x: "date", y: "ours", r: 2.5, fill: "var(--c-neig)" }),
                  Plot.tip(pts, Plot.pointerX({ x: "date", y: "true", title: (d: (typeof pts)[number]) => `${monthLabel(d.m)}\nOutcome ${pct(d.true)}\nFlash ${pct(d.flash)}\nPriceLens ${pct(d.ours)}` })),
                ],
              })}
            />
          </div>
        )}
      </ChartCard>
      <ChartCard
        badges={["forecast", "benchmark"]}
        title={(() => {
          const t = st.filter((r) => r.code === "TOTAL");
          const ecbWins = t.length > 0 && t.every((r) => r.ecb_mae < r.ours_mae);
          return ecbWins ? "ECB staff projections are more accurate, too" : "Against ECB staff projections";
        })()}
        subtitle={<>The ECB and Eurosystem staff publish quarterly projections four times a year. Here PriceLens's monthly forecasts are averaged into the same quarters for the euro area. Q0 is the quarter of the projection, Q1 the following quarter.</>}
        footnote="Mean absolute error of the quarterly annual rate, projection exercises from 2020 onward. Staff projections usually use one more month of data (the flash) than PriceLens's comparable forecast. Projections: Eurosystem/ECB staff macroeconomic projections, source: ECB; the error statistics are computed by PriceLens."
        table={<DataTable head={["Quarter", "Measure", "Exercises", "PriceLens MAE (pp)", "ECB staff MAE (pp)"]} rows={st.map((r) => [r.horizon, meta.labels[r.code], r.n, num(r.ours_mae, 3), num(r.ecb_mae, 3)])} />}
      >
        <div className="overflow-x-auto rounded border border-rule">
          <DataTable
            head={["Measure", "Q0 PriceLens", "Q0 ECB staff", "Q1 PriceLens", "Q1 ECB staff"]}
            rows={CODES.map((c) => {
              const q0 = st.find((r) => r.code === c && r.horizon === "Q0");
              const q1 = st.find((r) => r.code === c && r.horizon === "Q1");
              return [meta.labels[c], num(q0?.ours_mae, 2), num(q0?.ecb_mae, 2), num(q1?.ours_mae, 2), num(q1?.ecb_mae, 2)];
            })}
          />
        </div>
      </ChartCard>
    </>
  );
}

function Calibration({ fd }: { fd: ForecastData }) {
  const rows = fd.coverage.filter((r) => r.h === 1 || r.h === 3);
  return (
    <ChartCard
      badges={["forecast"]}
      title="Are the ranges honest? Not during shocks"
      subtitle={(() => {
        const shock = rows.find((r) => r.h === 1 && r.period.startsWith("2022"));
        const calm = rows.find((r) => r.h === 1 && r.period.startsWith("2024"));
        return (
          <>
            Share of outcomes that fell inside the 80% range given at the time. In the 2022–23 energy shock only {pct(100 * (shock?.cov80 ?? 0), 0)} of
            one-month-ahead outcomes did: ranges built from calmer past errors were too narrow. Afterwards they were too wide ({pct(100 * (calm?.cov80 ?? 0), 0)}{" "}
            in 2024–25) because they still remembered the shock.
          </>
        );
      })()}
      footnote="Out-of-sample forecasts of the chosen model, all 25 series. Range width is the median width of the 80% range in percentage points."
      table={<DataTable head={["Horizon", "Period", "Inside 80%", "Inside 95%", "Median 80% width (pp)", "Forecasts"]} rows={rows.map((r) => [r.h, r.period, pct(100 * r.cov80, 0), pct(100 * r.cov95, 0), num(r.width80, 2), r.n])} />}
    >
      <PlotFigure
        label="Interval coverage by period"
        deps={[fd.meta.generated_at]}
        make={(width) => ({
          width,
          height: 260,
          marginLeft: width < 600 ? 150 : 190,
          x: { domain: [0, 1], label: "share of outcomes inside the 80% range", grid: true, tickFormat: (d: number) => `${Math.round(100 * d)}%` },
          y: { label: null, tickSize: 0 },
          fy: { label: null },
          marks: [
            Plot.gridX({ ...GRID }),
            Plot.ruleX([0.8], { stroke: "var(--ink-2)" }),
            Plot.dot(rows, { x: "cov80", y: "period", fy: (r: (typeof rows)[number]) => `${r.h} month${r.h > 1 ? "s" : ""} ahead`, r: 5, fill: "var(--c-neig)" }),
            Plot.text(rows, { x: "cov80", y: "period", fy: (r: (typeof rows)[number]) => `${r.h} month${r.h > 1 ? "s" : ""} ahead`, text: (r: (typeof rows)[number]) => pct(100 * r.cov80, 0), dx: 10, textAnchor: "start", fill: "var(--ink-2)" }),
          ],
        })}
      />
      <p className="mt-2 text-xs text-muted">The vertical line marks the 80% target.</p>
    </ChartCard>
  );
}


type Advanced = {
  ablations: { model: string; split: string; h: number; group: string; mae: number; floor: number; gain_vs_floor_pct: number }[];
  hierarchy: { validation: Record<string, number>; adopted: string; gain: number; materiality: number; table: Row[] };
  intervals: { chosen: string; validation_winkler: Record<string, number>; table: { period: string; h: number; coverage80: number; winkler: number; method: string }[] };
};

function Experiments() {
  const { data: ad } = useJson<Advanced>("advanced.json");
  if (!ad) return null;
  const abl = ad.ablations.filter((r) => r.split === "test" && r.h === 1);
  const order = ["full", "no Brent or FX", "no pump prices (Oil Bulletin)", "no own price momentum", "no oil, fuel or FX"];
  const iv = ad.intervals.table.filter((r) => r.h === 1 && !r.period.startsWith("2012"));
  const shock = (m: string) => iv.find((r) => r.period.startsWith("2022") && r.method === m)?.coverage80 ?? 0;
  return (
    <>
      <ChartCard
        badges={["forecast"]}
        title="What the forecasts rely on"
        subtitle={<>How much better than the seasonal rule the model is when one family of inputs is removed, one month ahead, test period. Weekly pump prices carry the energy forecasts; for the other series the inputs matter less.</>}
        footnote="Ablations of the pooled ridge model: the same model refitted without the named inputs, scored on forecasts from 2020 onward. Gain = 1 − error ÷ error of the 3-year seasonal mean."
        table={<DataTable head={["Inputs", "Series", "MAE (pp)", "Gain vs seasonal rule"]} rows={abl.map((r) => [r.model, r.group, num(r.mae, 3), pct(r.gain_vs_floor_pct, 0)])} />}
      >
        <PlotFigure
          label="Ablation gains"
          deps={[abl.length]}
          make={(width) => ({
            width,
            height: 260,
            marginLeft: width < 600 ? 170 : 220,
            marginRight: 50,
            x: { label: "gain vs seasonal rule, %", grid: true },
            y: { domain: order, label: null, tickSize: 0 },
            fy: { label: null },
            marks: [
              Plot.gridX({ ...GRID }),
              Plot.barX(abl, { x: "gain_vs_floor_pct", y: "model", fy: "group", fill: (r: (typeof abl)[number]) => (r.model === "full" ? "var(--c-neig)" : "var(--muted)"), insetTop: 2, insetBottom: 2, rx: 2 }),
              Plot.ruleX([0], { stroke: "var(--ink-2)" }),
              Plot.text(abl, { x: "gain_vs_floor_pct", y: "model", fy: "group", text: (r: (typeof abl)[number]) => pct(r.gain_vs_floor_pct, 0), textAnchor: "start", dx: 5, fill: "var(--ink-2)" }),
            ],
          })}
        />
      </ChartCard>
      <section className="border-t border-rule pt-6 pb-10">
        <div className="mb-1.5 flex gap-1.5">
          <Badge type="forecast" />
        </div>
        <h2 className="font-serif text-2xl font-medium text-ink sm:text-[28px]">Two ideas that did not make the cut</h2>
        <div className="mt-3 grid gap-6 text-[15px] leading-relaxed text-ink-2 md:grid-cols-2">
          <div>
            <h3 className="font-medium text-ink">Building the headline from its parts</h3>
            <p className="mt-1">
              Forecasting energy, food, goods and services separately and combining them with the official weights, then averaging with the direct headline
              forecast, was {pct(100 * ad.hierarchy.gain, 1)} more accurate on 2012–2019. That is below the {pct(100 * ad.hierarchy.materiality, 0)} needed to justify
              the extra complexity, so the direct forecast stays.
            </p>
          </div>
          <div>
            <h3 className="font-medium text-ink">Ranges that widen in a crisis</h3>
            <p className="mt-1">
              Scaling the ranges by recent errors would have caught far more outcomes in the 2022–23 energy shock ({pct(100 * shock("adaptive"), 0)} inside the 80% range instead of{" "}
              {pct(100 * shock("static"), 0)}). But it scored worse on the calm 2012–2019 period used for every decision, so it was not adopted. Changing the rule after seeing the
              test period would make the test meaningless.
            </p>
          </div>
        </div>
      </section>
    </>
  );
}
