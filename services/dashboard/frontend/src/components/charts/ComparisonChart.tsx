// src/components/ComparisonChart.tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { CityTrend } from "../../api/client";

const LINE_COLORS = ["#2563eb", "#dc2626", "#16a34a", "#d97706", "#7c3aed"];

type ComparisonChartProps = {
  cities: CityTrend[];
};

function mergeByTime(cities: CityTrend[]) {
  const timeMap = new Map<string, Record<string, number | string>>();

  for (const city of cities) {
    for (const point of city.trend) {
      const existing = timeMap.get(point.time) ?? { time: point.time };
      existing[city.cityName] = point.aqi;
      timeMap.set(point.time, existing);
    }
  }

  return Array.from(timeMap.values());
}

export default function ComparisonChart({ cities }: ComparisonChartProps) {
  if (cities.length === 0) {
    return (
      <div className="border border-dashed border-gray-300 rounded-lg p-12 text-center text-sm text-gray-400">
        Select one or more cities to compare
      </div>
    );
  }

  const data = mergeByTime(cities);

  return (
    <div className="border border-gray-200 rounded-lg p-6">
      <p className="text-sm text-gray-500 mb-4">AQI comparison</p>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis dataKey="time" tick={{ fontSize: 12, fill: "#9ca3af" }} axisLine={{ stroke: "#e5e7eb" }} tickLine={false} />
          <YAxis domain={[1, 5]} ticks={[1, 2, 3, 4, 5]} tick={{ fontSize: 12, fill: "#9ca3af" }} axisLine={{ stroke: "#e5e7eb" }} tickLine={false} />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#e5e7eb" }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {cities.map((city, i) => (
            <Line
              key={city.id}
              type="monotone"
              dataKey={city.cityName}
              stroke={LINE_COLORS[i % LINE_COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}