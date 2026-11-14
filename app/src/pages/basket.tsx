import * as Plot from "@observablehq/plot";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Badge } from "@/components/badge";
import { ChartCard, DataTable, Segmented, Select } from "@/components/chart-card";
import { GRID, PlotFigure } from "@/components/plot-figure";
import { RATE_PIVOT } from "@/lib/colors";
import { type GeoData, type Meta, useJson } from "@/lib/data";
import { chained, contribSinceBase, extendScenario, fixedBase, normalize, rebase, yoy } from "@/lib/basket";
import { inGeo, monthLabel, num, pct, pp, toDate } from "@/lib/format";
import type { QuintileData } from "@/pages/quintiles";

type Mode = "fixed" | "chained";
type InputMode = "share" | "euro";

const HOUSING_NOTE =
  "Rent, repairs, water and household energy only. Mortgage payments and other costs of owning your home are not in the HICP, so leave them out.";

export function BasketPage({ meta }: { meta: Meta }) {
  const [params, setParams] = useSearchParams();
  const geo = params.get("geo") ?? "EA";
  const setGeo = (g: string) => setParams((p) => (p.set("geo", g), p), { replace: true });
  const { data: gd } = useJson<GeoData>(`geo/${geo}.json`);
  const { data: qd } = useJson<QuintileData>(geo === "EA" || geo === "EU27_2020" ? null : `quintiles/${geo}.json`);
  const name = meta.geos.find((g) => g.code === geo)?.name ?? geo;

  return (
    <div className="pt-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1.5">
          <Badge type="custom" />
        </div>
        <Select
          label="Prices from"
          value={geo}
          onChange={setGeo}
          options={meta.geos.map((g) => ({ value: g.code, label: g.name, group: g.aggregate ? "Aggregates" : "Countries" }))}
        />
      </div>
      <h1 className="mt-3 max-w-4xl font-serif text-4xl leading-[1.1] font-medium tracking-tight text-ink sm:text-5xl">
        Your basket, official prices
      </h1>
      <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-ink-2">
        Tell PriceLens how you split your spending and it re-weights the official price indices for {inGeo(geo, name)} to
        show how prices for <em>that</em> basket have moved. The result is a custom calculation, not an official
        statistic, and it is computed in your browser: nothing you enter is sent anywhere.
      </p>
      {geo === "IT" && (
        <p className="mt-3 max-w-3xl rounded border border-rule bg-surface p-3 text-sm text-ink-2">
          <strong className="text-ink">Italy:</strong> Italy's official index cannot be rebuilt exactly from its published
          categories and annual weights (see Method), so even the “official average” basket here differs slightly from
          the published Italian rate.
        </p>
      )}
      {gd ? <Studio meta={meta} gd={gd} qd={qd} name={inGeo(geo, name)} /> : <div className="py-16 text-sm text-muted">Loading…</div>}
    </div>
  );
}

function officialPercent(gd: GeoData, divisions: string[], year: string): Record<string, number> {
  const w = gd.weights[year] ?? {};
  return Object.fromEntries(divisions.map((d) => [d, Math.round((w[d] ?? 0) / 10 * 10) / 10]));
}

function Studio({ meta, gd, qd, name }: { meta: Meta; gd: GeoData; qd: QuintileData | null; name: string }) {
  const divs = meta.divisions;
  const latestYear = String(Math.max(...Object.keys(gd.weights).map(Number)));
  const official = useMemo(() => officialPercent(gd, divs, latestYear), [gd, divs, latestYear]);
  const [amounts, setAmounts] = useState<Record<string, number>>(official);
  const [preset, setPreset] = useState("official");
  const [mode, setMode] = useState<Mode>("chained");
  const [inputMode, setInputMode] = useState<InputMode>("share");
  const decembers = gd.months.filter((m) => m.endsWith("-12") && m >= "2000-12" && m < meta.latest_full_month);
  const [base, setBase] = useState(decembers.includes("2020-12") ? "2020-12" : decembers[0]);

  const presets: { value: string; label: string; shares?: Record<string, number> }[] = [
    { value: "official", label: `Average household (official weights ${latestYear})`, shares: official },
    { value: "equal", label: "Equal split", shares: Object.fromEntries(divs.map((d) => [d, Math.round(1000 / divs.length) / 10])) },
  ];
  if (qd) {
    const w = String(Math.max(...qd.waves));
    for (const [q, label] of [["QU1", "Lowest-income fifth"], ["QU5", "Highest-income fifth"]] as const) {
      presets.push({
        value: q,
        label: `${label} (survey ${w})`,
        shares: Object.fromEntries(divs.map((d) => [d, Math.round((qd.shares[w][q][d] ?? 0) * 1000) / 10])),
      });
    }
  }
  const applyPreset = (v: string) => {
    setPreset(v);
    const p = presets.find((x) => x.value === v);
    if (p?.shares) {
      setInputMode("share");
      setAmounts(p.shares);
    }
  };
  const setOne = (d: string, v: number) => {
    setPreset("custom");
    setAmounts((a) => ({ ...a, [d]: v }));
  };

  const norm = normalize(amounts);
  const lastFull = gd.months.indexOf(meta.latest_full_month);
  const months = gd.months.slice(0, lastFull + 1);
  const index = useMemo(() => Object.fromEntries(divs.map((d) => [d, gd.index[d].slice(0, lastFull + 1)])), [gd, divs, lastFull]);
  const bi = months.indexOf(base);

  const result = useMemo(() => {
    if (norm.error) return null;
    const lv = mode === "fixed" ? fixedBase(index, norm.shares, bi) : chained(index, months, () => norm.shares, bi);
    const off = rebase(gd.index.TOTAL.slice(0, lastFull + 1), bi);
    return { lv, rate: yoy(lv), off, offRate: gd.yoy.TOTAL.slice(0, lastFull + 1) };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(norm.shares), mode, bi, index, months, gd, lastFull]);

  const t = lastFull;
  const contrib = norm.error ? null : contribSinceBase(index, norm.shares, bi, t);

  return (
    <>
      <section className="mt-8 grid gap-8 border-t border-rule pt-6 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
        <div>
          <h2 className="font-serif text-2xl font-medium text-ink">1. How do you spend?</h2>
          <div className="mt-3 flex flex-col gap-2">
            <Select label="Start from" value={preset} onChange={applyPreset} options={[...presets, { value: "custom", label: "Your own numbers" }]} />
            <Segmented
              label="Enter as"
              value={inputMode}
              onChange={setInputMode}
              options={[
                { value: "share", label: "% of spending" },
                { value: "euro", label: "€ per month" },
              ]}
            />
          </div>
          <WeightsEditor meta={meta} amounts={amounts} setOne={setOne} official={official} shares={norm.shares} inputMode={inputMode} latestYear={latestYear} />
          <p className="mt-2 text-xs leading-relaxed text-muted" role="status">
            {norm.error
              ? norm.error
              : inputMode === "euro"
                ? `Your amounts total €${num(norm.total, 0)} a month; each category's share is its amount divided by the total.`
                : Math.abs(norm.total - 100) < 0.05
                  ? "Shares add up to 100%."
                  : `Your numbers add up to ${num(norm.total)}%, so PriceLens rescales them to 100% (shown on the right of each row).`}
          </p>
        </div>
        <div>
          <h2 className="font-serif text-2xl font-medium text-ink">2. Since when?</h2>
          <div className="mt-3 flex flex-wrap gap-2">
            <Select label="Start month" value={base} onChange={setBase} options={decembers.map((m) => ({ value: m, label: monthLabel(m) }))} />
            <Segmented
              label="Method"
              value={mode}
              onChange={setMode}
              options={[
                { value: "chained", label: "Re-weighted yearly" },
                { value: "fixed", label: "Fixed basket" },
              ]}
            />
          </div>
          <p className="mt-2 text-xs leading-relaxed text-muted">
            {mode === "chained"
              ? "Your spending shares are re-applied every December, the way the official index updates its weights each year. Recommended for comparisons with the official rate."
              : "You keep buying the same quantities as in the start month. Over long periods the shares drift as relative prices change, so this diverges from the official method."}
          </p>
          {result && (
            <div className="mt-5 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-rule bg-rule">
              <Stat
                label={`Your basket, ${monthLabel(months[t])} vs a year earlier`}
                value={pct(result.rate[t])}
                sub={`Official all-items: ${pct(result.offRate[t])}`}
              />
              <Stat
                label={`Your basket since ${monthLabel(base)}`}
                value={pp(result.lv[t] != null ? result.lv[t]! - 100 : null, 1) + "%"}
                sub={`Official all-items: ${pp(result.off[t] != null ? result.off[t]! - 100 : null, 1)}%`}
              />
            </div>
          )}
        </div>
      </section>

      {result && (
        <>
          <ResultCharts months={months} bi={bi} lv={result.lv} off={result.off} rate={result.rate} offRate={result.offRate} name={name} mode={mode} />
          {contrib && <ContribChart meta={meta} contrib={contrib} base={base} month={months[t]} total={result.lv[t]} mode={mode} />}
          <Scenario meta={meta} gd={gd} index={index} months={months} shares={norm.shares} official={official} lastFull={lastFull} name={name} />
        </>
      )}
      <MethodNote />
    </>
  );
}


// End-of-line labels for two series: the higher value sits above, the lower below, so close lines never collide.
function endLabels<T extends { v: number | null; who: string }>(rows: T[], text: (d: T) => string) {
  const sorted = [...rows].filter((d) => d.v != null).sort((a, b) => b.v! - a.v!);
  return sorted.map((d, i) =>
    Plot.text([d], { x: "date", y: "v", text, textAnchor: "start", dx: 6, dy: sorted.length > 1 ? (i === 0 ? -8 : 8) : 0, fill: "var(--ink)", fontWeight: 600 }),
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="bg-surface p-4">
      <div className="text-xs text-ink-2">{label}</div>
      <div className="num mt-1 font-serif text-3xl text-ink">{value}</div>
      <div className="num text-xs text-muted">{sub}</div>
    </div>
  );
}

function WeightsEditor({
  meta,
  amounts,
  setOne,
  official,
  shares,
  inputMode,
  latestYear,
}: {
  meta: Meta;
  amounts: Record<string, number>;
  setOne: (d: string, v: number) => void;
  official: Record<string, number>;
  shares: Record<string, number>;
  inputMode: InputMode;
  latestYear: string;
}) {
  return (
    <div className="mt-4 divide-y divide-rule border-y border-rule">
      {meta.divisions.map((d) => (
        <div key={d} className="py-2">
          <div className="grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3">
            <label htmlFor={`w-${d}`} className="text-sm text-ink">
              {meta.labels[d]}
              <span className="block text-[11px] text-muted">average {num(official[d])}%</span>
            </label>
            <input
              id={`w-${d}`}
              type="number"
              min={0}
              step={inputMode === "euro" ? 10 : 0.5}
              value={Number.isFinite(amounts[d]) ? amounts[d] : 0}
              onChange={(e) => setOne(d, e.target.value === "" ? 0 : Number(e.target.value))}
              className="num w-24 rounded-md border border-rule bg-surface px-2 py-1 text-right text-sm text-ink"
              aria-describedby={d === "CP04" ? "housing-note" : undefined}
            />
            <span className="num w-14 text-right text-xs text-ink-2" title="Share after rescaling">
              {shares[d] != null ? `${(100 * shares[d]).toFixed(1)}%` : "–"}
            </span>
          </div>
          {inputMode === "share" && (
            <input
              type="range"
              min={0}
              max={60}
              step={0.5}
              value={Math.min(60, amounts[d] ?? 0)}
              onChange={(e) => setOne(d, Number(e.target.value))}
              className="mt-1 w-full accent-[var(--ink)]"
              aria-label={`${meta.labels[d]} share`}
            />
          )}
          {d === "CP04" && (
            <p id="housing-note" className="mt-1 text-[11px] leading-snug text-ink-2">
              {HOUSING_NOTE}
            </p>
          )}
        </div>
      ))}
      <p className="pt-2 text-[11px] text-muted">“Average” = Eurostat HICP item weights {latestYear}.</p>
    </div>
  );
}

function ResultCharts({
  months,
  bi,
  lv,
  off,
  rate,
  offRate,
  name,
  mode,
}: {
  months: string[];
  bi: number;
  lv: (number | null)[];
  off: (number | null)[];
  rate: (number | null)[];
  offRate: (number | null)[];
  name: string;
  mode: Mode;
}) {
  const span = months.slice(bi).map((m, k) => ({ m, date: toDate(m), you: lv[bi + k], off: off[bi + k], r: rate[bi + k], ro: offRate[bi + k] }));
  const rows = (key: "you" | "off" | "r" | "ro", who: string) => span.map((s) => ({ date: s.date, m: s.m, v: s[key], who }));
  const last = span[span.length - 1];
  const lineMarks = (a: string, b: string, data: { date: Date; m: string; v: number | null; who: string }[], fmt: (v: number | null) => string) => [
    Plot.lineY(data.filter((d) => d.who === b), { x: "date", y: "v", stroke: "var(--muted)", strokeWidth: 2 }),
    Plot.lineY(data.filter((d) => d.who === a), { x: "date", y: "v", stroke: "var(--c-neig)", strokeWidth: 2.5 }),
    ...endLabels(data.filter((d) => d.m === last.m), (d) => `${d.who} ${fmt(d.v)}`),
    Plot.ruleX(span, Plot.pointerX({ x: "date", stroke: "var(--ink-2)" })),
    Plot.tip(
      data.filter((d) => d.who === a),
      Plot.pointerX({
        x: "date",
        y: "v",
        title: (d: { m: string; v: number | null }) =>
          `${monthLabel(d.m)}\nYour basket: ${fmt(d.v)}\nOfficial all-items: ${fmt(data.find((x) => x.m === d.m && x.who === b)?.v ?? null)}`,
      }),
    ),
  ];
  const levelData = [...rows("you", "Your basket"), ...rows("off", "Official")];
  const rateData = [...rows("r", "Your basket"), ...rows("ro", "Official")];
  return (
    <>
      <ChartCard
        badges={["custom", "official"]}
        title="How much more your basket costs"
        subtitle={<>Price level of your basket and of the official all-items index for {name}, both set to 100 in {monthLabel(months[bi])}.</>}
        footnote={`Custom ${mode === "chained" ? "annually re-weighted (December-linked)" : "fixed-base"} basket index computed in your browser from Eurostat HICP division indices (2025=100), rebased to ${monthLabel(months[bi])} = 100; official all-items HICP rebased the same way. An index level shows price change, not euros spent.`}
        table={<DataTable head={["Month", "Your basket", "Official all-items"]} rows={[...span].reverse().map((s) => [monthLabel(s.m), num(s.you, 1), num(s.off, 1)])} />}
      >
        <PlotFigure
          label="Basket price level against the official index"
          deps={[JSON.stringify(levelData.slice(-3)), bi, levelData.length]}
          make={(width) => ({
            width,
            height: 320,
            marginRight: width < 600 ? 120 : 170,
            x: { type: "utc", label: null },
            y: { label: `Index, ${monthLabel(months[bi])} = 100`, grid: true },
            marks: [Plot.gridY({ ...GRID }), Plot.ruleY([100], { stroke: "var(--ink-2)" }), ...lineMarks("Your basket", "Official", levelData, (v) => num(v, 1))],
          })}
        />
      </ChartCard>
      <ChartCard
        badges={["custom", "official"]}
        title="Your inflation rate, month by month"
        subtitle="The annual rate: how much more the same basket costs than twelve months before."
        footnote="Annual rate of the custom basket index vs the published HICP annual rate. The line at 2% marks the ECB's target."
        table={<DataTable head={["Month", "Your basket", "Official"]} rows={[...span].reverse().filter((s) => s.r != null).map((s) => [monthLabel(s.m), pct(s.r), pct(s.ro)])} />}
      >
        <PlotFigure
          label="Basket annual inflation against the official rate"
          deps={[JSON.stringify(rateData.slice(-3)), bi, rateData.length]}
          make={(width) => ({
            width,
            height: 300,
            marginRight: width < 600 ? 120 : 170,
            x: { type: "utc", label: null },
            y: { label: "% vs a year earlier", grid: true },
            marks: [
              Plot.gridY({ ...GRID }),
              Plot.ruleY([0], { stroke: "var(--ink-2)" }),
              Plot.ruleY([RATE_PIVOT], { stroke: "var(--muted)" }),
              ...lineMarks("Your basket", "Official", rateData.filter((d) => d.v != null), (v) => pct(v)),
            ],
          })}
        />
      </ChartCard>
    </>
  );
}

function ContribChart({
  meta,
  contrib,
  base,
  month,
  total,
  mode,
}: {
  meta: Meta;
  contrib: Record<string, number | null>;
  base: string;
  month: string;
  total: number | null;
  mode: Mode;
}) {
  const rows = Object.entries(contrib)
    .filter(([, v]) => v != null)
    .map(([c, v]) => ({ label: meta.labels[c], v: v as number }))
    .sort((a, b) => b.v - a.v);
  const sum = rows.reduce((a, r) => a + r.v, 0);
  return (
    <ChartCard
      badges={["custom"]}
      title="Where the increase comes from"
      subtitle={<>Contribution of each category to your basket's price rise since {monthLabel(base)}, in percentage points.</>}
      footnote={`Fixed-base contributions: share × price change of the category since ${monthLabel(base)}. They add up to the fixed-basket change (${pp(sum, 1)}%)${mode === "chained" ? `; the re-weighted index shown above differs slightly (${pp(total != null ? total - 100 : null, 1)}%) because it re-applies your shares each December` : ""}. To ${monthLabel(month)}.`}
      table={<DataTable head={["Category", "Contribution (pp)"]} rows={rows.map((r) => [r.label, pp(r.v, 2)])} />}
    >
      <PlotFigure
        label="Contributions to the basket price rise"
        deps={[JSON.stringify(rows)]}
        make={(width) => ({
          width,
          height: 28 * rows.length + 40,
          marginLeft: width < 600 ? 150 : 200,
          marginRight: 50,
          x: { label: "percentage points", grid: true },
          y: { domain: rows.map((r) => r.label), label: null, tickSize: 0 },
          marks: [
            Plot.gridX({ ...GRID }),
            Plot.barX(rows, { x: "v", y: "label", fill: (d: { v: number }) => (d.v >= 0 ? "var(--div-hi2)" : "var(--div-lo2)"), insetTop: 3, insetBottom: 3, rx: 2 }),
            Plot.ruleX([0], { stroke: "var(--ink-2)" }),
            Plot.text(rows, { x: "v", y: "label", text: (d: { v: number }) => pp(d.v, 1), textAnchor: "start", dx: 5, fill: "var(--ink-2)", filter: (d: { v: number }) => d.v >= 0 }),
            Plot.text(rows, { x: () => 0, y: "label", text: (d: { v: number }) => pp(d.v, 1), textAnchor: "start", dx: 5, fill: "var(--ink-2)", filter: (d: { v: number }) => d.v < 0 }),
          ],
        })}
      />
    </ChartCard>
  );
}

function Scenario({
  meta,
  gd,
  index,
  months,
  shares,
  official,
  lastFull,
  name,
}: {
  meta: Meta;
  gd: GeoData;
  index: Record<string, (number | null)[]>;
  months: string[];
  shares: Record<string, number>;
  official: Record<string, number>;
  lastFull: number;
  name: string;
}) {
  const latest = Object.fromEntries(meta.divisions.map((d) => [d, gd.yoy[d][lastFull] ?? 0]));
  const [rates, setRates] = useState<Record<string, number>>(latest);
  const ext = extendScenario(index, months, lastFull, rates, 12);
  const start = Math.max(0, lastFull - 24);
  const offShares = normalize(official).shares;
  const you = fixedBase(ext.index, shares, lastFull);
  const avg = fixedBase(ext.index, offShares, lastFull);
  const data = ext.months.slice(start).flatMap((m, k) => [
    { m, date: toDate(m), v: you[start + k], who: "Your basket", hyp: start + k > lastFull },
    { m, date: toDate(m), v: avg[start + k], who: "Average basket", hyp: start + k > lastFull },
  ]);
  const end = ext.months.length - 1;
  return (
    <section className="border-t border-rule pt-6 pb-10">
      <div className="mb-1.5 flex gap-1.5">
        <Badge type="scenario" />
      </div>
      <h2 className="font-serif text-2xl font-medium text-ink sm:text-[28px]">What if? Twelve months ahead</h2>
      <p className="mt-1.5 max-w-3xl text-[15px] leading-relaxed text-ink-2">
        Set an assumed price change for each category over the next year. By default every category keeps rising at its
        latest annual rate. This is a hypothetical calculation, not a forecast: the forecasts are on the Forecasts page.
      </p>
      <div className="mt-4 grid gap-6 lg:grid-cols-[minmax(0,4fr)_minmax(0,8fr)]">
        <div>
          <div className="divide-y divide-rule border-y border-rule">
            {meta.divisions.map((d) => (
              <label key={d} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2 py-1.5 text-sm text-ink">
                {meta.labels[d]}
                <span className="flex items-center gap-1">
                  <input
                    type="number"
                    step={1}
                    value={rates[d]}
                    onChange={(e) => setRates((r) => ({ ...r, [d]: e.target.value === "" ? 0 : Number(e.target.value) }))}
                    className="num w-20 rounded-md border border-rule bg-surface px-2 py-0.5 text-right text-sm"
                    aria-label={`${meta.labels[d]} assumed annual change, %`}
                  />
                  <span className="text-xs text-muted">%/yr</span>
                </span>
              </label>
            ))}
          </div>
          <div className="mt-2 flex gap-2 text-xs">
            <button onClick={() => setRates(latest)} className="rounded border border-rule px-2 py-1 text-ink-2 hover:bg-hover">
              Latest rates
            </button>
            <button onClick={() => setRates(Object.fromEntries(meta.divisions.map((d) => [d, 0])))} className="rounded border border-rule px-2 py-1 text-ink-2 hover:bg-hover">
              No change
            </button>
            <button onClick={() => setRates((r) => ({ ...r, CP04: r.CP04 + 20, CP07: r.CP07 + 10 }))} className="rounded border border-rule px-2 py-1 text-ink-2 hover:bg-hover">
              Add an energy shock
            </button>
          </div>
        </div>
        <div>
          <p className="font-serif text-xl text-ink">
            Under these assumptions your basket would cost <span className="num">{pct(you[end] != null ? you[end]! - 100 : null)}</span> more in{" "}
            {monthLabel(ext.months[end])} than in {monthLabel(months[lastFull])}; the average basket{" "}
            <span className="num">{pct(avg[end] != null ? avg[end]! - 100 : null)}</span>.
          </p>
          <PlotFigure
            label="Hypothetical scenario path"
            deps={[JSON.stringify(rates), JSON.stringify(shares)]}
            make={(width) => ({
              width,
              height: 280,
              marginRight: width < 600 ? 110 : 140,
              x: { type: "utc", label: null },
              y: { label: `Index, ${monthLabel(months[lastFull])} = 100`, grid: true },
              marks: [
                Plot.rectX([{ a: toDate(ext.months[lastFull]), b: toDate(ext.months[end]) }], { x1: "a", x2: "b", fill: "var(--badge-hypo)", fillOpacity: 0.5 }),
                Plot.text([{ x: toDate(ext.months[lastFull]) }], { x: "x", frameAnchor: "top", textAnchor: "start", dx: 6, dy: 4, text: () => "Hypothetical", fill: "var(--badge-hypo-ink)" }),
                Plot.gridY({ ...GRID }),
                Plot.ruleY([100], { stroke: "var(--ink-2)" }),
                Plot.lineY(data.filter((d) => d.who === "Average basket" && !d.hyp), { x: "date", y: "v", stroke: "var(--muted)", strokeWidth: 2 }),
                Plot.lineY(data.filter((d) => d.who === "Average basket" && (d.hyp || d.m === months[lastFull])), { x: "date", y: "v", stroke: "var(--muted)", strokeWidth: 2, strokeDasharray: "5,4" }),
                Plot.lineY(data.filter((d) => d.who === "Your basket" && !d.hyp), { x: "date", y: "v", stroke: "var(--c-neig)", strokeWidth: 2.5 }),
                Plot.lineY(data.filter((d) => d.who === "Your basket" && (d.hyp || d.m === months[lastFull])), { x: "date", y: "v", stroke: "var(--c-neig)", strokeWidth: 2.5, strokeDasharray: "5,4" }),
                ...endLabels(data.filter((d) => d.m === ext.months[end]), (d) => `${d.who} ${num(d.v, 1)}`),
              ],
            })}
          />
          <p className="mt-2 text-xs leading-relaxed text-muted">
            Hypothetical scenario — not a forecast. Category indices for {name} are extended from {monthLabel(months[lastFull])} at the assumed annual
            rates (compounded monthly); “average basket” uses the official HICP weights of the latest year as a fixed basket. Dashed lines are assumptions.
          </p>
        </div>
      </div>
    </section>
  );
}

function MethodNote() {
  return (
    <section className="border-t border-rule pt-6 pb-4 text-sm leading-relaxed text-ink-2">
      <h2 className="mb-2 font-serif text-xl text-ink">How the basket is calculated</h2>
      <p className="max-w-3xl">
        Re-weighted yearly (chained): each month, I<sub>t</sub> = I<sub>Dec</sub> × Σ w<sub>i</sub> · I<sub>i,t</sub> / I<sub>i,Dec</sub>, linked
        through every December, with your shares w<sub>i</sub> summing to 1. Fixed basket: I<sub>t</sub> = 100 × Σ w<sub>i</sub> · I<sub>i,t</sub> / I
        <sub>i,base</sub>. Both use Eurostat's 13 official category indices. With the official weights, the re-weighted version reproduces the published
        all-items rate within about 0.1 percentage point for all countries except Italy. Categories are broad averages: your own prices within a category
        (your rent, your supermarket) may move differently.
      </p>
    </section>
  );
}
