import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { Shell } from "@/components/shell";
import { type Meta, type Rates, useJson } from "@/lib/data";
import { AtlasPage } from "@/pages/atlas";

// Secondary pages load on demand; the Atlas is the landing page and ships in the main bundle.
const BasketPage = lazy(() => import("@/pages/basket").then((m) => ({ default: m.BasketPage })));
const QuintilesPage = lazy(() => import("@/pages/quintiles").then((m) => ({ default: m.QuintilesPage })));
const ForecastsPage = lazy(() => import("@/pages/forecasts").then((m) => ({ default: m.ForecastsPage })));
const USPage = lazy(() => import("@/pages/us").then((m) => ({ default: m.USPage })));
const MethodPage = lazy(() => import("@/pages/method").then((m) => ({ default: m.MethodPage })));

export function App() {
  const { data: meta, error } = useJson<Meta>("meta.json");
  const { data: rates } = useJson<Rates>("rates.json");
  return (
    <Shell meta={meta}>
      {error && <p className="py-10 text-sm">Could not load data ({error}). Run `uv run pricelens export`.</p>}
      {meta && rates ? (
        <Suspense fallback={<div className="py-16 text-sm text-muted">Loading…</div>}>
        <Routes>
          <Route path="/" element={<AtlasPage meta={meta} rates={rates} />} />
          <Route path="/basket" element={<BasketPage meta={meta} />} />
          <Route path="/quintiles" element={<QuintilesPage meta={meta} />} />
          <Route path="/forecasts" element={<ForecastsPage meta={meta} rates={rates} />} />
          <Route path="/us" element={<USPage />} />
          <Route path="/method" element={<MethodPage meta={meta} />} />
        </Routes>
        </Suspense>
      ) : (
        !error && <div className="py-16 text-sm text-muted">Loading official data…</div>
      )}
    </Shell>
  );
}
