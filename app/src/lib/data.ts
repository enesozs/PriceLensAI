import { useEffect, useState } from "react";

// Shapes written by `uv run pricelens export` (src/pricelens/export.py).
export type GeoMeta = { code: string; name: string; aggregate: boolean };
export type Meta = {
  generated_at: string;
  source_versions: string[];
  latest_month: string;
  latest_full_month: string;
  flash_month: string | null;
  index_base: string;
  classification: string;
  geos: GeoMeta[];
  aggregates: string[];
  divisions: string[];
  labels: Record<string, string>;
  attribution: string;
};
export type Rates = {
  months: string[];
  geos: string[];
  codes: string[];
  values: (number | null)[][][]; // [geo][code][month]
  estimated: string[]; // "GEO|CODE|YYYY-MM" flagged estimated (flash)
};
export type GeoData = {
  geo: string;
  months: string[];
  index: Record<string, (number | null)[]>;
  yoy: Record<string, (number | null)[]>;
  weights: Record<string, Record<string, number>>;
  contrib: { months: string[]; values: Record<string, (number | null)[]>; residual: (number | null)[] };
};
export type Quality = {
  qa_ok: boolean;
  checks: { name: string; status: string; detail: string }[];
  reconstruction: { geo: string; p95_abs_pp: number; max_abs_pp: number; gate: string }[];
  hbs_waves: Record<string, number[]>;
};

const cache = new Map<string, Promise<unknown>>();
export function fetchJson<T>(path: string): Promise<T> {
  if (!cache.has(path)) {
    cache.set(
      path,
      fetch(`./data/${path}`).then((r) => {
        if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
        return r.json();
      }),
    );
  }
  return cache.get(path) as Promise<T>;
}

export function useJson<T>(path: string | null): { data: T | null; error: string | null } {
  const [state, setState] = useState<{ data: T | null; error: string | null }>({ data: null, error: null });
  useEffect(() => {
    if (!path) return;
    let live = true;
    setState({ data: null, error: null });
    fetchJson<T>(path)
      .then((d) => live && setState({ data: d, error: null }))
      .catch((e: Error) => live && setState({ data: null, error: e.message }));
    return () => {
      live = false;
    };
  }, [path]);
  return state;
}

export function rateOf(r: Rates, geo: string, code: string, month: string): number | null {
  const g = r.geos.indexOf(geo), c = r.codes.indexOf(code), m = r.months.indexOf(month);
  if (g < 0 || c < 0 || m < 0) return null;
  return r.values[g][c][m];
}
export function isEstimated(r: Rates, geo: string, code: string, month: string): boolean {
  return r.estimated.includes(`${geo}|${code}|${month}`);
}
