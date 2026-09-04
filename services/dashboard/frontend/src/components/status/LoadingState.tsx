// src/components/LoadingState.tsx
export default function LoadingState() {
  return (
    <div className="px-6 py-8 space-y-6 animate-pulse">
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="border border-gray-200 rounded-lg p-3 h-20 bg-gray-100" />
        ))}
      </div>
      <div className="border border-gray-200 rounded-lg p-6 h-24 bg-gray-100" />
      <div className="border border-gray-200 rounded-lg p-6 h-64 bg-gray-100" />
    </div>
  );
}