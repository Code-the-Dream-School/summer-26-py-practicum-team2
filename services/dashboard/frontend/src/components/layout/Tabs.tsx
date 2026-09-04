// src/components/layout/Tabs.tsx
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
    <div className="flex gap-1 border-b border-border-default">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={`text-sm px-4 py-2 border-b-2 -mb-px transition-colors ${
            activeId === tab.id
              ? "border-content text-content font-medium"
              : "border-transparent text-content-subtle hover:text-content"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}