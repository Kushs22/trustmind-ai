"use client";

import type { PendingImage } from "@/hooks/useFileUpload";

type ImagePreviewProps = {
  item: PendingImage;
  disabled?: boolean;
  onRemove: () => void;
  onTextChange: (text: string) => void;
  onToggleIncluded: (included: boolean) => void;
};

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

export function ImagePreview({
  item,
  disabled,
  onRemove,
  onTextChange,
  onToggleIncluded,
}: ImagePreviewProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex gap-3">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={item.previewUrl}
          alt={`Preview of uploaded image ${item.file.name}`}
          className="h-16 w-16 rounded object-cover"
        />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">
            {item.file.name}
          </p>
          <p className="text-xs text-slate-500">
            {formatBytes(item.file.size)} ·{" "}
            <span aria-live="polite">{item.status}</span>
            {item.status === "uploading" ? ` (${item.progress}%)` : ""}
          </p>
          {item.error && (
            <p className="mt-1 text-xs text-rose-600" role="alert">
              {item.error}
            </p>
          )}
          {item.result?.warnings?.length ? (
            <p className="mt-1 text-xs text-amber-700 dark:text-amber-300">
              {item.result.warnings.join(" ")}
            </p>
          ) : null}
        </div>
        <button
          type="button"
          onClick={onRemove}
          disabled={disabled}
          className="text-sm text-rose-700 underline dark:text-rose-300"
          aria-label={`Remove ${item.file.name}`}
        >
          Remove
        </button>
      </div>
      {item.status === "processed" && (
        <div className="mt-3 space-y-2">
          <label className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300">
            <input
              type="checkbox"
              checked={item.included}
              disabled={disabled}
              onChange={(e) => onToggleIncluded(e.target.checked)}
            />
            Include extracted text in analysis
          </label>
          <textarea
            value={item.extractedText}
            onChange={(e) => onTextChange(e.target.value)}
            rows={3}
            disabled={disabled || !item.included}
            aria-label={`Extracted text from ${item.file.name}`}
            className="w-full rounded border border-slate-200 bg-slate-50 px-2 py-1.5 text-sm dark:border-slate-600 dark:bg-slate-800"
            placeholder="No text extracted — you can type relevant notes here."
          />
        </div>
      )}
    </div>
  );
}
