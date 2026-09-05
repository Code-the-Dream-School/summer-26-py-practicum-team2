// src/components/CitySummary.tsx
import AqiBadge from "./AqiBadge";

type CitySummaryProps = {
  cityName: string;
  aqi: number;
};

export default function CitySummary({ cityName, aqi }: CitySummaryProps) {
  return (
    <div className="border border-gray-200 rounded-lg p-6 text-right">
      <p className="text-sm text-gray-500">{cityName}</p>
      <div className="mt-2 flex items-center justify-end gap-3">
        <span className="text-4xl font-semibold text-gray-900">{aqi}</span>
        <AqiBadge aqi={aqi} />
      </div>
    </div>
  );
}