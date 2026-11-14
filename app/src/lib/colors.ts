// Fixed identity for the four ECB special aggregates (validated palette; see index.css).
export const AGG_COLOR: Record<string, string> = {
  NRG: "var(--c-nrg)",
  FOOD: "var(--c-food)",
  IGD_NNRG: "var(--c-neig)",
  SERV: "var(--c-serv)",
};
export const AGG_ORDER = ["NRG", "FOOD", "IGD_NNRG", "SERV"];

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

// Diverging scale for annual rates, centred on the ECB's 2% target: blue below, red above, grey at 2%.
export const RATE_PIVOT = 2;
export const RATE_DOMAIN: [number, number] = [-4, 8];
export function rateScheme(): string[] {
  return ["--div-lo", "--div-lo2", "--div-mid", "--div-hi2", "--div-hi"].map(cssVar);
}
export function resolved(v: string): string {
  return v.startsWith("var(") ? cssVar(v.slice(4, -1)) : v;
}
