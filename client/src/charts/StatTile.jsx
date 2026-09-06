import { ResponsiveContainer, LineChart, Line } from "recharts";
import { colorForIndex, formatCompact } from "../lib/chartTheme.js";

// The single-current-value job: "a single current value (+ maybe a trend)
// uses a stat tile, not a one-bar bar chart" (choosing-a-form.md). One
// series -> a hero-figure-sized tile; several -> a KPI row of smaller ones.
// The value stays in text tokens (never the series color); the delta is the
// one place a status color belongs, since it signals direction, not identity.
export default function StatTile({ data, series, unit }) {
  const hero = series.length === 1;
  return (
    <div
      style={{
        display: hero ? "block" : "grid",
        gridTemplateColumns: hero ? undefined : "repeat(auto-fit, minmax(160px, 1fr))",
        gap: 16,
      }}
    >
      {series.map((name, i) => (
        <Tile key={name} name={name} data={data} unit={unit} colorIndex={i} hero={hero} />
      ))}
    </div>
  );
}

function Tile({ name, data, unit, colorIndex, hero }) {
  const values = data.map((d) => d[name]).filter((v) => v !== null && v !== undefined);
  const last = values[values.length - 1] ?? 0;
  const first = values[0] ?? 0;
  const pct = first ? ((last - first) / first) * 100 : 0;
  const up = pct >= 0;
  const sparklineData = data.map((d) => ({ x: d.x, v: d[name] }));

  return (
    <div
      style={{
        border: hero ? "none" : "1px solid var(--border)",
        borderRadius: "var(--radius-sm)",
        padding: hero ? 0 : "14px 16px",
      }}
    >
      <div style={{ fontSize: 13, color: "var(--text-muted)" }}>{name}</div>
      <div
        style={{
          fontSize: hero ? 48 : 26,
          fontWeight: 600,
          color: "var(--text-primary)",
          fontFamily: "var(--font-sans)",
          lineHeight: 1.15,
          margin: "2px 0 4px",
        }}
      >
        {formatCompact(last, unit)}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: up ? "var(--success-text)" : "var(--danger-text)",
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {up ? "↑" : "↓"} {Math.abs(pct).toFixed(1)}%
        </span>
        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>vs period start</span>
      </div>
      {sparklineData.length > 1 && (
        <div style={{ height: hero ? 56 : 32, marginTop: 8 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={sparklineData} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
              {/* De-emphasis hue for the trend context; the accent dot at the
                  end is the only place this tile's own series color appears. */}
              <Line
                type="monotone"
                dataKey="v"
                stroke="var(--baseline)"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="v"
                stroke="none"
                dot={(props) =>
                  props.index === sparklineData.length - 1 ? (
                    <circle key="accent-dot" cx={props.cx} cy={props.cy} r={3} fill={colorForIndex(colorIndex)} />
                  ) : (
                    <circle key={`empty-${props.index}`} r={0} />
                  )
                }
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
