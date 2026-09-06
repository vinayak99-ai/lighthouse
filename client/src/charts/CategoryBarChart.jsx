import { ResponsiveContainer, BarChart, Bar, CartesianGrid, XAxis, YAxis, Tooltip } from "recharts";
import { colorForIndex, formatCompact, formatDateLabel } from "../lib/chartTheme.js";
import ChartTooltip from "./ChartTooltip.jsx";

export default function CategoryBarChart({ data, series, unit, hoveredSeries, hiddenSeries }) {
  return (
    <ResponsiveContainer width="100%" height={320}>
      <BarChart data={data} margin={{ top: 8, right: 16, left: 8, bottom: 0 }} barGap={2} barCategoryGap="20%">
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
          cursor={{ fill: "var(--gridline)", opacity: 0.4 }}
        />
        {series.map((key, i) => {
          if (hiddenSeries?.has(key)) return null;
          const dimmed = hoveredSeries && hoveredSeries !== key;
          return (
            <Bar
              key={key}
              dataKey={key}
              fill={colorForIndex(i)}
              fillOpacity={dimmed ? 0.35 : 1}
              radius={[4, 4, 0, 0]}
              maxBarSize={24}
              animationDuration={500}
              animationEasing="ease-out"
              style={{ transition: "opacity 0.2s ease" }}
            />
          );
        })}
      </BarChart>
    </ResponsiveContainer>
  );
}
