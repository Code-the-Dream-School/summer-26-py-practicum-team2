// src/components/CityMultiSelect.tsx
import type { CityListItem } from "../../api/client";

type CityMultiSelectProps = {
  cities: CityListItem[];
  selectedIds: string[];
  onToggle: (id: string) => void;
};

export default function CityMultiSelect({ cities, selectedIds, onToggle }: CityMultiSelectProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {cities.map((city) => {
        const isSelected = selectedIds.includes(city.id);
        return (
          <button
            key={city.id}
            onClick={() => onToggle(city.id)}
            className={`text-sm px-3 py-1.5 rounded-full border transition-colors ${
              isSelected
                ? "border-gray-900 bg-gray-900 text-white"
                : "border-gray-200 text-gray-600 hover:border-gray-400"
            }`}
          >
            {city.cityName}
          </button>
        );
      })}
    </div>
  );
}