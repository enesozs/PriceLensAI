// Eurostat geo code -> ISO 3166-1 numeric id used by world-atlas (Natural Earth).
export const ISO_NUM: Record<string, string> = {
  AT: "040", BE: "056", BG: "100", HR: "191", CY: "196", CZ: "203", DK: "208", EE: "233", FI: "246",
  FR: "250", DE: "276", EL: "300", HU: "348", IE: "372", IT: "380", LV: "428", LT: "440", LU: "442",
  MT: "470", NL: "528", PL: "616", PT: "620", RO: "642", SK: "703", SI: "705", ES: "724", SE: "752",
};
export const NUM_TO_GEO: Record<string, string> = Object.fromEntries(Object.entries(ISO_NUM).map(([k, v]) => [v, k]));
