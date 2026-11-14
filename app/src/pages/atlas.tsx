import * as Plot from "@observablehq/plot";
import * as d3 from "d3";
import type { Feature, Geometry } from "geojson";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { feature } from "topojson-client";
import type { Topology } from "topojson-specification";
import { Badge } from "@/components/badge";
import { ChartCard, DataTable, Segmented, Select } from "@/components/chart-card";
import { GRID, PlotFigure } from "@/components/plot-figure";
import { AGG_COLOR, AGG_ORDER, RATE_DOMAIN, RATE_PIVOT, rateScheme } from "@/lib/colors";
import { type GeoData, type Meta, type Rates, isEstimated, rateOf, useJson } from "@/lib/data";
import { inGeo, monthLabel, pct, pp, toDate } from "@/lib/format";
import { ISO_NUM, NUM_TO_GEO } from "@/lib/geo";

type Props = { meta: Meta; rates: Rates };

function rateColor() {
  return {
    type: "diverging" as const,
    pivot: RATE_PIVOT,
    domain: RATE_DOMAIN,
    clamp: true,
    interpolate: d3.interpolateRgbBasis(rateScheme()),
  };
}

export function AtlasPage({ meta, rates }: Props) {
  const [params, setParams] = useSearchParams();
  const geo = params.get("geo") ?? "EA";
  const setGeo = (g: string) => setParams((p) => (p.set("geo", g), p), { replace: true });
  const { data: gd, error } = useJson<GeoData>(`geo/${geo}.json`);
  const { data: ea } = useJson<GeoData>(geo === "EA" ? "geo/EU27_2020.json" : "geo/EA.json");
  const name = (code: string) => meta.geos.find((g) => g.code === code)?.name ?? code;
  const geoOptions = meta.geos.map((g) => ({
    value: g.code,
    label: g.name,
    group: g.aggregate ? "Aggregates" : "Countries",
  }));

  return (
    <div>
      <Hero meta={meta} rates={rates} geo={geo} name={inGeo(geo, name(geo))} setGeo={setGeo} options={geoOptions} />
      {error && <p className="text-sm text-red-600">Could not load data: {error}</p>}
      {gd && <Contributions meta={meta} gd={gd} name={inGeo(geo, name(geo))} />}
      {gd && <Heatstrip meta={meta} gd={gd} name={name(geo)} />}
      <Ranking meta={meta} rates={rates} geo={geo} setGeo={setGeo} />
      {gd && ea && <Divisions meta={meta} gd={gd} ref_={ea} name={name(geo)} refName={name(ea.geo)} refPhrase={inGeo(ea.geo, name(ea.geo))} />}
    </div>
  );
}

// ------------------------------------------------------------------------------------------------ hero

function Hero({
  meta,
  rates,
  geo,
  name,
  setGeo,
  options,
}: {
  meta: Meta;
  rates: Rates;
  geo: string;
  name: string;
  setGeo: (g: string) => void;
  options: { value: string; label: string; group?: string }[];
}) {
  const full = meta.latest_full_month;
  const flash = meta.flash_month;
  const flashVal = flash ? rateOf(rates, geo, "TOTAL", flash) : null;
  const hasFlash = flash != null && flashVal != null && isEstimated(rates, geo, "TOTAL", flash);
  const headMonth = hasFlash ? flash! : full;
  const head = rateOf(rates, geo, "TOTAL", headMonth);
  const prevIdx = rates.months.indexOf(headMonth) - 1;
  const prev = rateOf(rates, geo, "TOTAL", rates.months[prevIdx]);
  return (
    <section className="pt-10 pb-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-ink-2">Harmonised index of consumer prices · annual rate of change</p>
        <Select label="Country or area" value={geo} onChange={setGeo} options={options} />
      </div>
      <h1 className="mt-4 max-w-4xl font-serif text-4xl leading-[1.1] font-medium tracking-tight text-ink sm:text-5xl">
        Prices in {name} were <span className="num">{pct(head)}</span> higher in {monthLabel(headMonth, true)} than a year
        earlier.
      </h1>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-ink-2">
        <Badge type={hasFlash ? "flash" : "official"} />
        <span>
          {prev != null && head != null && (
            <>
              {head > prev ? "Up" : head < prev ? "Down" : "Unchanged"} from {pct(prev)} in{" "}
              {monthLabel(rates.months[prevIdx])}.{" "}
            </>
          )}
          {hasFlash
            ? `Flash estimate published at the end of the month; the full release for ${monthLabel(flash!)} follows mid-month.`
            : "Final release."}
        </span>
      </div>
      <div className="mt-8 grid grid-cols-2 gap-px overflow-hidden rounded-lg border border-rule bg-rule sm:grid-cols-4">
        {AGG_ORDER.map((c) => {
          const v = rateOf(rates, geo, c, headMonth) ?? rateOf(rates, geo, c, full);
          const m = rateOf(rates, geo, c, headMonth) != null ? headMonth : full;
          return (
            <div key={c} className="bg-surface p-4">
              <div className="flex items-center gap-2 text-xs text-ink-2">
                <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: AGG_COLOR[c] }} />
                {meta.labels[c]}
              </div>
              <div className="num mt-1.5 font-serif text-3xl text-ink">{pct(v)}</div>
              <div className="text-xs text-muted">{monthLabel(m)}</div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ------------------------------------------------------------------------------------------------ contributions

type Range = "3y" | "10y" | "all";
const RANGE_MONTHS: Record<Range, number> = { "3y": 36, "10y": 120, all: 10000 };

function Contributions({ meta, gd, name }: { meta: Meta; gd: GeoData; name: string }) {
  const [range, setRange] = useState<Range>("10y");
  const c = gd.contrib;
  const n = c.months.length;
  const from = Math.max(0, n - RANGE_MONTHS[range]);
  const months = c.months.slice(from);
  const rows = months.flatMap((m, k) =>
    AGG_ORDER.map((code) => ({ date: toDate(m), month: m, code, value: c.values[code][from + k] })),
  );
  const yoyAt = (m: string) => gd.yoy.TOTAL[gd.months.indexOf(m)];
  const totals = months.map((m, k) => ({
    date: toDate(m),
    month: m,
    total: yoyAt(m),
    residual: c.residual[from + k],
    parts: AGG_ORDER.map((code) => c.values[code][from + k]),
  }));
  const last = totals[totals.length - 1];
  const flash = meta.flash_month === last?.month;
  const label = (m: string) => (m === meta.flash_month ? `${monthLabel(m)} (flash)` : monthLabel(m));

  return (
    <ChartCard
      badges={flash ? ["official", "flash"] : ["official"]}
      title={`What is driving inflation in ${name}`}
      subtitle={
        <>
          Each bar splits the annual inflation rate into the contributions of energy, food, goods and services, in
          percentage points. The line is the published headline rate.
        </>
      }
      controls={
        <Segmented
          label="Time range"
          value={range}
          onChange={setRange}
          options={[
            { value: "3y", label: "3 years" },
            { value: "10y", label: "10 years" },
            { value: "all", label: "Since 2001" },
          ]}
        />
      }
      footnote={
        <>
          Contributions computed by PriceLens from Eurostat HICP indices (2025=100) and annual item weights with the
          standard decomposition for a December-linked chain index; they add up to the rate of the index rebuilt
          from these four components. The gap to the published rate (rounding and compilation detail) is shown in
          the table as “residual”; for this series it is at most {pp(Math.max(...c.residual.filter((x): x is number => x != null).map(Math.abs)), 2, false)} pp.
          {flash && " The latest bar is based on the flash estimate."}
        </>
      }
      table={
        <DataTable
          head={["Month", ...AGG_ORDER.map((a) => meta.labels[a]), "Headline (published)", "Residual"]}
          rows={[...totals].reverse().map((t) => [label(t.month), ...t.parts.map((p) => pp(p, 2)), pct(t.total), pp(t.residual, 2)])}
        />
      }
    >
      <div className="mb-3 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-ink-2" aria-hidden>
        {AGG_ORDER.map((code, i) => (
          <span key={code} className="inline-flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: AGG_COLOR[code] }} />
            {meta.labels[code]}
            <span className="num text-ink">{pp(last?.parts[i], 2)} pp</span>
          </span>
        ))}
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-0.5 w-4 bg-ink" />
          Headline <span className="num text-ink">{pct(last?.total)}</span>
        </span>
      </div>
      <PlotFigure
        label={`Contributions to annual inflation, ${name}`}
        deps={[gd.geo, range]}
        make={(width) => ({
          width,
          height: 360,
          marginLeft: 36,
          x: { type: "utc", label: null, ticks: width < 600 ? 4 : 8 },
          y: { label: "pp", grid: true, tickFormat: (d: number) => d.toFixed(0) },
          color: { domain: AGG_ORDER, range: AGG_ORDER.map((a) => AGG_COLOR[a]) },
          marks: [
            Plot.gridY({ ...GRID }),
            Plot.ruleY([RATE_PIVOT], { stroke: "var(--muted)", strokeWidth: 1 }),
            Plot.text([{ y: RATE_PIVOT }], {
              y: "y",
              frameAnchor: "left",
              text: () => "2% target",
              dy: -7,
              dx: 4,
              fill: "var(--muted)",
              fontSize: 11,
            }),
            Plot.rectY(
              rows,
              Plot.stackY({
                x: "date",
                interval: "month",
                y: "value",
                fill: "code",
                order: AGG_ORDER,
                insetLeft: months.length > 150 ? 0 : 0.75,
                insetRight: months.length > 150 ? 0 : 0.75,
                fillOpacity: (d: { month: string }) => (d.month === meta.flash_month ? 0.55 : 1),
              }),
            ),
            Plot.ruleY([0], { stroke: "var(--ink-2)", strokeWidth: 1 }),
            Plot.lineY(totals, { x: "date", y: "total", stroke: "var(--ink)", strokeWidth: 2, curve: "monotone-x" }),
            Plot.ruleX(totals, Plot.pointerX({ x: "date", stroke: "var(--ink-2)", strokeWidth: 1 })),
            Plot.tip(
              totals,
              Plot.pointerX({
                x: "date",
                y: "total",
                title: (t: (typeof totals)[number]) =>
                  [
                    `${label(t.month)} — headline ${pct(t.total)}`,
                    ...AGG_ORDER.map((a, i) => `${meta.labels[a]}: ${pp(t.parts[i], 2)} pp`),
                  ].join("\n"),
              }),
            ),
          ],
        })}
      />
    </ChartCard>
  );
}

// ------------------------------------------------------------------------------------------------ heatstrip

function Heatstrip({ meta, gd, name }: { meta: Meta; gd: GeoData; name: string }) {
  const end = gd.months.indexOf(meta.latest_full_month);
  const span = 36;
  const ms = gd.months.slice(Math.max(0, end - span + 1), end + 1);
  const latestYear = Math.max(...Object.keys(gd.weights).map(Number));
  const w = gd.weights[String(latestYear)] ?? {};
  const order = ["TOTAL", ...[...meta.divisions].sort((a, b) => (w[b] ?? 0) - (w[a] ?? 0))];
  const rowLabel = (c: string) => (c === "TOTAL" ? "All items" : `${meta.labels[c]}  ${w[c] != null ? `${(w[c] / 10).toFixed(1)}%` : ""}`);
  const cells = order.flatMap((c) =>
    ms.map((m) => ({ code: c, row: rowLabel(c), month: m, value: gd.yoy[c]?.[gd.months.indexOf(m)] ?? null })),
  );
  return (
    <ChartCard
      badges={["official"]}
      title="Which categories are running hot"
      subtitle={
        <>
          Annual inflation by spending category over the last three years. Grey is the 2% target; red is above it,
          blue below. Rows are ordered by their share of household spending in {latestYear} (in brackets).
        </>
      }
      footnote={`${name}. Eurostat HICP annual rates of change (ECOICOP ver. 2 divisions), to ${monthLabel(meta.latest_full_month)}. Colour scale clamped at −4% and +8%. Weights: Eurostat item weights ${latestYear}, % of household spending.`}
      table={
        <DataTable
          head={["Category", ...ms.slice(-12).map((m) => monthLabel(m))]}
          rows={order.map((c) => [
            c === "TOTAL" ? "All items" : meta.labels[c],
            ...ms.slice(-12).map((m) => pct(gd.yoy[c]?.[gd.months.indexOf(m)])),
          ])}
        />
      }
    >
      <div className="overflow-x-auto" ref={(el) => { if (el) el.scrollLeft = el.scrollWidth; }}>
        <PlotFigure
          label={`Annual inflation by category, ${name}`}
          deps={[gd.geo]}
          make={(width) => {
            const W = Math.max(width, 760);
            return {
              width: W,
              style: { maxWidth: "none" }, // scroll horizontally on phones instead of shrinking
              height: 26 * order.length + 60,
              marginLeft: 230,
              marginBottom: 28,
              x: {
                type: "band",
                domain: ms,
                label: null,
                tickFormat: (m: string) => (m.endsWith("-01") || (m === ms[0] && Number(m.slice(5)) <= 9) ? monthLabel(m) : ""),
                tickSize: 0,
              },
              y: { domain: order.map(rowLabel), label: null, tickSize: 0 },
              color: { ...rateColor(), legend: true, label: "Annual rate, % (grey = 2% target)", width: 320 },
              marks: [
                Plot.cell(cells, {
                  x: "month",
                  y: "row",
                  fill: "value",
                  inset: 1,
                  rx: 2,
                  tip: { format: { x: (m: string) => monthLabel(m), fill: (v: number) => pct(v), y: true } },
                }),
                Plot.ruleY([rowLabel("TOTAL")], { dy: 13, stroke: "var(--ink-2)", strokeWidth: 1 }),
              ],
            };
          }}
        />
      </div>
    </ChartCard>
  );
}

// ------------------------------------------------------------------------------------------------ ranking + map

type GeoFeature = Feature<Geometry, { name: string }> & { id?: string };

function Ranking({
  meta,
  rates,
  geo,
  setGeo,
}: {
  meta: Meta;
  rates: Rates;
  geo: string;
  setGeo: (g: string) => void;
}) {
  const fullIdx = rates.months.indexOf(meta.latest_full_month);
  const [mi, setMi] = useState(fullIdx);
  const [code, setCode] = useState("TOTAL");
  const [params, setParams] = useSearchParams();
  const view = params.get("view") === "map" ? "map" : "strip";
  const setView = (v: "strip" | "map") => setParams((p) => (v === "map" ? p.set("view", "map") : p.delete("view"), p), { replace: true });
  const month = rates.months[mi];
  const countries = meta.geos.filter((g) => !g.aggregate);
  const codes = ["TOTAL", ...AGG_ORDER];
  const pts = codes.flatMap((c) =>
    countries.map((g) => ({
      code: c,
      label: meta.labels[c],
      geo: g.code,
      name: g.name,
      value: rateOf(rates, g.code, c, month),
    })),
  ).filter((d) => d.value != null);
  const ea = codes.map((c) => ({ label: meta.labels[c], value: rateOf(rates, "EA", c, month) }));
  const sel = pts.filter((d) => d.geo === geo);
  const ranked = countries
    .map((g) => ({ name: g.name, value: rateOf(rates, g.code, code, month) }))
    .filter((d) => d.value != null)
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

  const [topo, setTopo] = useState<GeoFeature[] | null>(null);
  useEffect(() => {
    if (view !== "map" || topo) return;
    import("world-atlas/countries-50m.json").then((m) => {
      const t = (m.default ?? m) as unknown as Topology;
      const fc = feature(t, t.objects.countries) as unknown as { features: GeoFeature[] };
      setTopo(fc.features);
    });
  }, [view, topo]);

  return (
    <ChartCard
      badges={["official"]}
      title="How countries compare"
      subtitle={
        <>
          Annual inflation in each EU country in {monthLabel(month, true)}.{" "}
          {view === "strip" ? "Each dot is a country; the ring marks the euro area." : "Colour shows the annual rate; grey is the 2% target."}
        </>
      }
      controls={
        <>
          <Segmented
            label="View"
            value={view}
            onChange={setView}
            options={[
              { value: "strip", label: "Ranking" },
              { value: "map", label: "Map" },
            ]}
          />
          {view === "map" && (
            <Select
              label="Measure"
              value={code}
              onChange={setCode}
              options={codes.map((c) => ({ value: c, label: meta.labels[c] }))}
            />
          )}
        </>
      }
      footnote={`Eurostat HICP annual rates of change, ${monthLabel(month)}. Countries without a release for the month are omitted. ${view === "map" ? "Boundaries: Natural Earth (public domain). Non-EU countries in plain grey." : "Click a dot to switch the page to that country."}`}
      table={
        <DataTable head={["Country", `${meta.labels[code]} ${monthLabel(month)}`]} rows={ranked.map((r) => [r.name, pct(r.value)])} />
      }
    >
      <label className="mb-4 flex items-center gap-3 text-xs text-ink-2">
        <span className="w-28 shrink-0">{monthLabel(month)}</span>
        <input
          type="range"
          min={0}
          max={fullIdx}
          value={mi}
          onChange={(e) => setMi(Number(e.target.value))}
          className="w-full accent-[var(--ink)]"
          aria-label="Month"
        />
      </label>
      {view === "strip" ? (
        <PlotFigure
          label={`Annual inflation by country, ${monthLabel(month)}`}
          deps={[month, geo]}
          make={(width) => {
            const vals = pts.map((d) => d.value as number);
            const lo = Math.min(-1, d3.min(vals) ?? 0), hi = Math.max(5, d3.max(vals) ?? 0);
            const narrow = width < 600;
            return {
              width,
              height: (narrow ? 76 : 64) * codes.length + 40,
              marginLeft: narrow ? 8 : 190,
              marginRight: 12,
              x: { domain: [lo - 0.5, hi + 0.5], label: "Annual rate, %", grid: true, tickFormat: (d: number) => `${d}%` },
              y: { domain: codes.map((c) => meta.labels[c]), label: null, tickSize: 0, axis: narrow ? null : "left" },
              marks: [
                Plot.gridX({ ...GRID }),
                ...(narrow
                  ? [
                      Plot.text(codes.map((c) => meta.labels[c]), {
                        y: (d: string) => d,
                        text: (d: string) => d,
                        frameAnchor: "left",
                        textAnchor: "start",
                        dy: -20,
                        fill: "var(--ink-2)",
                      }),
                    ]
                  : []),
                Plot.ruleX([RATE_PIVOT], { stroke: "var(--muted)" }),
                Plot.dot(pts, {
                  x: "value",
                  y: "label",
                  r: 5,
                  fill: "var(--muted)",
                  fillOpacity: 0.55,
                  stroke: "var(--surface)",
                  strokeWidth: 1,
                }),
                Plot.dot(ea, { x: "value", y: "label", r: 8, stroke: "var(--ink)", strokeWidth: 1.5, fill: "none" }),
                Plot.dot(sel, { x: "value", y: "label", r: 6, fill: "var(--ink)", stroke: "var(--surface)", strokeWidth: 2 }),
                Plot.text(sel, { x: "value", y: "label", text: "name", dy: -14, fill: "var(--ink)", fontWeight: 600 }),
                Plot.tip(
                  pts,
                  Plot.pointer({
                    x: "value",
                    y: "label",
                    title: (d: (typeof pts)[number]) => `${d.name}\n${d.label}: ${pct(d.value)}`,
                  }),
                ),
              ],
            };
          }}
        />
      ) : topo ? (
        <ClickableMap topo={topo} rates={rates} code={code} month={month} geo={geo} setGeo={setGeo} meta={meta} />
      ) : (
        <div className="h-[460px] animate-pulse rounded bg-hover" />
      )}
      {view === "strip" && <StripClick pts={pts} setGeo={setGeo} />}
    </ChartCard>
  );
}

// Keyboard-accessible alternative to clicking dots: list of countries as buttons, sorted by headline rate.
function StripClick({ pts, setGeo }: { pts: { code: string; geo: string; name: string; value: number | null }[]; setGeo: (g: string) => void }) {
  const tot = pts.filter((p) => p.code === "TOTAL").sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
  return (
    <div className="mt-3 flex flex-wrap gap-1 text-xs" aria-label="Choose a country">
      {tot.map((p) => (
        <button key={p.geo} onClick={() => setGeo(p.geo)} className="rounded border border-rule px-1.5 py-0.5 text-ink-2 hover:bg-hover">
          {p.name} <span className="num text-ink">{pct(p.value)}</span>
        </button>
      ))}
    </div>
  );
}

const EUROPE_BOX = {
  type: "Polygon" as const,
  coordinates: [[[-11, 34], [-11, 70.5], [34, 70.5], [34, 34], [-11, 34]]],
};

function ClickableMap({
  topo,
  rates,
  code,
  month,
  geo,
  setGeo,
  meta,
}: {
  topo: GeoFeature[];
  rates: Rates;
  code: string;
  month: string;
  geo: string;
  setGeo: (g: string) => void;
  meta: Meta;
}) {
  const feats = useMemo(
    () =>
      topo.map((f) => {
        const g = NUM_TO_GEO[String(f.id)];
        return { f, g, value: g ? rateOf(rates, g, code, month) : null };
      }),
    [topo, rates, code, month],
  );
  return (
    <div
      onClick={(e) => {
        const t = (e.target as SVGElement).closest("[data-geo]");
        if (t) setGeo(t.getAttribute("data-geo")!);
      }}
    >
      <PlotFigure
        label={`Map of ${meta.labels[code]} inflation, ${monthLabel(month)}`}
        deps={[code, month, geo, feats]}
        make={(width) => ({
          width,
          height: Math.min(620, width * 0.85),
          projection: { type: "azimuthal-equal-area", rotate: [-10, -52], domain: EUROPE_BOX },
          color: { ...rateColor(), legend: true, label: "Annual rate, % (grey = 2% target)", width: 320 },
          marks: [
            Plot.geo(feats.filter((d) => !d.g), { geometry: (d) => d.f, fill: "var(--hover)", stroke: "var(--surface)", strokeWidth: 0.6 }),
            Plot.geo(feats.filter((d) => d.g), {
              geometry: (d) => d.f,
              fill: (d) => d.value,
              stroke: (d) => (d.g === geo ? "var(--ink)" : "var(--surface)"),
              strokeWidth: (d) => (d.g === geo ? 2 : 0.8),
              tip: true,
              title: (d) => `${meta.geos.find((x) => x.code === d.g)?.name}\n${meta.labels[code]}: ${pct(d.value)}`,
              render: (index, scales, values, dims, ctx, next) => {
                const g = next!(index, scales, values, dims, ctx)!;
                const fs = feats.filter((d) => d.g);
                g.querySelectorAll("path").forEach((p, i) => {
                  p.setAttribute("data-geo", fs[index[i]].g!);
                  p.style.cursor = "pointer";
                });
                return g;
              },
            }),
          ],
        })}
      />
      <p className="sr-only">ISO ids used: {Object.values(ISO_NUM).length} EU countries.</p>
    </div>
  );
}

// ------------------------------------------------------------------------------------------------ small multiples

function Divisions({ meta, gd, ref_, name, refName, refPhrase }: { meta: Meta; gd: GeoData; ref_: GeoData; name: string; refName: string; refPhrase: string }) {
  const end = gd.months.indexOf(meta.latest_full_month);
  const start = Math.max(0, end - 119);
  const ms = gd.months.slice(start, end + 1);
  const cols = 4;
  const rows = (src: GeoData, who: string) =>
    meta.divisions.flatMap((c, i) =>
      ms.map((m) => ({
        who,
        code: c,
        title: meta.labels[c],
        fx: i % cols,
        fy: Math.floor(i / cols),
        date: toDate(m),
        value: src.yoy[c]?.[src.months.indexOf(m)] ?? null,
      })),
    );
  const data = [...rows(ref_, refName), ...rows(gd, name)];
  const titles = meta.divisions.map((c, i) => ({ fx: i % cols, fy: Math.floor(i / cols), title: meta.labels[c] }));
  return (
    <ChartCard
      badges={["official"]}
      title={`Thirteen categories, ten years: ${name} against ${refPhrase}`}
      subtitle={
        <>
          Annual inflation in each spending category. The dark line is {name}; the grey line is {refPhrase} for comparison.
        </>
      }
      footnote={`Eurostat HICP annual rates of change by ECOICOP ver. 2 division, ${monthLabel(ms[0])}–${monthLabel(ms[ms.length - 1])}. All panels share one y-axis, so heights compare directly.`}
    >
      <PlotFigure
        label={`Annual inflation by category, ${name} vs ${refName}`}
        deps={[gd.geo, ref_.geo]}
        make={(width) => {
          const c = width < 640 ? 2 : cols;
          const remap = (i: number) => ({ fx: i % c, fy: Math.floor(i / c) });
          const idx = new Map(meta.divisions.map((code, i) => [code, remap(i)]));
          const data2 = data.map((d) => ({ ...d, ...idx.get(d.code)! }));
          const titles2 = titles.map((t, i) => ({ ...t, ...remap(i) }));
          return {
            width,
            height: Math.ceil(13 / c) * 170 + 30,
            marginLeft: 34,
            marginTop: 22,
            fx: { axis: null, padding: 0.12 },
            fy: { axis: null, padding: 0.3 },
            x: { type: "utc", ticks: 2, label: null },
            y: { grid: true, label: null, ticks: 4, tickFormat: (d: number) => `${d}%` },
            marks: [
              Plot.gridY({ ...GRID }),
              Plot.ruleY([0], { stroke: "var(--ink-2)", strokeWidth: 0.75 }),
              Plot.text(titles2, { fx: "fx", fy: "fy", text: "title", frameAnchor: "top-left", dy: -14, fontWeight: 600, fill: "var(--ink)" }),
              Plot.lineY(data2.filter((d) => d.who === refName), { fx: "fx", fy: "fy", x: "date", y: "value", stroke: "var(--muted)", strokeWidth: 1.5 }),
              Plot.lineY(data2.filter((d) => d.who === name), { fx: "fx", fy: "fy", x: "date", y: "value", stroke: "var(--ink)", strokeWidth: 2 }),
              Plot.tip(
                data2.filter((d) => d.who === name),
                Plot.pointerX({
                  fx: "fx",
                  fy: "fy",
                  x: "date",
                  y: "value",
                  title: (d: (typeof data2)[number]) => `${d.title}\n${d3.utcFormat("%b %Y")(d.date)}: ${pct(d.value)}`,
                }),
              ),
            ],
          };
        }}
      />
    </ChartCard>
  );
}
