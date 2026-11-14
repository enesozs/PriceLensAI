import { useEffect, useState, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import type { Meta } from "@/lib/data";
import { monthLabel } from "@/lib/format";

const NAV = [
  { to: "/", label: "Atlas" },
  { to: "/basket", label: "Basket" },
  { to: "/quintiles", label: "Income groups" },
  { to: "/forecasts", label: "Forecasts" },
  { to: "/us", label: "United States" },
  { to: "/method", label: "Method & sources" },
];

function ThemeToggle() {
  const [theme, setTheme] = useState<string | null>(() => document.documentElement.dataset.theme ?? null);
  useEffect(() => {
    if (theme) document.documentElement.dataset.theme = theme;
    else delete document.documentElement.dataset.theme;
    try {
      if (theme) localStorage.setItem("pl-theme", theme);
      else localStorage.removeItem("pl-theme");
    } catch {
      /* storage unavailable: theme still applies for this visit */
    }
  }, [theme]);
  const dark =
    theme === "dark" || (!theme && window.matchMedia("(prefers-color-scheme: dark)").matches);
  return (
    <button
      onClick={() => setTheme(dark ? "light" : "dark")}
      className="rounded-md border border-rule px-2.5 py-1 text-xs text-ink-2 hover:bg-hover"
      aria-label={`Switch to ${dark ? "light" : "dark"} theme`}
    >
      {dark ? "Light" : "Dark"}
    </button>
  );
}

export function Shell({ meta, children }: { meta: Meta | null; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-bg">
      <header className="border-b border-rule bg-bg/90 backdrop-blur supports-[backdrop-filter]:bg-bg/75 sticky top-0 z-20">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4 py-3 sm:px-6">
          <NavLink to="/" className="font-serif text-xl font-semibold tracking-tight text-ink">
            PriceLens
          </NavLink>
          <nav className="flex flex-1 gap-1 overflow-x-auto text-sm" aria-label="Main">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.to === "/"}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-md px-2.5 py-1 ${isActive ? "bg-hover text-ink" : "text-ink-2 hover:text-ink"}`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          <ThemeToggle />
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 sm:px-6">{children}</main>
      <footer className="mt-10 border-t border-rule">
        <div className="mx-auto max-w-6xl px-4 py-8 text-xs leading-relaxed text-muted sm:px-6">
          <p>{meta?.attribution} United States page: U.S. Bureau of Labor Statistics (public domain).</p>
          {meta && (
            <p className="mt-1">
              HICP data to {monthLabel(meta.latest_month, true)}
              {meta.flash_month ? ` (${monthLabel(meta.flash_month)} is a flash estimate)` : ""} · Eurostat data
              versions {meta.source_versions.join(", ")} · Index {meta.index_base}, {meta.classification}. Map
              boundaries: Natural Earth (public domain).
            </p>
          )}
          <p className="mt-1">
            PriceLens shows official statistics, custom calculations, forecasts and scenarios — each is labelled.
            Custom and forecast numbers are not official statistics.
          </p>
        </div>
      </footer>
    </div>
  );
}
