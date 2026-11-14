import * as Plot from "@observablehq/plot";
import { useEffect, useRef } from "react";

// Observable Plot in React: redraws on resize and on theme change.
// `make(width)` returns the Plot options and must be pure.
export function PlotFigure({
  make,
  label,
  deps,
}: {
  make: (width: number) => Plot.PlotOptions;
  label: string;
  deps: unknown[];
}) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let lastW = -1;
    const draw = (force = false) => {
      const w = Math.max(300, Math.floor(el.clientWidth));
      if (!force && w === lastW) return;
      lastW = w;
      const opts = make(w);
      const chart = Plot.plot({
        ...opts,
        style: {
          background: "transparent",
          color: "var(--ink-2)",
          fontSize: "12px",
          fontFamily: "inherit",
          overflow: "visible",
          ...(typeof opts.style === "object" ? opts.style : {}),
        },
      });
      el.replaceChildren(chart);
    };
    draw(true);
    const ro = new ResizeObserver(() => draw());
    ro.observe(el);
    const mo = new MutationObserver(() => draw(true)); // theme toggle
    mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onMq = () => draw(true);
    mq.addEventListener("change", onMq);
    return () => {
      ro.disconnect();
      mo.disconnect();
      mq.removeEventListener("change", onMq);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return <div ref={ref} className="w-full" role="img" aria-label={label} />;
}

// Shared axis/grid styling: solid hairlines one shade off the surface.
export const GRID = { stroke: "var(--grid)", strokeOpacity: 1 } as const;
