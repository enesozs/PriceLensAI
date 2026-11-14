// Basket index maths, run entirely in the browser (no basket ever leaves the device).
// Same formulas as the Python reference (src/pricelens/basket.py); both are tested against
// tests/fixtures/basket_cases.json.
//
// Fixed-base:  I_t = 100 * Σ w_i · I_i,t / I_i,b
// Chained:     L_t = Σ w_i,y · I_i,t / I_i,Dec(y-1);  I_t = I_Dec(y-1) · L_t   (shares re-applied each December)

export type IndexSeries = Record<string, (number | null)[]>;
export type Shares = Record<string, number>;

export function normalize(amounts: Shares): { shares: Shares; total: number; error: string | null } {
  const vals = Object.values(amounts);
  if (vals.some((v) => !Number.isFinite(v) || v < 0)) return { shares: {}, total: 0, error: "Weights must be zero or positive numbers." };
  const total = vals.reduce((a, b) => a + b, 0);
  if (total <= 0) return { shares: {}, total: 0, error: "The basket is empty: give at least one category a weight." };
  return { shares: Object.fromEntries(Object.entries(amounts).map(([k, v]) => [k, v / total])), total, error: null };
}

export function fixedBase(index: IndexSeries, shares: Shares, base: number): (number | null)[] {
  const n = Object.values(index)[0]?.length ?? 0;
  const out: (number | null)[] = [];
  for (let t = 0; t < n; t++) {
    let acc = 0;
    let ok = true;
    for (const [c, w] of Object.entries(shares)) {
      if (!w) continue;
      const it = index[c]?.[t], ib = index[c]?.[base];
      if (it == null || ib == null) {
        ok = false;
        break;
      }
      acc += (w * it) / ib;
    }
    out.push(ok ? 100 * acc : null);
  }
  return out;
}

export function chained(
  index: IndexSeries,
  months: string[],
  sharesFor: (year: number) => Shares | null,
  base: number,
): (number | null)[] {
  const n = months.length;
  const level: (number | null)[] = Array.from({ length: n }, () => null);
  const first = months.findIndex((m) => m.endsWith("-12"));
  if (first < 0) return level;
  const decLevel = new Map<number, number>([[Number(months[first].slice(0, 4)), 100]]);
  const decIdx = new Map<number, number>([[Number(months[first].slice(0, 4)), first]]);
  level[first] = 100;
  for (let t = first + 1; t < n; t++) {
    const y = Number(months[t].slice(0, 4));
    const prev = decLevel.get(y - 1);
    const di = decIdx.get(y - 1);
    const sh = sharesFor(y);
    if (prev == null || di == null || !sh) continue;
    let acc = 0;
    let ok = true;
    for (const [c, w] of Object.entries(sh)) {
      if (!w) continue;
      const it = index[c]?.[t], id = index[c]?.[di];
      if (it == null || id == null) {
        ok = false;
        break;
      }
      acc += (w * it) / id;
    }
    if (!ok) continue;
    level[t] = prev * acc;
    if (months[t].endsWith("-12")) {
      decLevel.set(y, level[t]!);
      decIdx.set(y, t);
    }
  }
  const b = level[base];
  if (b == null) return Array.from({ length: n }, () => null);
  return level.map((v) => (v == null ? null : (100 * v) / b));
}

export function yoy(levels: (number | null)[]): (number | null)[] {
  return levels.map((v, t) => {
    const p = t >= 12 ? levels[t - 12] : null;
    return v == null || p == null ? null : 100 * (v / p - 1);
  });
}

export function rebase(levels: (number | null)[], base: number): (number | null)[] {
  const b = levels[base];
  return levels.map((v) => (v == null || b == null ? null : (100 * v) / b));
}

/** Fixed-base contributions to the cumulative % change since the base month (they add up to I_t − 100). */
export function contribSinceBase(index: IndexSeries, shares: Shares, base: number, t: number): Record<string, number | null> {
  return Object.fromEntries(
    Object.entries(shares).map(([c, w]) => {
      const it = index[c]?.[t], ib = index[c]?.[base];
      return [c, it == null || ib == null ? null : 100 * w * (it / ib - 1)];
    }),
  );
}

/** Hypothetical scenario: extend each component from month `last` for `horizon` months at an assumed annual
 *  rate (compounded monthly). Returns new month labels and the extended index (observed part unchanged). */
export function extendScenario(
  index: IndexSeries,
  months: string[],
  last: number,
  annualRates: Record<string, number>,
  horizon = 12,
): { months: string[]; index: IndexSeries } {
  const next: string[] = [];
  let [y, m] = months[last].split("-").map(Number);
  for (let k = 0; k < horizon; k++) {
    m += 1;
    if (m > 12) {
      m = 1;
      y += 1;
    }
    next.push(`${y}-${String(m).padStart(2, "0")}`);
  }
  const outMonths = [...months.slice(0, last + 1), ...next];
  const out: IndexSeries = {};
  for (const [c, s] of Object.entries(index)) {
    const base = s[last];
    const r = annualRates[c] ?? 0;
    const ext = next.map((_, k) => (base == null ? null : base * Math.pow(1 + r / 100, (k + 1) / 12)));
    out[c] = [...s.slice(0, last + 1), ...ext];
  }
  return { months: outMonths, index: out };
}
