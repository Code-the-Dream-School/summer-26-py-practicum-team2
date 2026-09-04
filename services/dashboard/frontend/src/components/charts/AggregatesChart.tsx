// src/components/AggregatesChart.tsx
import { useState, useEffect } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { fetchCityAggregates, type AggregatePoint } from "../../api/client";

type AggregatesChartProps = {
  cityId: string;
  cityName: string;
};

export default function AggregatesChart({ cityId, cityName }: AggregatesChartProps) {
  const [period, setPeriod] = useState<"daily" | "weekly">("daily");
  const [data, setData] = useState<AggregatePoint[]>([]);

  useEffect(() => {
    fetchCityAggregates(cityId, period).then(setData);
  }, [cityId, period]);

  return (
    <div className="border border-gray-200 rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-500">{cityName} — AQI history</p>
        <div className="flex gap-1">
          <button
            onClick={() => setPeriod("daily")}
            className={`text-xs px-3 py-1 rounded-full border transition-colors ${
              period === "daily"
                ? "border-gray-900 bg-gray-900 text-white"
                : "border-gray-200 text-gray-600 hover:border-gray-400"
            }`}
          >
            Daily
          </button>
          <button
            onClick={() => setPeriod("weekly")}
            className={`text-xs px-3 py-1 rounded-full border transition-colors ${
              period === "weekly"
                ? "border-gray-900 bg-gray-900 text-white"
                : "border-gray-200 text-gray-600 hover:border-gray-400"
            }`}
          >
            Weekly
          </button>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: "#9ca3af" }}
            axisLine={{ stroke: "#e5e7eb" }}
            tickLine={false}
          />
          <YAxis
            domain={[1, 5]}
            ticks={[1, 2, 3, 4, 5]}
            tick={{ fontSize: 12, fill: "#9ca3af" }}
            axisLine={{ stroke: "#e5e7eb" }}
            tickLine={false}
          />
           <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, borderColor: "#e5e7eb" }} /> {/*cursor={false} if don't want to display the background bar*/}
          <Bar dataKey="aqi" fill="#2563eb" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}