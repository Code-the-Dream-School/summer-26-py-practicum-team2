// src/components/AqiBadge.tsx
import { CircleCheck, Smile, CloudFog, TriangleAlert, CircleAlert } from "lucide-react";

const AQI_CONFIG: Record<
  number,
  { label: string; icon: typeof CircleCheck; color: string; bg: string }
> = {
  1: { label: "Good", icon: CircleCheck, color: "text-green-600", bg: "bg-green-50" },
  2: { label: "Fair", icon: Smile, color: "text-lime-600", bg: "bg-lime-50" },
  3: { label: "Moderate", icon: CloudFog, color: "text-yellow-600", bg: "bg-yellow-50" },
  4: { label: "Poor", icon: TriangleAlert, color: "text-orange-600", bg: "bg-orange-50" },
  5: { label: "Very Poor", icon: CircleAlert, color: "text-red-600", bg: "bg-red-50" },
};

type AqiBadgeProps = {
  aqi: number;
};

export default function AqiBadge({ aqi }: AqiBadgeProps) {
  const config = AQI_CONFIG[aqi];

  // TODO: discuss with the team how to handle an out-of-range AQI value.
  // OpenWeather's scale is 1-5, and the DB schema (AIR-19 proposal) enforces CHECK (aqi BETWEEN 1 AND 5), so this shouldn't happen in practice.
  // Right now this silently renders nothing if aqi is out of range — no error, no visible fallback.
  // Worth deciding whether we want a visible "unknown" state, a logged warning, or something else.
  if (!config) return null;

  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-sm font-medium ${config.color} ${config.bg}`}
    >
      <Icon size={16} />
      {config.label}
    </span>
  );
}