export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const LONG_MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export function monthLabel(ym: string, long = false): string {
  const [y, m] = ym.split("-").map(Number);
  return `${(long ? LONG_MONTHS : MONTHS)[m - 1]} ${y}`;
}
export function toDate(ym: string): Date {
  const [y, m] = ym.split("-").map(Number);
  return new Date(Date.UTC(y, m - 1, 1));
}
export function pp(x: number | null | undefined, digits = 1, sign = true): string {
  if (x == null || Number.isNaN(x)) return "–";
  const s = x.toFixed(digits);
  return sign && x > 0 ? `+${s}` : s.replace("-", "−");
}
export function pct(x: number | null | undefined, digits = 1): string {
  if (x == null || Number.isNaN(x)) return "–";
  return `${x.toFixed(digits).replace("-", "−")}%`;
}
export function num(x: number | null | undefined, digits = 1): string {
  if (x == null || Number.isNaN(x)) return "–";
  return x.toFixed(digits).replace("-", "−");
}

// Geo names inside sentences: "the euro area", "the European Union", otherwise the country name.
export function inGeo(code: string, name: string): string {
  if (code === "EA") return "the euro area";
  if (code === "EU27_2020") return "the European Union";
  return name;
}
