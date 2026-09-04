type CityOption = {
  id: string;
  cityName: string;
};

type CitySelectorProps = {
  cities: CityOption[];
  selectedId: string;
  onSelect: (id: string) => void;
};

export default function CitySelector({
  cities,
  selectedId,
  onSelect,
}: CitySelectorProps) {
  return (
    <select
      value={selectedId}
      onChange={(e) => onSelect(e.target.value)}
      className="border border-gray-200 rounded-lg px-3 py-2 text-sm text-gray-700"
    >
      {cities.map((city) => (
        <option key={city.id} value={city.id}>
          {city.cityName}
        </option>
      ))}
    </select>
  );
}
