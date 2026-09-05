// src/components/layout/Header.tsx
import ThemeToggle from "./ThemeToggle";

export default function Header() {
  return (
    <header className="flex items-center justify-between border-b border-border-default px-6 py-4">
      <div>
        <h1 className="text-2xl font-semibold text-content font-playfair">City Air Tracker</h1>
        <p className="text-xs text-content-subtle mt-0.5">Real-time air quality by city</p>
      </div>
      <ThemeToggle />
    </header>
  );
}