import { useState } from "react";
import TimeSeriesChart from "../charts/TimeSeriesChart.jsx";
import CategoryBarChart from "../charts/CategoryBarChart.jsx";
import StackedBarChart from "../charts/StackedBarChart.jsx";
import ChartLegend from "../charts/ChartLegend.jsx";
import { formatCompact, formatDateLabel } from "../lib/chartTheme.js";

export default function ChartCard({ chart }) {
  const [showTable, setShowTable] = useState(false);
  const { chart_type, title, subtitle, series, data, insight, y_unit } = chart;

  return (
    <div
      style={{
        background: "var(--surface-1)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-md)",
        padding: 20,
        marginTop: 8,
        maxWidth: 720,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>{title}</h3>
          {subtitle && <p style={{ margin: "4px 0 0", fontSize: 13, color: "var(--text-muted)" }}>{subtitle}</p>}
        </div>
        <button
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

      <ChartLegend series={series} />

      {showTable ? (
        <DataTable data={data} series={series} unit={y_unit} />
      ) : chart_type === "bar" ? (
        <CategoryBarChart data={data} series={series} unit={y_unit} />
      ) : chart_type === "stacked_bar" ? (
        <StackedBarChart data={data} series={series} unit={y_unit} />
      ) : (
        <TimeSeriesChart type={chart_type} data={data} series={series} unit={y_unit} />
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
