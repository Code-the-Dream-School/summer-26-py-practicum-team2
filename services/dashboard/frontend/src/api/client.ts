const API_BASE = "http://localhost:8000/api";

export type CityListItem = {
  id: string;
  cityName: string;
};

export type CityOverview = {
  id: string;
  cityName: string;
  aqi: number;
  observedAt: string;
};

export async function fetchCities(): Promise<CityListItem[]> {
  const res = await fetch(`${API_BASE}/cities`);
  if (!res.ok) throw new Error("Failed to fetch cities");
  return res.json();
}

export type CityTrend = {
  id: string;
  cityName: string;
  aqi: number | null;
  trend: { observedAt: string; aqi: number }[];
};

export async function fetchCityTrend(cityId: string): Promise<CityTrend> {
  const res = await fetch(`${API_BASE}/cities/${cityId}/trend`);
  if (!res.ok) throw new Error(`Failed to fetch trend for ${cityId}`);
  return res.json();
}

export async function fetchCitiesOverview(): Promise<CityOverview[]> {
  const res = await fetch(`${API_BASE}/cities/overview`);
  if (!res.ok) throw new Error("Failed to fetch cities overview");
  return res.json();
}

export type AggregatePoint = {
  date: string;
  aqi: number;
};

export async function fetchCityAggregates(
  cityId: string,
  period: "daily" | "weekly"
): Promise<AggregatePoint[]> {
  const res = await fetch(`${API_BASE}/cities/${cityId}/aggregates?period=${period}`);
  if (!res.ok) throw new Error(`Failed to fetch aggregates for ${cityId}`);
  return res.json();
}
