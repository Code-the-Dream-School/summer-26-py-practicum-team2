// src/components/layout/Footer.tsx
export default function Footer() {
  return (
    <footer className="border-t border-border-default px-6 py-4 text-sm text-content-subtle flex items-center justify-between font-playfair">
      <span>City Air Tracker — data via OpenWeather</span>
      <span>Code the Dream · Team 2 · {new Date().getFullYear()}</span>
    </footer>
  );
}