import { Route, Routes } from "react-router-dom";
import { Shell } from "@/components/shell";
import { type Meta, type Rates, useJson } from "@/lib/data";
import { AtlasPage } from "@/pages/atlas";
import { BasketPage } from "@/pages/basket";
import { QuintilesPage } from "@/pages/quintiles";
import { ForecastsPage } from "@/pages/forecasts";
import { MethodPage } from "@/pages/method";

export function App() {
  const { data: meta, error } = useJson<Meta>("meta.json");
  const { data: rates } = useJson<Rates>("rates.json");
  return (
    <Shell meta={meta}>
      {error && <p className="py-10 text-sm">Could not load data ({error}). Run `uv run pricelens export`.</p>}
      {meta && rates ? (
        <Routes>
          <Route path="/" element={<AtlasPage meta={meta} rates={rates} />} />
          <Route path="/basket" element={<BasketPage meta={meta} />} />
          <Route path="/quintiles" element={<QuintilesPage meta={meta} />} />
          <Route path="/forecasts" element={<ForecastsPage meta={meta} rates={rates} />} />
          <Route path="/method" element={<MethodPage meta={meta} />} />
        </Routes>
      ) : (
        !error && <div className="py-16 text-sm text-muted">Loading official data…</div>
      )}
    </Shell>
  );
}
