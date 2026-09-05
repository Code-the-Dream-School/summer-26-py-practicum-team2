import { useState, useEffect } from "react";
import Header from "./components/layout/Header";
import Footer from "./components/layout/Footer";
// import CitySummary from "./components/city/CitySummary";
import TrendChart from "./components/charts/TrendChart";
// import CitySelector from "./components/city/CitySelector";
import CityOverviewGrid from "./components/city/CityOverviewGrid";
import CityMultiSelect from "./components/city/CityMultiSelect";
import ComparisonChart from "./components/charts/ComparisonChart";
import AggregatesChart from "./components/charts/AggregatesChart";
import Tabs from "./components/layout/Tabs";
import LoadingState from "./components/status/LoadingState";
import ErrorState from "./components/status/ErrorState";
import {
  fetchCities,
  fetchCityTrend,
  fetchCitiesOverview,
  type CityListItem,
  type CityTrend,
  type CityOverview,
} from "./api/client";

const CHART_TABS = [
  { id: "hourly", label: "Hourly" },
  { id: "history", label: "History" },
  { id: "compare", label: "Compare" },
];

function App() {
  const [cities, setCities] = useState<CityListItem[]>([]);
  const [overview, setOverview] = useState<CityOverview[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedCity, setSelectedCity] = useState<CityTrend | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [compareData, setCompareData] = useState<CityTrend[]>([]);
  const [activeTab, setActiveTab] = useState("hourly");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCitiesData = () => {
    Promise.all([fetchCities(), fetchCitiesOverview()])
      .then(([citiesData, overviewData]) => {
        setCities(citiesData);
        setOverview(overviewData);
        if (citiesData.length > 0) setSelectedId(citiesData[0].id);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchCitiesData();
  }, []);

  const handleRetry = () => {
    setLoading(true);
    setError(null);
    fetchCitiesData();
  };

  useEffect(() => {
    if (!selectedId) return;
    fetchCityTrend(selectedId)
      .then(setSelectedCity)
      .catch((err) => setError(err.message));
  }, [selectedId]);

  useEffect(() => {
    Promise.resolve()
      .then(() =>
        compareIds.length === 0
          ? []
          : Promise.all(compareIds.map((id) => fetchCityTrend(id)))
      )
      .then(setCompareData)
      .catch((err) => setError(err.message));
  }, [compareIds]);

  const toggleCompare = (id: string) => {
    setCompareIds((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} onRetry={handleRetry} />;
  if (!selectedCity || !selectedId) return null;

  return (
    <div className="min-h-screen flex flex-col bg-surface">
      <Header />
      <main className="flex-1 px-6 py-8 space-y-6">
        <CityOverviewGrid cities={overview} selectedId={selectedId} onSelect={setSelectedId} />
        {/* <div className="flex justify-left">
          <CitySelector cities={cities} selectedId={selectedId} onSelect={setSelectedId} />
        </div> 
        <CitySummary cityName={selectedCity.cityName} aqi={selectedCity.aqi} /> */}

        <div className="space-y-4">
          <Tabs tabs={CHART_TABS} activeId={activeTab} onChange={setActiveTab} />

          {activeTab === "hourly" && (
            <TrendChart cityName={selectedCity.cityName} data={selectedCity.trend} />
          )}

          {activeTab === "history" && (
            <AggregatesChart cityId={selectedId} cityName={selectedCity.cityName} />
          )}

          {activeTab === "compare" && (
            <div className="space-y-3">
              <p className="text-sm text-gray-500">Compare cities</p>
              <CityMultiSelect cities={cities} selectedIds={compareIds} onToggle={toggleCompare} />
              <ComparisonChart cities={compareData} />
            </div>
          )}
        </div>

        <div className="border border-dashed border-gray-300 rounded-lg p-12 text-center text-sm text-gray-400">
          Data above is served from the local Flask backend (sample data, not the real database yet).
        </div>
      </main>
      <Footer />
    </div>
  );
}

export default App;