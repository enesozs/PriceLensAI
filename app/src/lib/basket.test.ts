import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { chained, contribSinceBase, extendScenario, fixedBase, normalize, yoy } from "./basket";

// Same hand-worked fixture as the Python reference tests.
const CASE = JSON.parse(readFileSync(resolve(__dirname, "../../../tests/fixtures/basket_cases.json"), "utf8"));
const M: string[] = CASE.months;
const at = (lv: (number | null)[], m: string) => lv[M.indexOf(m)];

describe("hand-worked basket fixture", () => {
  it("fixed-base levels", () => {
    const lv = fixedBase(CASE.index, CASE.shares, M.indexOf(CASE.base));
    for (const [m, v] of Object.entries(CASE.expected.fixed)) if (!m.startsWith("_")) expect(at(lv, m)).toBeCloseTo(v as number, 9);
  });
  it("chained levels", () => {
    const lv = chained(CASE.index, M, () => CASE.shares, M.indexOf(CASE.base));
    for (const [m, v] of Object.entries(CASE.expected.chained)) if (!m.startsWith("_")) expect(at(lv, m)).toBeCloseTo(v as number, 9);
  });
  it("annual rates", () => {
    expect(yoy(fixedBase(CASE.index, CASE.shares, 0))[13]).toBeCloseTo(CASE.expected.yoy_2026_01.fixed, 8);
    expect(yoy(chained(CASE.index, M, () => CASE.shares, 0))[13]).toBeCloseTo(CASE.expected.yoy_2026_01.chained, 8);
  });
  it("contributions add up to the cumulative change", () => {
    const c = contribSinceBase(CASE.index, CASE.shares, 0, 13);
    expect(c.A).toBeCloseTo(10.5, 9);
    expect(c.C).toBeCloseTo(-2.9, 9);
    const sum = Object.values(c).reduce((a, b) => a! + b!, 0)!;
    expect(sum).toBeCloseTo(CASE.expected.fixed["2026-01"] - 100, 9);
  });
});

describe("validation", () => {
  it("normalizes amounts and rejects invalid input", () => {
    expect(normalize({ a: 300, b: 100 }).shares).toEqual({ a: 0.75, b: 0.25 });
    expect(normalize({ a: -1, b: 2 }).error).not.toBeNull();
    expect(normalize({ a: 0, b: 0 }).error).not.toBeNull();
  });
  it("missing component gives a missing level, never zero", () => {
    const lv = fixedBase({ A: [100, null, 110], B: [100, 100, 100] }, { A: 0.5, B: 0.5 }, 0);
    expect(lv[1]).toBeNull();
    expect(lv[2]).toBeCloseTo(105);
  });
});

describe("scenario extension", () => {
  it("compounds an annual rate monthly and leaves observed data untouched", () => {
    const { months, index } = extendScenario({ A: [100, 100] }, ["2026-08", "2026-09"], 1, { A: 12 }, 12);
    expect(months.at(-1)).toBe("2027-09");
    expect(index.A[1]).toBe(100);
    expect(index.A.at(-1)!).toBeCloseTo(112, 9);
  });
});

// Chained mode with official division weights must reproduce the published all-items HICP (the reconstruction gate, now on the
// browser implementation and the exported data).
describe.each(["DE", "FR", "ES", "EA"])("official reconstruction %s", (geo) => {
  it("annual rate within the reconstruction tolerance", () => {
    const g = JSON.parse(readFileSync(resolve(__dirname, `../../public/data/geo/${geo}.json`), "utf8"));
    const divs = Object.keys(g.index).filter((c) => /^CP\d\d$/.test(c));
    const sharesFor = (y: number) => {
      const w = g.weights[String(y)];
      if (!w || divs.some((d) => w[d] == null)) return null;
      return normalize(Object.fromEntries(divs.map((d) => [d, w[d]]))).shares;
    };
    const idx = Object.fromEntries(divs.map((d) => [d, g.index[d]]));
    const base = g.months.indexOf("2015-12");
    const r = yoy(chained(idx, g.months, sharesFor, base));
    const gaps: number[] = [];
    g.months.forEach((m: string, t: number) => {
      if (m >= "2002-01" && r[t] != null && g.yoy.TOTAL[t] != null) gaps.push(Math.abs(r[t]! - g.yoy.TOTAL[t]));
    });
    gaps.sort((a, b) => a - b);
    const p95 = gaps[Math.floor(0.95 * (gaps.length - 1))];
    expect(gaps.length).toBeGreaterThan(250);
    // published rates have 1 decimal, so allow 0.05 on top of the 0.10 pp reconstruction gate
    expect(p95).toBeLessThan(0.15);
  });
});
