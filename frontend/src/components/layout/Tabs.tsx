// src/components/Tabs.tsx
type Tab = {
  id: string;
  label: string;
};

type TabsProps = {
  tabs: Tab[];
  activeId: string;
  onChange: (id: string) => void;
};

export default function Tabs({ tabs, activeId, onChange }: TabsProps) {
  return (
    <div className="flex gap-1 border-b border-gray-200">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`text-sm px-4 py-2 border-b-2 -mb-px transition-colors ${
            activeId === tab.id
              ? "border-gray-900 text-gray-900 font-medium"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}