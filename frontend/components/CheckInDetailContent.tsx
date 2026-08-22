"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  getCheckIn,
  type CheckInDetail,
} from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import { SupportUrgencyMeter } from "@/components/SupportUrgencyMeter";

export function CheckInDetailContent({ checkInId }: { checkInId: string }) {
  const [detail, setDetail] = useState<CheckInDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!isAuthenticated()) {
      setIsLoading(false);
      setError("Please log in to view this check-in.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const data = await getCheckIn(checkInId);
      setDetail(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setError("This check-in was not found. It may have been deleted.");
      } else if (err instanceof ApiError && err.status === 401) {
        setError("Please log in to view this check-in.");
      } else {
        setError(
          err instanceof ApiError
            ? err.message
            : "Unable to load this check-in.",
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, [checkInId]);

  useEffect(() => {
    void load();
  }, [load]);

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Loading check-in…
        </p>
      </div>
    );
  }

  if (error || !detail) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <p className="text-sm text-slate-600 dark:text-slate-400">
          {error ?? "Check-in not found."}
        </p>
        <Link
          href="/dashboard"
          className="mt-6 inline-flex h-10 items-center justify-center rounded-lg bg-teal-600 px-5 text-sm font-medium text-white hover:bg-teal-700"
        >
          Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link
            href="/dashboard"
            className="text-sm font-medium text-teal-700 hover:underline dark:text-teal-300"
          >
            ← Back to dashboard
          </Link>
          <h1 className="mt-3 text-2xl font-semibold tracking-tight text-slate-800 dark:text-slate-100 sm:text-3xl">
            Saved check-in
          </h1>
          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            {detail.date}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/analyse?continue=1"
            className="inline-flex h-10 items-center justify-center rounded-lg bg-teal-600 px-4 text-sm font-medium text-white hover:bg-teal-700"
          >
            Continue from here
          </Link>
          <Link
            href="/analyse"
            className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 px-4 text-sm font-medium text-slate-700 hover:border-teal-200 hover:bg-teal-50/50 dark:border-slate-600 dark:text-slate-200"
          >
            New check-in
          </Link>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
          Concern: {detail.concern}
        </span>
        <span className="rounded-full bg-teal-50 px-2.5 py-1 text-xs font-medium text-teal-700 dark:bg-teal-950/40 dark:text-teal-200">
          {detail.confidence} confidence
        </span>
        {detail.abstained && (
          <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700 dark:bg-blue-950/40 dark:text-blue-200">
            Abstained
          </span>
        )}
        {detail.is_private && (
          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            Private
          </span>
        )}
      </div>

      {typeof detail.support_urgency === "number" &&
        detail.support_urgency_band && (
          <SupportUrgencyMeter
            score={detail.support_urgency}
            band={detail.support_urgency_band}
            rationale={detail.support_urgency_rationale}
            uncertain={Boolean(detail.support_urgency_uncertain)}
          />
        )}

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:p-8">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
          Reflection
        </h2>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-slate-700 dark:text-slate-300">
          {detail.explanation || "No reflection was stored for this check-in."}
        </p>
      </section>

      {!detail.is_private && detail.preview && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:p-8">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
            What you shared
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
            {detail.preview}
          </p>
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            Only a short preview is kept — original files and full transcripts
            are not stored.
          </p>
        </section>
      )}

      {detail.is_private && (
        <section className="rounded-2xl border border-dashed border-slate-200 bg-slate-50/60 p-6 dark:border-slate-700 dark:bg-slate-800/40 sm:p-8">
          <p className="text-sm text-slate-600 dark:text-slate-400">
            This was a private check-in — raw text was not stored. Themes and
            the saved reflection metadata are shown above.
          </p>
        </section>
      )}

      {detail.safe_next_steps.length > 0 && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:p-8">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
            Suggested next steps
          </h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-slate-700 dark:text-slate-300">
            {detail.safe_next_steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:p-8">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
          Details
        </h2>
        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Uncertainty</dt>
            <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
              {detail.uncertainty_level || "—"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">Grounding</dt>
            <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
              {detail.grounding_status || "—"}
            </dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-slate-500 dark:text-slate-400">Abstention</dt>
            <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
              {detail.abstention_status || "—"}
            </dd>
          </div>
        </dl>
        {detail.safety_note && (
          <p className="mt-4 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
            {detail.safety_note}
          </p>
        )}
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          Evidence sources from the original run are not re-listed in history —
          only the reflection and summary metadata are kept.
        </p>
      </section>
    </div>
  );
}
