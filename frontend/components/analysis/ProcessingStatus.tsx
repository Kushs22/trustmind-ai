"use client";

type ProcessingStatusProps = {
  message: string;
  progress?: number;
};

export function ProcessingStatus({ message, progress }: ProcessingStatusProps) {
  return (
    <div
      className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200"
      role="status"
      aria-live="polite"
    >
      <p>{message}</p>
      {typeof progress === "number" && (
        <div
          className="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
          aria-label="Upload progress"
        >
          <div
            className="h-full rounded-full bg-teal-500"
            style={{ width: `${Math.max(0, Math.min(100, progress))}%` }}
          />
        </div>
      )}
    </div>
  );
}
