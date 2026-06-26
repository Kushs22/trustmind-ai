"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  deleteCheckInHistory,
  getCheckIns,
  getDashboardStats,
  type CheckIn,
  type DashboardStats,
} from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";

export function DashboardContent() {
  const [checkIns, setCheckIns] = useState<CheckIn[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showDeleted, setShowDeleted] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const loadDashboard = useCallback(async () => {
    if (!isAuthenticated()) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const [history, dashboardStats] = await Promise.all([
        getCheckIns(),
        getDashboardStats(),
      ]);
      setCheckIns(history);
      setStats(dashboardStats);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Please log in or continue anonymously to view your history.");
      } else {
        setError(
          err instanceof ApiError
            ? err.message
            : "Unable to load dashboard. Is the backend running?",
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard]);

  async function handleDeleteHistory() {
    setIsDeleting(true);
    setError(null);

    try {
      await deleteCheckInHistory();
      setCheckIns([]);
      setStats((current) =>
        current
          ? {
              ...current,
              saved_analyses: 0,
              avg_ai_confidence: null,
              abstention_count: 0,
            }
          : null,
      );
      setShowDeleted(true);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to delete history. Please try again.",
      );
    } finally {
      setIsDeleting(false);
    }
  }

  if (isLoading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-12 text-center shadow-sm">
        <p className="text-sm text-slate-500 dark:text-slate-400">Loading your dashboard…</p>
      </div>
    );
  }

  if (!isAuthenticated()) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-8 text-center shadow-sm">
        <p className="text-sm text-slate-600 dark:text-slate-400">
          Sign in or continue anonymously to view saved check-ins.
        </p>
        <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href="/login"
            className="inline-flex h-10 items-center justify-center rounded-lg bg-teal-600 px-5 text-sm font-medium text-white hover:bg-teal-700"
          >
            Log in
          </Link>
          <Link
            href="/analyse"
            className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 px-5 text-sm font-medium text-slate-700 dark:text-slate-300 hover:border-teal-200 hover:bg-teal-50/50"
          >
            Continue anonymously
          </Link>
        </div>
      </div>
    );
  }

  const avgConfidence =
    stats?.avg_ai_confidence != null ? `${stats.avg_ai_confidence}%` : "—";

  return (
    <div className="space-y-8">
      {error && (
        <div
          className="rounded-xl border border-red-100 bg-red-50/80 px-4 py-3 text-sm text-red-800"
          role="alert"
        >
          {error}
        </div>
      )}

      {showDeleted && checkIns.length === 0 && (
        <div className="rounded-xl border border-teal-100 bg-teal-50/60 px-4 py-3 text-sm text-teal-800">
          History cleared. Your saved check-ins have been removed from the
          server.
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            label: "Saved analyses",
            value: String(stats?.saved_analyses ?? checkIns.length),
            detail: "Text-based check-ins",
          },
          {
            label: "Avg. AI confidence",
            value: avgConfidence,
            detail: "Across saved check-ins",
          },
          {
            label: "Abstention count",
            value: String(stats?.abstention_count ?? 0),
            detail: "When AI declined to predict",
          },
          {
            label: "Privacy mode",
            value: stats?.privacy_mode ?? "Active",
            detail: "Based on your saved check-ins",
          },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-5 shadow-sm"
          >
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {stat.label}
            </p>
            <p className="mt-2 text-2xl font-semibold text-slate-800 dark:text-slate-100">
              {stat.value}
            </p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{stat.detail}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-6 shadow-sm sm:p-8">
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
                  Previous wellbeing check-ins
                </h2>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  Saved analyses from your account
                </p>
              </div>
              <Link
                href="/analyse"
                className="inline-flex h-10 items-center justify-center rounded-lg bg-teal-600 px-4 text-sm font-medium text-white hover:bg-teal-700"
              >
                New check-in
              </Link>
            </div>

            {checkIns.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/50 px-6 py-12 text-center">
                <p className="text-sm text-slate-600 dark:text-slate-400">No saved check-ins yet.</p>
                <Link
                  href="/analyse"
                  className="mt-4 inline-flex text-sm font-medium text-teal-700 hover:underline"
                >
                  Start your first analysis
                </Link>
              </div>
            ) : (
              <ul className="space-y-4">
                {checkIns.map((item) => (
                  <li
                    key={item.id}
                    className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 transition-colors hover:border-teal-100 hover:bg-teal-50/30 dark:border-slate-700 dark:bg-slate-800/50 dark:hover:border-teal-800 dark:hover:bg-teal-950/30"
                  >
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
                          {item.date}
                        </p>
                        <p className="mt-1 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                          {item.preview ??
                            (item.is_private
                              ? "Private check-in · raw text not stored"
                              : "No preview available")}
                        </p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
                          {item.concern}
                        </span>
                        <span className="rounded-full bg-teal-50 px-2.5 py-1 text-xs font-medium text-teal-700">
                          {item.confidence} confidence
                        </span>
                        {item.abstained && (
                          <span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">
                            Abstained
                          </span>
                        )}
                        {item.is_private && (
                          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600 dark:text-slate-400">
                            Private
                          </span>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
              Concern level history
            </h2>
            <ul className="mt-4 space-y-3">
              {checkIns.slice(0, 4).map((item) => (
                <li
                  key={item.id}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-slate-500 dark:text-slate-400">{item.date}</span>
                  <span className="font-medium text-amber-600">
                    {item.concern}
                  </span>
                </li>
              ))}
              {checkIns.length === 0 && (
                <li className="text-sm text-slate-500 dark:text-slate-400">No data available</li>
              )}
            </ul>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
              AI confidence history
            </h2>
            <ul className="mt-4 space-y-3">
              {checkIns.slice(0, 4).map((item) => (
                <li
                  key={item.id}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="text-slate-500 dark:text-slate-400">{item.date}</span>
                  <span className="font-medium text-teal-600">
                    {item.confidence}
                  </span>
                </li>
              ))}
              {checkIns.length === 0 && (
                <li className="text-sm text-slate-500 dark:text-slate-400">No data available</li>
              )}
            </ul>
          </div>

          <button
            type="button"
            onClick={handleDeleteHistory}
            disabled={checkIns.length === 0 || isDeleting}
            className="w-full rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-4 py-3 text-sm font-medium text-slate-700 dark:text-slate-300 transition-colors hover:border-red-200 hover:bg-red-50 hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isDeleting ? "Deleting…" : "Delete history"}
          </button>
        </div>
      </div>
    </div>
  );
}
