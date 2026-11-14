export type MeasureType = "official" | "flash" | "custom" | "quintile" | "forecast" | "benchmark" | "scenario";

const STYLE: Record<MeasureType, { label: string; bg: string; ink: string }> = {
  official: { label: "Official", bg: "var(--badge-official)", ink: "var(--badge-official-ink)" },
  flash: { label: "Flash estimate", bg: "var(--badge-flash)", ink: "var(--badge-flash-ink)" },
  custom: { label: "Custom basket", bg: "var(--badge-custom)", ink: "var(--badge-custom-ink)" },
  quintile: { label: "Quintile basket", bg: "var(--badge-custom)", ink: "var(--badge-custom-ink)" },
  forecast: { label: "Model forecast", bg: "var(--badge-flash)", ink: "var(--badge-flash-ink)" },
  benchmark: { label: "Benchmark forecast", bg: "var(--hover)", ink: "var(--ink-2)" },
  scenario: { label: "Hypothetical scenario", bg: "var(--badge-hypo)", ink: "var(--badge-hypo-ink)" },
};

// Measure-type badge: every chart says what kind of number it shows.
export function Badge({ type, text }: { type: MeasureType; text?: string }) {
  const s = STYLE[type];
  return (
    <span
      className="inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-medium tracking-wide uppercase"
      style={{ background: s.bg, color: s.ink }}
    >
      {text ?? s.label}
    </span>
  );
}
