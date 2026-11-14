import * as Plot from "@observablehq/plot";
import { useState } from "react";
import { Badge } from "@/components/badge";
import { ChartCard, DataTable, Segmented } from "@/components/chart-card";
import { GRID, PlotFigure } from "@/components/plot-figure";
import { RATE_PIVOT } from "@/lib/colors";
import { type GeoData, useJson } from "@/lib/data";
import { monthLabel, pct, pp, toDate } from "@/lib/format";

// Shape written by src/pricelens/us.py
type USData = {
  source: string;
  latest_month: string;
  missing_months: string[];
  labels: Record<string, string>;
  parts: string[];
  groups: string[];
  months: string[];
  yoy: Record<string, (number | null)[]>;
  weights: Record<string, Record<string, number>>;
  contrib: { months: string[]; values: Record<string, (number | null)[]>; residual: (number | null)[] };
  quality: { max_abs_residual_pp: number; p95_abs_residual_pp: number; fit_rmse_by_year: Record<string, number> };
};

// Same identity colours as the euro-area aggregates (energy, food, goods, services); validated palette.
const PART_COLOR: Record<string, string> = { SA0E: "var(--c-nrg)", SAF1: "var(--c-food)", SACL1E: "var(--c-neig)", SASLE: "var(--c-serv)" };

export function USPage() {
  const { data: us } = useJson<USData>("us.json");
  const { data: ea } = useJson<GeoData>("geo/EA.json");
  if (!us || !ea) return <div className="py-16 text-sm text-muted">Loading…</div>;
  const n = us.months.length;
  let k = n - 1;
  while (k > 0 && us.yoy.SA0[k] == null) k--;
  const latestMissing = k < n - 1;
  return (
    <div className="pt-10">
      <div className="flex gap-1.5">
        <Badge type="official" text="Official · BLS CPI-U" />
      </div>
      <h1 className="mt-3 max-w-4xl font-serif text-4xl leading-[1.1] font-medium tracking-tight text-ink sm:text-5xl">
        Prices in the United States were <span className="num">{pct(us.yoy.SA0[k])}</span> higher in {monthLabel(us.months[k], true)} than a year earlier.
      </h1>
      <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-ink-2">
        The US consumer price index (CPI-U) is compiled by the Bureau of Labor Statistics with its own methods. It is shown here on its own page and never
        mixed into European figures.
        {latestMissing && (
          <>
            {" "}
            The annual rate for {monthLabel(us.months[n - 1])} cannot be calculated from published data: BLS published no index for{" "}
            {us.missing_months.map((m) => monthLabel(m)).join(", ")} (federal government shutdown), and PriceLens does not fill the gap.
          </>
        )}
      </p>
      <Contributions us={us} />
      <Comparison us={us} ea={ea} />
      <Groups us={us} />
      <section className="border-t border-rule pt-6 pb-4 text-sm leading-relaxed text-ink-2">
        <h2 className="mb-2 font-serif text-xl text-ink">About these numbers</h2>
        <ul className="max-w-3xl list-disc space-y-1.5 pl-5">
          <li>Source: {us.source}. US government data, public domain; "Source: U.S. Bureau of Labor Statistics".</li>
          <li>
            Contributions use December weights that PriceLens <em>derives</em> from the published indices (the CPI-U is linked each December, so each
            year's weights follow from its monthly index identity). BLS publishes official relative importances on its website, which PriceLens cannot
            fetch automatically. With the derived weights, the contributions add up to the published annual rate within {pp(us.quality.p95_abs_residual_pp, 2, false)} pp
            (95th percentile) since 2001. Before 2007 BLS indices have one decimal, so earlier weights are less precise.
          </li>
          <li>Missing months are shown as gaps, never interpolated.</li>
        </ul>
      </section>
    </div>
  );
}

function Contributions({ us }: { us: USData }) {
  const [range, setRange] = useState<"3y" | "10y">("10y");
  const c = us.contrib;
  const from = Math.max(0, c.months.length - (range === "3y" ? 36 : 120));
  const ms = c.months.slice(from);
  const rows = ms.flatMap((m, i) => us.parts.map((p) => ({ date: toDate(m), m, code: p, value: c.values[p][from + i] }))).filter((r) => r.value != null);
  const tot = ms.map((m) => ({ date: toDate(m), m, v: us.yoy.SA0[us.months.indexOf(m)] }));
  const lastIdx = c.months.length - 1;
  return (
    <ChartCard
      badges={["official"]}
      title="What is driving US inflation"
      subtitle="Annual CPI inflation split into energy, food, core goods and core services, in percentage points. The line is the published rate."
      controls={<Segmented label="Range" value={range} onChange={setRange} options={[{ value: "3y", label: "3 years" }, { value: "10y", label: "10 years" }]} />}
      footnote={`BLS CPI-U, not seasonally adjusted. Contributions computed by PriceLens with the chain-index decomposition and derived December weights; months without published data are blank.`}
      table={
        <DataTable
          head={["Month", ...us.parts.map((p) => us.labels[p]), "Published rate", "Residual"]}
          rows={[...ms].reverse().map((m) => {
            const i = c.months.indexOf(m);
            return [monthLabel(m), ...us.parts.map((p) => pp(c.values[p][i], 2)), pct(us.yoy.SA0[us.months.indexOf(m)]), pp(c.residual[i], 2)];
          })}
        />
      }
    >
      <div className="mb-3 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-ink-2" aria-hidden>
        {us.parts.map((p) => (
          <span key={p} className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: PART_COLOR[p] }} />
            {us.labels[p]} <span className="num text-ink">{pp(c.values[p][lastIdx], 2)} pp</span>
          </span>
        ))}
      </div>
      <PlotFigure
        label="Contributions to US CPI inflation"
        deps={[range]}
        make={(width) => ({
          width,
          height: 340,
          x: { type: "utc", label: null },
          y: { label: "pp", grid: true },
          color: { domain: us.parts, range: us.parts.map((p) => PART_COLOR[p]) },
          marks: [
            Plot.gridY({ ...GRID }),
            Plot.ruleY([RATE_PIVOT], { stroke: "var(--muted)" }),
            Plot.rectY(rows, Plot.stackY({ x: "date", interval: "month", y: "value", fill: "code", order: us.parts, insetLeft: 0.75, insetRight: 0.75 })),
            Plot.ruleY([0], { stroke: "var(--ink-2)" }),
            Plot.lineY(tot, { x: "date", y: "v", stroke: "var(--ink)", strokeWidth: 2 }),
            Plot.tip(tot, Plot.pointerX({ x: "date", y: "v", title: (d: (typeof tot)[number]) => [`${monthLabel(d.m)} — ${pct(d.v)}`, ...us.parts.map((p) => `${us.labels[p]}: ${pp(c.values[p][c.months.indexOf(d.m)], 2)} pp`)].join("\n") })),
          ],
        })}
      />
    </ChartCard>
  );
}

function Comparison({ us, ea }: { us: USData; ea: GeoData }) {
  const from = us.months.indexOf("2016-01");
  const ms = us.months.slice(from);
  const rows = [
    ...ms.map((m) => ({ who: "US CPI, all items", date: toDate(m), m, v: us.yoy.SA0[us.months.indexOf(m)] })),
    ...ms.map((m) => ({ who: "US CPI, less shelter", date: toDate(m), m, v: us.yoy.SA0L2[us.months.indexOf(m)] })),
    ...ms.map((m) => ({ who: "Euro area HICP", date: toDate(m), m, v: ea.yoy.TOTAL[ea.months.indexOf(m)] ?? null })),
  ];
  const who = ["US CPI, all items", "US CPI, less shelter", "Euro area HICP"];
  const color = ["var(--c-neig)", "var(--muted)", "var(--ink)"];
  return (
    <ChartCard
      badges={["official"]}
      title="The US and the euro area, side by side"
      subtitle="Annual inflation. The two indices are built differently; the clearest difference is housing: the US CPI includes owners' equivalent rent (roughly a quarter of the index), the HICP leaves owner-occupied housing out. The grey line removes all shelter from the US CPI."
      footnote="BLS CPI-U and Eurostat HICP, both not seasonally adjusted, each as published. Comparisons are indicative only: coverage, weights, quality adjustment and housing treatment differ. Gaps are months without published data."
      table={<DataTable head={["Month", ...who]} rows={[...ms].reverse().map((m) => [monthLabel(m), ...who.map((w) => pct(rows.find((r) => r.m === m && r.who === w)?.v ?? null))])} />}
    >
      <div className="mb-3 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-ink-2" aria-hidden>
        {who.map((w, i) => (
          <span key={w} className="inline-flex items-center gap-1.5">
            <span className="inline-block w-4" style={{ height: 3, background: color[i] }} />
            {w}
          </span>
        ))}
      </div>
      <PlotFigure
        label="US CPI and euro area HICP annual inflation"
        deps={[ms.length]}
        make={(width) => ({
          width,
          height: 300,
          x: { type: "utc", label: null },
          y: { label: "% vs a year earlier", grid: true },
          color: { domain: who, range: color },
          marks: [
            Plot.gridY({ ...GRID }),
            Plot.ruleY([0], { stroke: "var(--ink-2)" }),
            Plot.lineY(rows, { x: "date", y: "v", stroke: "who", z: "who", strokeWidth: (d: { who: string }) => (d.who === "US CPI, less shelter" ? 1.5 : 2) }),
            Plot.tip(rows.filter((r) => r.who === "US CPI, all items"), Plot.pointerX({ x: "date", y: "v", title: (d: { m: string }) => [monthLabel(d.m), ...who.map((w) => `${w}: ${pct(rows.find((r) => r.m === d.m && r.who === w)?.v ?? null)}`)].join("\n") })),
          ],
        })}
      />
    </ChartCard>
  );
}

function Groups({ us }: { us: USData }) {
  const from = Math.max(0, us.months.length - 120);
  const ms = us.months.slice(from);
  const cols = 4;
  const data = us.groups.flatMap((g, i) => ms.map((m) => ({ g, title: us.labels[g], fx: i % cols, fy: Math.floor(i / cols), date: toDate(m), m, v: us.yoy[g][us.months.indexOf(m)] })));
  const titles = us.groups.map((g, i) => ({ fx: i % cols, fy: Math.floor(i / cols), t: us.labels[g] }));
  return (
    <ChartCard
      badges={["official"]}
      title="Eight major groups, ten years"
      subtitle="Annual inflation in each BLS major expenditure group. All panels share one axis."
      footnote="BLS CPI-U major groups (US city average, not seasonally adjusted)."
    >
      <PlotFigure
        label="US CPI major groups"
        deps={[ms.length]}
        make={(width) => {
          const c = width < 640 ? 2 : cols;
          const d2 = data.map((d) => {
            const i = us.groups.indexOf(d.g);
            return { ...d, fx: i % c, fy: Math.floor(i / c) };
          });
          const t2 = titles.map((t, i) => ({ ...t, fx: i % c, fy: Math.floor(i / c) }));
          return {
            width,
            height: Math.ceil(us.groups.length / c) * 170 + 30,
            marginTop: 22,
            fx: { axis: null, padding: 0.12 },
            fy: { axis: null, padding: 0.3 },
            x: { type: "utc", ticks: 2, label: null },
            y: { grid: true, label: null, ticks: 4, tickFormat: (v: number) => `${v}%` },
            marks: [
              Plot.gridY({ ...GRID }),
              Plot.ruleY([0], { stroke: "var(--ink-2)", strokeWidth: 0.75 }),
              Plot.text(t2, { fx: "fx", fy: "fy", text: "t", frameAnchor: "top-left", dy: -14, fontWeight: 600, fill: "var(--ink)" }),
              Plot.lineY(d2, { fx: "fx", fy: "fy", x: "date", y: "v", stroke: "var(--ink)", strokeWidth: 1.75 }),
              Plot.tip(d2, Plot.pointerX({ fx: "fx", fy: "fy", x: "date", y: "v", title: (d: (typeof d2)[number]) => `${d.title}\n${monthLabel(d.m)}: ${pct(d.v)}` })),
            ],
          };
        }}
      />
    </ChartCard>
  );
}
