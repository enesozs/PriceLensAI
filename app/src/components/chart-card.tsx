import type { ReactNode } from "react";
import { Badge, type MeasureType } from "./badge";

// One chart = one story: serif title, a plain-language subtitle, the figure, a footnote with source/base/units,
// and an optional table view (accessibility: the data is never colour-only or chart-only).
export function ChartCard({
  title,
  subtitle,
  badges,
  children,
  footnote,
  table,
  controls,
}: {
  title: string;
  subtitle?: ReactNode;
  badges?: MeasureType[];
  children: ReactNode;
  footnote: ReactNode;
  table?: ReactNode;
  controls?: ReactNode;
}) {
  return (
    <section className="border-t border-rule pt-6 pb-10">
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-3xl">
          <div className="mb-1.5 flex gap-1.5">{badges?.map((b) => <Badge key={b} type={b} />)}</div>
          <h2 className="font-serif text-2xl leading-tight font-medium text-ink sm:text-[28px]">{title}</h2>
          {subtitle && <p className="mt-1.5 text-[15px] leading-relaxed text-ink-2">{subtitle}</p>}
        </div>
        {controls && <div className="flex flex-wrap items-center gap-2">{controls}</div>}
      </div>
      {children}
      <p className="mt-3 text-xs leading-relaxed text-muted">{footnote}</p>
      {table && (
        <details className="mt-2 text-sm">
          <summary className="cursor-pointer text-xs text-ink-2 underline decoration-rule underline-offset-4 hover:text-ink">
            Show data table
          </summary>
          <div className="mt-2 max-h-80 overflow-auto rounded border border-rule">{table}</div>
        </details>
      )}
    </section>
  );
}

export function DataTable({ head, rows }: { head: string[]; rows: (string | number)[][] }) {
  return (
    <table className="num w-full border-collapse text-xs">
      <thead className="sticky top-0 bg-surface">
        <tr>
          {head.map((h) => (
            <th key={h} className="border-b border-rule px-2 py-1.5 text-left font-medium text-ink-2">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => (
          <tr key={i} className="odd:bg-hover/40">
            {r.map((c, j) => (
              <td key={j} className="px-2 py-1 text-ink">
                {c}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex rounded-md border border-rule bg-surface p-0.5 text-xs">
      {options.map((o) => (
        <button
          key={o.value}
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={`rounded px-2.5 py-1 transition-colors ${value === o.value ? "bg-ink text-bg" : "text-ink-2 hover:bg-hover"}`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Select({
  value,
  onChange,
  options,
  label,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string; group?: string }[];
  label: string;
}) {
  const groups = [...new Set(options.map((o) => o.group ?? ""))];
  return (
    <label className="inline-flex items-center gap-2 text-xs text-ink-2">
      <span className="sr-only sm:not-sr-only">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-rule bg-surface px-2 py-1.5 text-sm text-ink"
      >
        {groups.map((g) =>
          g ? (
            <optgroup key={g} label={g}>
              {options.filter((o) => o.group === g).map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </optgroup>
          ) : (
            options.filter((o) => !o.group).map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))
          ),
        )}
      </select>
    </label>
  );
}
