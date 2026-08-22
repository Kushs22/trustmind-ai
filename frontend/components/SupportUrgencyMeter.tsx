"use client";

export type SupportUrgencyBand = "low" | "moderate" | "elevated" | "urgent";

const BAND_LABEL: Record<SupportUrgencyBand, string> = {
  low: "Low",
  moderate: "Moderate",
  elevated: "Elevated",
  urgent: "Urgent",
};

function barClass(band: SupportUrgencyBand, uncertain: boolean): string {
  if (uncertain && band !== "urgent") {
    return "bg-slate-400 dark:bg-slate-500";
  }
  switch (band) {
    case "urgent":
      return "bg-rose-600 dark:bg-rose-500";
    case "elevated":
      return "bg-amber-600 dark:bg-amber-500";
    case "moderate":
      return "bg-teal-600 dark:bg-teal-500";
    default:
      return "bg-slate-500 dark:bg-slate-400";
  }
}

function badgeClass(band: SupportUrgencyBand, uncertain: boolean): string {
  if (uncertain && band !== "urgent") {
    return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300";
  }
  switch (band) {
    case "urgent":
      return "bg-rose-50 text-rose-800 dark:bg-rose-950/50 dark:text-rose-200";
    case "elevated":
      return "bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-200";
    case "moderate":
      return "bg-teal-50 text-teal-800 dark:bg-teal-950/40 dark:text-teal-200";
    default:
      return "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300";
  }
}

type Props = {
  score: number;
  band: SupportUrgencyBand;
  rationale?: string | null;
  uncertain?: boolean;
  compact?: boolean;
};

export function SupportUrgencyMeter({
  score,
  band,
  rationale,
  uncertain = false,
  compact = false,
}: Props) {
  const clamped = Math.max(0, Math.min(100, Math.round(score)));
  const label = BAND_LABEL[band] ?? "Moderate";

  if (compact) {
    return (
      <span
        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ${badgeClass(band, uncertain)}`}
        title={rationale || undefined}
      >
        Support urgency: {clamped}
        {uncertain ? " · uncertain" : ""}
      </span>
    );
  }

  return (
    <div className="rounded-lg border border-white/80 bg-white p-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Support urgency
          </p>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
            How strongly support is suggested
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-semibold tabular-nums text-slate-800 dark:text-slate-100">
            {clamped}
            <span className="ml-1 text-sm font-medium text-slate-500 dark:text-slate-400">
              / 100
            </span>
          </p>
          <span
            className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${badgeClass(band, uncertain)}`}
          >
            {label}
            {uncertain ? " · uncertain" : ""}
          </span>
        </div>
      </div>

      <div
        className="mt-4 h-2.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-700"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={clamped}
        aria-label="Support urgency"
      >
        <div
          className={`h-full rounded-full transition-[width] duration-500 ease-out ${barClass(band, uncertain)}`}
          style={{ width: `${clamped}%` }}
        />
      </div>

      <p className="mt-3 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
        {rationale?.trim() ||
          "Not a diagnosis or clinical risk score — a gentle guide based on this check-in."}
      </p>
    </div>
  );
}
