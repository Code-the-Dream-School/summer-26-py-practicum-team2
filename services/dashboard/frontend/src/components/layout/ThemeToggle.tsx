// src/components/layout/ThemeToggle.tsx
import { useEffect, useState } from "react";
import { Sun, Moon, Monitor } from "lucide-react";

type Theme = "light" | "dark" | "system";

function applyTheme(theme: Theme) {
  const isDark =
    theme === "dark" ||
    (theme === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", isDark);
}

const OPTIONS: { value: Theme; icon: typeof Sun; label: string }[] = [
  { value: "light", icon: Sun, label: "Light" },
  { value: "dark", icon: Moon, label: "Dark" },
  { value: "system", icon: Monitor, label: "System" },
];

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(
    () => (localStorage.getItem("theme") as Theme) || "system"
  );

  useEffect(() => {
    applyTheme(theme);
    localStorage.setItem("theme", theme);
  }, [theme]);

  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handleChange = () => {
      if (theme === "system") applyTheme("system");
    };
    media.addEventListener("change", handleChange);
    return () => media.removeEventListener("change", handleChange);
  }, [theme]);

  const activeIndex = OPTIONS.findIndex((o) => o.value === theme);

  return (
    <div className="relative inline-flex items-center border border-border-default rounded-full p-1 bg-surface-subtle">
      <div
        className="absolute top-1 bottom-1 w-8 rounded-full bg-content shadow-sm transition-transform duration-300 ease-out"
        style={{ transform: `translateX(${activeIndex * 2}rem)` }}
      />
      {OPTIONS.map(({ value, icon: Icon, label }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          aria-label={label}
          className={`relative z-10 w-8 h-8 flex items-center justify-center rounded-full transition-colors ${
            theme === value ? "text-surface" : "text-content-subtle hover:text-content"
          }`}
        >
          <Icon size={15} />
        </button>
      ))}
    </div>
  );
}