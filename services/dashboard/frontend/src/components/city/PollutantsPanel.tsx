// src/components/city/PollutantsPanel.tsx
import type { Pollutants } from "../../api/client";

const LABELS: Record<keyof Pollutants, string> = {
  co: "CO", no: "NO", no2: "NO₂", o3: "O₃",
  so2: "SO₂", pm2_5: "PM2.5", pm10: "PM10", nh3: "NH₃",
};

type PollutantsPanelProps = {
  pollutants: Pollutants;
};

export default function PollutantsPanel({ pollutants }: PollutantsPanelProps) {
  return (
    <div className="border border-border-default rounded-lg p-4">
      <p className="text-xs text-content-subtle mb-3">Pollutants (μg/m³)</p>
      <div className="grid grid-cols-4 gap-3">
        {(Object.keys(LABELS) as (keyof Pollutants)[]).map((key) => (
          <div key={key} className="text-center">
            <p className="text-xs text-content-subtle">{LABELS[key]}</p>
            <p className="text-sm font-medium text-content">
              {pollutants[key] ?? "—"}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}