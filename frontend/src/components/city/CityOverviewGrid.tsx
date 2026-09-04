// src/components/CityOverviewGrid.tsx
import AqiBadge from "./AqiBadge";
import type { CityOverview } from "../../api/client";

type CityOverviewGridProps = {
  cities: CityOverview[];
  selectedId: string;
  onSelect: (id: string) => void;
};

export default function CityOverviewGrid({
  cities,
  selectedId,
  onSelect,
}: CityOverviewGridProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-7 gap-3">
      {cities.map((city) => (
        <button
          key={city.id}
          onClick={() => onSelect(city.id)}
          className={`border rounded-lg p-3 text-right transition-colors ${
            city.id === selectedId
              ? "border-gray-900"
              : "border-gray-200 hover:border-gray-400"
          }`}
        >
          <p className="text-sm text-gray-500">{city.cityName}</p>
          <div className="mt-2 flex items-center justify-end gap-2">
            <span className="text-2xl font-semibold text-gray-900">
              {city.aqi}
            </span>
            <AqiBadge aqi={city.aqi} />
          </div>
        </button>
      ))}
    </div>
  );
}
