import * as Plot from "@observablehq/plot";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Badge } from "@/components/badge";
import { ChartCard, DataTable, Segmented, Select } from "@/components/chart-card";
import { GRID, PlotFigure } from "@/components/plot-figure";
import { RATE_PIVOT } from "@/lib/colors";
import { type GeoData, type Meta, useJson } from "@/lib/data";
import { monthLabel, num, pct, pp, toDate } from "@/lib/format";

// Shapes written by src/pricelens/quintile.py
export type QuintileData = {
  geo: string;
  waves: number[];
  months: string[];
  yoy: Record<string, Record<string, (number | null)[]>>;
  contrib: { months: string[]; values: Record<string, Record<string, Record<string, (number | null)[]>>> };
  shares: Record<string, Record<string, Record<string, number>>>;
  imputed_rent_per_1000: Record<string, Record<string, number | null>>;
};
type Summary = { latest: { geo: string; wave: number; month: string; q1: number | null; q5: number | null; gap: number | null }[] };

const Q = ["QU1", "QU2", "QU3", "QU4", "QU5"];
const QLABEL: Record<string, string> = {
  QU1: "Lowest-income fifth",
  QU2: "Second fifth",
  QU3: "Middle fifth",
  QU4: "Fourth fifth",
  QU5: "Highest-income fifth",
};
const QCOLOR: Record<string, string> = { QU1: "var(--q1)", QU2: "var(--q2)", QU3: "var(--q3)", QU4: "var(--q4)", QU5: "var(--q5)" };

export function QuintilesPage({ meta }: { meta: Meta }) {
  const { data: sum } = useJson<Summary>("quintiles/summary.json");
  const [params, setParams] = useSearchParams();
  const usable = sum ? [...new Set(sum.latest.map((r) => r.geo))] : [];
  const req = params.get("geo");
  const geo = req && usable.includes(req) ? req : usable.includes("DE") ? "DE" : usable[0];
  const setGeo = (g: string) => setParams((p) => (p.set("geo", g), p), { replace: true });
  const { data: qd } = useJson<QuintileData>(geo ? `quintiles/${geo}.json` : null);
  const { data: gd } = useJson<GeoData>(geo ? `geo/${geo}.json` : null);
  const name = (c: string) => meta.geos.find((g) => g.code === c)?.name ?? c;
  if (!sum || !geo) return <div className="py-16 text-sm text-muted">Loading…</div>;
  const missing = meta.geos.filter((g) => !g.aggregate && !usable.includes(g.code)).map((g) => g.name);
  return (
    <div className="pt-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-1.5">
          <Badge type="quintile" />
          <Badge type="official" text="Official prices" />
        </div>
        <Select label="Country" value={geo} onChange={setGeo} options={usable.map((g) => ({ value: g, label: name(g) })).sort((a, b) => a.label.localeCompare(b.label))} />
      </div>
      {qd && gd && <Body meta={meta} qd={qd} gd={gd} sum={sum} name={name(geo)} nameOf={name} setGeo={setGeo} />}
      <section className="border-t border-rule pt-6 pb-4 text-sm leading-relaxed text-ink-2">
        <h2 className="mb-2 font-serif text-xl text-ink">How this is calculated, and its limits</h2>
        <ul className="max-w-3xl list-disc space-y-1.5 pl-5">
          <li>
            Spending patterns come from Eurostat's Household Budget Survey (table hbs_str_t223): the average share of spending on each category for each
            fifth of households ranked by income. They are averages for large groups, not any real household.
          </li>
          <li>
            The survey counts the imputed rent of owner-occupiers as spending; the HICP does not. PriceLens removes it and rescales the other shares. The
            survey's 1999 classification is mapped to the current 13 HICP categories (postal services to transport, IT and audio-visual equipment to
            information and communication, insurance and financial services to their own category).
          </li>
          <li>
            Each group's shares are price-updated to every December and chained exactly like the official index, using the official category prices of
            the country. Prices are national averages: the same category may cost different households different amounts.
          </li>
          <li>
            Surveys are from 2015 and 2020; 2020 was a pandemic year with unusual spending. Switch the survey year to see how much the result depends on
            it. Not available: {missing.join(", ")} (no complete survey data in this table).
          </li>
        </ul>
      </section>
    </div>
  );
}

function Body({
  meta,
  qd,
  gd,
  sum,
  name,
  nameOf,
  setGeo,
}: {
  meta: Meta;
  qd: QuintileData;
  gd: GeoData;
  sum: Summary;
  name: string;
  nameOf: (c: string) => string;
  setGeo: (g: string) => void;
}) {
  const [waveSel, setWave] = useState<string | null>(null);
  const wave = waveSel && qd.waves.map(String).includes(waveSel) ? waveSel : String(Math.max(...qd.waves));
  const [range, setRange] = useState<"10y" | "all">("10y");
  const y = qd.yoy[wave];
  let last = qd.months.length - 1;
  while (last > 0 && (y.QU1[last] == null || y.QU5[last] == null)) last--;
  const first = range === "10y" ? Math.max(0, last - 119) : 0;
  const ms = qd.months.slice(first, last + 1);
  const lines = Q.flatMap((q) => ms.map((m, k) => ({ q, label: QLABEL[q], date: toDate(m), m, v: y[q][first + k] })));
  const official = ms.map((m) => ({ date: toDate(m), m, v: gd.yoy.TOTAL[gd.months.indexOf(m)] }));
  const gap = ms.map((m, k) => ({ date: toDate(m), m, v: y.QU1[first + k] != null && y.QU5[first + k] != null ? y.QU1[first + k]! - y.QU5[first + k]! : null }));
  const q1 = y.QU1[last], q5 = y.QU5[last];
  const peak = gap.reduce((a, b) => ((b.v ?? -99) > (a.v ?? -99) ? b : a), gap[0]);

  return (
    <>
      <h1 className="mt-3 max-w-4xl font-serif text-4xl leading-[1.1] font-medium tracking-tight text-ink sm:text-5xl">
        In {monthLabel(qd.months[last], true)}, prices in {name} rose <span className="num">{pct(q1)}</span> for the lowest-income fifth of households and{" "}
        <span className="num">{pct(q5)}</span> for the highest-income fifth.
      </h1>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        {qd.waves.length > 1 && (
          <Segmented label="Survey year" value={wave} onChange={setWave} options={qd.waves.map((w) => ({ value: String(w), label: `Survey ${w}` }))} />
        )}
        <span className="text-xs text-muted">Spending patterns from the {wave} Household Budget Survey.</span>
      </div>

      <ChartCard
        badges={["quintile", "official"]}
        title="Inflation by income group"
        subtitle={<>Annual inflation of the average basket of each fifth of households, ranked by income. The grey line is the official all-items rate.</>}
        controls={<Segmented label="Range" value={range} onChange={setRange} options={[{ value: "10y", label: "10 years" }, { value: "all", label: "Since 2002" }]} />}
        footnote={`${name}. Income-group baskets computed by PriceLens from Eurostat HICP category indices and HBS ${wave} spending shares (imputed rent removed), chained annually. Official line: published HICP annual rate.`}
        table={
          <DataTable
            head={["Month", ...Q.map((q) => QLABEL[q]), "Official"]}
            rows={[...ms].reverse().map((m) => [monthLabel(m), ...Q.map((q) => pct(y[q][qd.months.indexOf(m)])), pct(gd.yoy.TOTAL[gd.months.indexOf(m)])])}
          />
        }
      >
        <div className="mb-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-2" aria-hidden>
          {Q.map((q) => (
            <span key={q} className="inline-flex items-center gap-1.5">
              <span className="inline-block h-0.5 w-4" style={{ background: QCOLOR[q], height: 3 }} />
              {QLABEL[q]} <span className="num text-ink">{pct(y[q][last])}</span>
            </span>
          ))}
          <span className="inline-flex items-center gap-1.5">
            <span className="inline-block w-4 bg-[var(--muted)]" style={{ height: 3 }} />
            Official <span className="num text-ink">{pct(gd.yoy.TOTAL[gd.months.indexOf(qd.months[last])])}</span>
          </span>
        </div>
        <PlotFigure
          label={`Annual inflation by income group, ${name}`}
          deps={[qd.geo, wave, range]}
          make={(width) => ({
            width,
            height: 340,
            marginRight: width < 600 ? 10 : 140,
            x: { type: "utc", label: null },
            y: { label: "% vs a year earlier", grid: true },
            color: { domain: Q, range: Q.map((q) => QCOLOR[q]) },
            marks: [
              Plot.gridY({ ...GRID }),
              Plot.ruleY([0], { stroke: "var(--ink-2)" }),
              Plot.ruleY([RATE_PIVOT], { stroke: "var(--muted)", strokeOpacity: 0.6 }),
              Plot.lineY(official, { x: "date", y: "v", stroke: "var(--muted)", strokeWidth: 1.5 }),
              Plot.lineY(lines, { x: "date", y: "v", stroke: "q", z: "q", strokeWidth: (d: { q: string }) => (d.q === "QU1" || d.q === "QU5" ? 2.25 : 1.25) }),
              ...(width >= 600
                ? [
                    Plot.text(lines.filter((d) => d.m === ms[ms.length - 1] && (d.q === "QU1" || d.q === "QU5")), {
                      x: "date",
                      y: "v",
                      text: (d: { q: string }) => (d.q === "QU1" ? "Lowest fifth" : "Highest fifth"),
                      textAnchor: "start",
                      dx: 6,
                      fill: "var(--ink)",
                      fontWeight: 600,
                    }),
                  ]
                : []),
              Plot.ruleX(ms.map((m) => ({ date: toDate(m) })), Plot.pointerX({ x: "date", stroke: "var(--ink-2)" })),
              Plot.tip(
                ms.map((m, k) => ({ date: toDate(m), m, k })),
                Plot.pointerX({
                  x: "date",
                  frameAnchor: "top",
                  title: (d: { m: string; k: number }) =>
                    [monthLabel(d.m), ...Q.map((q) => `${QLABEL[q]}: ${pct(y[q][first + d.k])}`), `Official: ${pct(gd.yoy.TOTAL[gd.months.indexOf(d.m)])}`].join("\n"),
                }),
              ),
            ],
          })}
        />
      </ChartCard>

      <ChartCard
        badges={["quintile"]}
        title="The gap between the lowest and highest incomes"
        subtitle={
          <>
            Lowest-income fifth minus highest-income fifth, in percentage points. Above zero, poorer households faced higher inflation.
            {peak?.v != null && peak.v > 0.5 && ` The gap peaked at ${pp(peak.v, 1)} pp in ${monthLabel(peak.m)}.`}
          </>
        }
        footnote={`${name}, HBS ${wave} spending shares. A gap of 1 pp means the lowest-income basket became 1% dearer than the highest-income basket over the year.`}
        table={<DataTable head={["Month", "Gap (pp)"]} rows={[...gap].reverse().map((g) => [monthLabel(g.m), pp(g.v, 2)])} />}
      >
        <PlotFigure
          label={`Inflation gap between lowest and highest income fifths, ${name}`}
          deps={[qd.geo, wave, range]}
          make={(width) => ({
            width,
            height: 220,
            x: { type: "utc", label: null },
            y: { label: "pp", grid: true },
            marks: [
              Plot.gridY({ ...GRID }),
              Plot.areaY(gap, { x: "date", y: (d: { v: number | null }) => (d.v != null && d.v > 0 ? d.v : 0), fill: "var(--div-hi2)", fillOpacity: 0.35 }),
              Plot.areaY(gap, { x: "date", y: (d: { v: number | null }) => (d.v != null && d.v < 0 ? d.v : 0), fill: "var(--div-lo2)", fillOpacity: 0.35 }),
              Plot.lineY(gap, { x: "date", y: "v", stroke: "var(--ink)", strokeWidth: 1.5 }),
              Plot.ruleY([0], { stroke: "var(--ink-2)" }),
              Plot.tip(gap, Plot.pointerX({ x: "date", y: "v", title: (d: { m: string; v: number | null }) => `${monthLabel(d.m)}: ${pp(d.v, 2)} pp` })),
            ],
          })}
        />
      </ChartCard>

      <Drivers meta={meta} qd={qd} wave={wave} name={name} />
      <EuStrip sum={sum} wave={Number(wave)} geo={qd.geo} nameOf={nameOf} setGeo={setGeo} />
      <SharesTable meta={meta} qd={qd} wave={wave} />
    </>
  );
}

function Drivers({ meta, qd, wave, name }: { meta: Meta; qd: QuintileData; wave: string; name: string }) {
  const c = qd.contrib;
  let k = c.months.length - 1;
  const v = c.values[wave];
  while (k > 0 && meta.divisions.some((d) => v.QU1[d][k] == null || v.QU5[d][k] == null)) k--;
  const rows = meta.divisions
    .map((d) => ({ label: meta.labels[d], q1: v.QU1[d][k] ?? 0, q5: v.QU5[d][k] ?? 0 }))
    .map((r) => ({ ...r, diff: r.q1 - r.q5 }))
    .sort((a, b) => b.diff - a.diff);
  return (
    <ChartCard
      badges={["quintile"]}
      title="What drives the gap"
      subtitle={<>Contribution of each category to the lowest-income fifth's annual inflation minus its contribution for the highest-income fifth, {monthLabel(c.months[k], true)}.</>}
      footnote={`${name}, HBS ${wave}. Contributions use the same chain-index decomposition as the Atlas; the differences add up to the gap. Red pushes the lowest-income fifth's rate up relative to the highest.`}
      table={<DataTable head={["Category", "Lowest fifth (pp)", "Highest fifth (pp)", "Difference (pp)"]} rows={rows.map((r) => [r.label, pp(r.q1, 2), pp(r.q5, 2), pp(r.diff, 2)])} />}
    >
      <PlotFigure
        label="Category contributions to the income-group inflation gap"
        deps={[qd.geo, wave]}
        make={(width) => ({
          width,
          height: 28 * rows.length + 40,
          marginLeft: width < 600 ? 150 : 200,
          marginRight: 50,
          x: { label: "pp of the gap", grid: true },
          y: { domain: rows.map((r) => r.label), label: null, tickSize: 0 },
          marks: [
            Plot.gridX({ ...GRID }),
            Plot.barX(rows, { x: "diff", y: "label", fill: (d: { diff: number }) => (d.diff >= 0 ? "var(--div-hi2)" : "var(--div-lo2)"), insetTop: 3, insetBottom: 3, rx: 2 }),
            Plot.ruleX([0], { stroke: "var(--ink-2)" }),
            Plot.text(rows, { x: "diff", y: "label", text: (d: { diff: number }) => pp(d.diff, 2), textAnchor: "start", dx: 5, fill: "var(--ink-2)", filter: (d: { diff: number }) => d.diff >= 0 }),
            Plot.text(rows, { x: () => 0, y: "label", text: (d: { diff: number }) => pp(d.diff, 2), textAnchor: "start", dx: 5, fill: "var(--ink-2)", filter: (d: { diff: number }) => d.diff < 0 }),
          ],
        })}
      />
    </ChartCard>
  );
}

function EuStrip({ sum, wave, geo, nameOf, setGeo }: { sum: Summary; wave: number; geo: string; nameOf: (c: string) => string; setGeo: (g: string) => void }) {
  const rows = sum.latest
    .filter((r) => r.wave === wave && r.gap != null)
    .map((r) => ({ ...r, name: nameOf(r.geo) }))
    .sort((a, b) => b.gap! - a.gap!);
  const month = rows[0]?.month;
  return (
    <ChartCard
      badges={["quintile"]}
      title="Where the gap is widest"
      subtitle={<>Lowest-income minus highest-income fifth, latest month, every country with {wave} survey data.</>}
      footnote={`HBS ${wave} spending shares; ${month ? monthLabel(month) : ""}. Countries are ranked by the gap. Click a bar to switch country.`}
      table={<DataTable head={["Country", "Lowest fifth", "Highest fifth", "Gap (pp)"]} rows={rows.map((r) => [r.name, pct(r.q1), pct(r.q5), pp(r.gap, 2)])} />}
    >
      <div
        onClick={(e) => {
          const t = (e.target as SVGElement).closest("[data-geo]");
          if (t) setGeo(t.getAttribute("data-geo")!);
        }}
      >
        <PlotFigure
          label="Income-group inflation gap by country"
          deps={[wave, geo, rows.length]}
          make={(width) => ({
            width,
            height: 22 * rows.length + 40,
            marginLeft: 110,
            marginRight: 50,
            x: { label: "pp", grid: true },
            y: { domain: rows.map((r) => r.name), label: null, tickSize: 0 },
            marks: [
              Plot.gridX({ ...GRID }),
              Plot.barX(rows, {
                x: "gap",
                y: "name",
                fill: (d: { geo: string }) => (d.geo === geo ? "var(--ink)" : "var(--muted)"),
                fillOpacity: (d: { geo: string }) => (d.geo === geo ? 1 : 0.6),
                insetTop: 2,
                insetBottom: 2,
                rx: 2,
                render: (index, scales, values, dims, ctx, next) => {
                  const g = next!(index, scales, values, dims, ctx)!;
                  g.querySelectorAll("rect").forEach((r, i) => {
                    r.setAttribute("data-geo", rows[index[i]].geo);
                    r.style.cursor = "pointer";
                  });
                  return g;
                },
              }),
              Plot.ruleX([0], { stroke: "var(--ink-2)" }),
              Plot.text(rows, { x: "gap", y: "name", text: (d: { gap: number }) => pp(d.gap, 1), textAnchor: "start", dx: 5, fill: "var(--ink-2)", filter: (d: { gap: number }) => d.gap >= 0 }),
              Plot.text(rows, { x: () => 0, y: "name", text: (d: { gap: number }) => pp(d.gap, 1), textAnchor: "start", dx: 5, fill: "var(--ink-2)", filter: (d: { gap: number }) => d.gap < 0 }),
            ],
          })}
        />
      </div>
    </ChartCard>
  );
}

function SharesTable({ meta, qd, wave }: { meta: Meta; qd: QuintileData; wave: string }) {
  const sh = qd.shares[wave];
  const imp = qd.imputed_rent_per_1000[wave];
  return (
    <section className="border-t border-rule pt-6 pb-10">
      <h2 className="font-serif text-2xl font-medium text-ink">The baskets</h2>
      <p className="mt-1.5 max-w-3xl text-[15px] leading-relaxed text-ink-2">
        Share of spending on each category by income group (survey {wave}), after removing owner-occupiers' imputed rent, which the survey counts as
        spending but the HICP does not.
      </p>
      <div className="mt-3 overflow-x-auto rounded border border-rule">
        <DataTable
          head={["Category", ...Q.map((q) => QLABEL[q])]}
          rows={[
            ...meta.divisions.map((d) => [meta.labels[d], ...Q.map((q) => `${num(100 * (sh[q][d] ?? 0))}%`)]),
            ["Imputed rent removed (‰ of survey spending)", ...Q.map((q) => (imp[q] == null ? "–" : num(imp[q], 0)))],
          ]}
        />
      </div>
    </section>
  );
}
