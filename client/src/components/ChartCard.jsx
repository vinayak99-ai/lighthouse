import { useState } from "react";
import TimeSeriesChart from "../charts/TimeSeriesChart.jsx";
import CategoryBarChart from "../charts/CategoryBarChart.jsx";
import StackedBarChart from "../charts/StackedBarChart.jsx";
import StatTile from "../charts/StatTile.jsx";
import SmallMultiples from "../charts/SmallMultiples.jsx";
import ChartLegend from "../charts/ChartLegend.jsx";
import { formatCompact, formatDateLabel } from "../lib/chartTheme.js";

// "stat" and "small_multiples" self-label every value/facet directly (a name
// beside each tile or above each mini-chart) -- color isn't the identity
// channel there, so the color-matching legend those other forms need would
// just restate what's already on screen.
const SELF_LABELED_TYPES = new Set(["stat", "small_multiples"]);

export default function ChartCard({ chart }) {
  const [showTable, setShowTable] = useState(false);
  const [hoveredSeries, setHoveredSeries] = useState(null);
  const [hiddenSeries, setHiddenSeries] = useState(() => new Set());
  const { chart_type, title, subtitle, series, data, insight, y_unit } = chart;

  function toggleSeries(name) {
    setHiddenSeries((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else if (next.size < series.length - 1) next.add(name); // never hide the last visible series
      return next;
    });
  }

  const chartProps = { data, series, unit: y_unit, hoveredSeries, hiddenSeries };

  return (
    <div
      className="lh-chart-card"
      style={{
        background: "var(--surface-1)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        padding: 20,
        marginTop: 8,
        width: "100%",
        maxWidth: 720,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>{title}</h3>
          {subtitle && <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-muted)" }}>{subtitle}</p>}
        </div>
        <button
          className="lh-btn"
          onClick={() => setShowTable((s) => !s)}
          style={{
            background: "transparent",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            color: "var(--text-secondary)",
            fontSize: 12,
            padding: "4px 10px",
            cursor: "pointer",
            flexShrink: 0,
          }}
        >
          {showTable ? "Chart" : "Table"}
        </button>
      </div>

      {!SELF_LABELED_TYPES.has(chart_type) && (
        <ChartLegend series={series} hiddenSeries={hiddenSeries} onToggle={toggleSeries} onHover={setHoveredSeries} />
      )}

      {showTable ? (
        <DataTable data={data} series={series} unit={y_unit} />
      ) : chart_type === "stat" ? (
        <StatTile data={data} series={series} unit={y_unit} />
      ) : chart_type === "small_multiples" ? (
        <SmallMultiples data={data} series={series} unit={y_unit} />
      ) : chart_type === "bar" ? (
        <CategoryBarChart {...chartProps} />
      ) : chart_type === "stacked_bar" ? (
        <StackedBarChart {...chartProps} />
      ) : (
        <TimeSeriesChart type={chart_type} {...chartProps} />
      )}

      {insight && (
        <p style={{ margin: "12px 0 0", fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.5, borderTop: "1px solid var(--border)", paddingTop: 12 }}>
          {insight}
        </p>
      )}
    </div>
  );
}

function DataTable({ data, series, unit }) {
  return (
    <div style={{ maxHeight: 320, overflow: "auto", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)" }}>
      <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 13 }}>
        <thead>
          <tr>
            <th style={thStyle}>Date</th>
            {series.map((s) => (
              <th key={s} style={{ ...thStyle, textAlign: "right" }}>
                {s}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <tr key={row.x}>
              <td style={tdStyle}>{formatDateLabel(row.x)}</td>
              {series.map((s) => (
                <td key={s} style={{ ...tdStyle, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
                  {formatCompact(row[s], unit)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const thStyle = {
  textAlign: "left",
  padding: "8px 12px",
  color: "var(--text-muted)",
  fontWeight: 500,
  position: "sticky",
  top: 0,
  background: "var(--surface-1)",
  borderBottom: "1px solid var(--border)",
};

const tdStyle = {
  padding: "6px 12px",
  color: "var(--text-secondary)",
  borderBottom: "1px solid var(--border)",
};
