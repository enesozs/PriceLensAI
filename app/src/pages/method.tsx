import { DataTable } from "@/components/chart-card";
import { type Meta, type Quality, useJson } from "@/lib/data";
import { monthLabel } from "@/lib/format";

function H({ children }: { children: React.ReactNode }) {
  return <h2 className="mt-10 mb-2 font-serif text-2xl font-medium text-ink">{children}</h2>;
}
function P({ children }: { children: React.ReactNode }) {
  return <p className="mb-3 max-w-3xl text-[15px] leading-relaxed text-ink-2">{children}</p>;
}

export function MethodPage({ meta }: { meta: Meta }) {
  const { data: q } = useJson<Quality>("quality.json");
  const name = (c: string) => meta.geos.find((g) => g.code === c)?.name ?? c;
  return (
    <article className="py-10">
      <h1 className="font-serif text-4xl font-medium text-ink">Method & sources</h1>
      <P>
        PriceLens is built on official statistics and keeps them separate from anything it calculates. Every number on
        the site is labelled as official, flash estimate, custom basket, income-group basket, model forecast, benchmark
        forecast or hypothetical scenario.
      </P>

      <H>What the HICP measures</H>
      <P>
        The harmonised index of consumer prices (HICP) measures the change in prices of goods and services bought by
        households, compiled the same way in every EU country. It is a chain-linked index: weights are updated every
        year and linked through December of the previous year. Since data for January 2026 it uses the ECOICOP ver. 2
        classification (13 spending categories) and the reference period 2025=100. The annual rate compares a month
        with the same month a year earlier.
      </P>
      <P>
        <strong className="text-ink">What it leaves out:</strong> the HICP excludes the costs of owner-occupied housing
        and mortgage interest. Its housing category covers actual rents, maintenance, water and household energy. An
        index level shows price change relative to the reference period, not the euro cost of living.
      </P>

      <H>How PriceLens checks its own maths</H>
      <P>
        Before anything is shown, the pipeline rebuilds each country's all-items HICP from the 13 published category
        indices and Eurostat's annual weights, using the same December-linked chain formula as the official index, and
        compares the result with the published figure. The gate is a 95th-percentile gap of at most 0.10 percentage
        points (and no month above 0.30) since 2001.
      </P>
      {q && (
        <>
          <P>
            Result: {q.reconstruction.filter((r) => r.gate === "PASS").length} of {q.reconstruction.length} series pass.
            Italy does not: its published index cannot be reproduced from its published categories and annual weights
            to this precision, consistent with within-year weight changes in its compilation. Italian official figures
            are shown as published; custom calculations for Italy carry this caveat.
          </P>
          <details className="mb-4 max-w-3xl text-sm">
            <summary className="cursor-pointer text-xs text-ink-2 underline decoration-rule underline-offset-4">
              Reconstruction gap by country
            </summary>
            <div className="mt-2 max-h-96 overflow-auto rounded border border-rule">
              <DataTable
                head={["Country", "95th pct gap (pp)", "Max gap (pp)", "Gate"]}
                rows={q.reconstruction.map((r) => [name(r.geo), r.p95_abs_pp.toFixed(3), r.max_abs_pp.toFixed(3), r.gate === "PASS" ? "Pass" : "Exception"])}
              />
            </div>
          </details>
        </>
      )}

      <H>Contributions</H>
      <P>
        The contribution of energy, food, goods and services to the annual rate uses the standard decomposition for a
        December-linked chain index: one term for the change since last December with this year's weights and one for
        the change from a year ago to last December with last year's weights. The pieces add up exactly to the rate of
        the index rebuilt from the four components; the small difference to the published rate is reported, not
        spread.
      </P>

      <H>Sources and licences</H>
      <ul className="mb-3 max-w-3xl list-disc space-y-1.5 pl-5 text-[15px] leading-relaxed text-ink-2">
        <li>
          Eurostat HICP monthly indices and rates (<code>prc_hicp_minr</code>) and item weights (<code>prc_hicp_iw</code>);
          Household Budget Survey structures by income quintile (<code>hbs_str_t223</code>). Reuse authorised with
          acknowledgement of the source (Eurostat copyright notice; CC BY 4.0). Data versions:{" "}
          {meta.source_versions.join(", ")}.
        </li>
        <li>Country boundaries: Natural Earth (public domain), via the world-atlas package.</li>
        <li>
          Latest month: {monthLabel(meta.latest_month, true)}
          {meta.flash_month ? " is a flash estimate for the euro area and some member states; full data follow mid-month." : "."}
        </li>
      </ul>
      <P>{meta.attribution}</P>

      {q && (
        <>
          <H>Data quality checks (latest pipeline run)</H>
          <div className="max-w-3xl rounded border border-rule">
            <DataTable head={["Check", "Status", "Detail"]} rows={q.checks.map((c) => [c.name, c.status, c.detail])} />
          </div>
        </>
      )}
    </article>
  );
}
