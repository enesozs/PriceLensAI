import { Route, Routes } from "react-router-dom";
import { Shell } from "@/components/shell";
import { type Meta, type Rates, useJson } from "@/lib/data";
import { AtlasPage } from "@/pages/atlas";
import { MethodPage } from "@/pages/method";

function Placeholder({ title, milestone }: { title: string; milestone: string }) {
  return (
    <div className="py-16">
      <h1 className="font-serif text-3xl text-ink">{title}</h1>
      <p className="mt-2 text-ink-2">Not built yet — planned for {milestone}.</p>
    </div>
  );
}

export function App() {
  const { data: meta, error } = useJson<Meta>("meta.json");
  const { data: rates } = useJson<Rates>("rates.json");
  return (
    <Shell meta={meta}>
      {error && <p className="py-10 text-sm">Could not load data ({error}). Run `uv run pricelens export`.</p>}
      {meta && rates ? (
        <Routes>
          <Route path="/" element={<AtlasPage meta={meta} rates={rates} />} />
          <Route path="/basket" element={<Placeholder title="Basket Studio" milestone="M3" />} />
          <Route path="/quintiles" element={<Placeholder title="Inflation by income group" milestone="M3" />} />
          <Route path="/forecasts" element={<Placeholder title="Forecast Lab" milestone="M4" />} />
          <Route path="/method" element={<MethodPage meta={meta} />} />
        </Routes>
      ) : (
        !error && <div className="py-16 text-sm text-muted">Loading official data…</div>
      )}
    </Shell>
  );
}
