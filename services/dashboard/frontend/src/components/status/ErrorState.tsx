// src/components/ErrorState.tsx
type ErrorStateProps = {
  message: string;
  onRetry: () => void;
};

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="px-6 py-8">
      <div className="border border-red-200 bg-red-50 rounded-lg p-6 text-center">
        <p className="text-sm text-red-600">Something went wrong loading the dashboard.</p>
        <p className="mt-1 text-xs text-red-400">{message}</p>
        <button
          onClick={onRetry}
          className="mt-4 border border-red-300 rounded-lg px-4 py-2 text-sm text-red-600 hover:bg-red-100 transition-colors"
        >
          Try again
        </button>
      </div>
    </div>
  );
}