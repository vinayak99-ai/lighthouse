import { ResponsiveContainer, LineChart, Line, AreaChart, Area, CartesianGrid, XAxis, YAxis, Tooltip } from "recharts";
import { colorForIndex, formatCompact, formatDateLabel } from "../lib/chartTheme.js";
import ChartTooltip from "./ChartTooltip.jsx";

export default function TimeSeriesChart({ type, data, series, unit }) {
  const Chart = type === "area" ? AreaChart : LineChart;
  return (
    <ResponsiveContainer width="100%" height={320}>
      <Chart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke="var(--gridline)" strokeWidth={1} />
        <XAxis
          dataKey="x"
          tickFormatter={formatDateLabel}
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
          axisLine={{ stroke: "var(--baseline)" }}
          tickLine={false}
          minTickGap={32}
        />
        <YAxis
          tickFormatter={(v) => formatCompact(v, unit)}
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
          axisLine={false}
          tickLine={false}
          width={64}
        />
        <Tooltip
          content={<ChartTooltip unit={unit} seriesOrder={series} />}
          cursor={{ stroke: "var(--baseline)", strokeWidth: 1 }}
        />
        {series.map((key, i) =>
          type === "area" ? (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              stroke={colorForIndex(i)}
              strokeWidth={2}
              fill={colorForIndex(i)}
              fillOpacity={0.1}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--surface-1)" }}
            />
          ) : (
            <Line
              key={key}
              type="monotone"
              dataKey={key}
              stroke={colorForIndex(i)}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, stroke: "var(--surface-1)" }}
            />
          )
        )}
      </Chart>
    </ResponsiveContainer>
  );
}
