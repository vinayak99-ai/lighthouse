import { colorForIndex } from "../lib/chartTheme.js";

// A legend is always present for 2+ series (the dependable identity channel);
// a single series needs no legend box -- the chart title already names it.
// Click a swatch to toggle that series off; hover one to spotlight it (dims
// the rest in the chart) -- the interaction Highcharts ships by default.
export default function ChartLegend({ series, hiddenSeries, onToggle, onHover }) {
  if (!series || series.length < 2) return null;
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 16px", padding: "4px 4px 12px" }}>
      {series.map((name, i) => {
        const hidden = hiddenSeries?.has(name);
        return (
          <button
            key={name}
            type="button"
            className="lh-legend-item"
            data-hidden={hidden ? "true" : "false"}
            onClick={() => onToggle?.(name)}
            onMouseEnter={() => onHover?.(name)}
            onMouseLeave={() => onHover?.(null)}
            style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, color: "var(--text-secondary)", padding: 0 }}
          >
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: hidden ? "var(--baseline)" : colorForIndex(i),
                flexShrink: 0,
                transition: "background 0.15s ease",
              }}
            />
            <span style={{ textDecoration: hidden ? "line-through" : "none" }}>{name}</span>
          </button>
        );
      })}
    </div>
  );
}
