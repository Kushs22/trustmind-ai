"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, deleteAccount, exportMyData } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";

export function PrivacyActions() {
  const router = useRouter();
  const [deleted, setDeleted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  async function handleExport() {
    if (!isAuthenticated()) {
      setError("Sign in before exporting your data.");
      return;
    }

    setError(null);
    setNotice(null);
    setIsExporting(true);

    try {
      const data = await exportMyData();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "trustmind-data-export.json";
      anchor.click();
      URL.revokeObjectURL(url);
      setNotice("Download started — keep the file private.");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to export your data. Please try again.",
      );
    } finally {
      setIsExporting(false);
    }
  }

  async function handleDeleteData() {
    if (!isAuthenticated()) {
      setError("Sign in before deleting your account.");
      return;
    }

    if (!confirmDelete) {
      setConfirmDelete(true);
      setNotice(
        "Click “Delete my account” again to confirm. This cannot be undone.",
      );
      return;
    }

    setError(null);
    setNotice(null);
    setIsDeleting(true);

    try {
      await deleteAccount();
      setDeleted(true);
      setConfirmDelete(false);
      router.push("/");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to delete your data. Please try again.",
      );
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
        Your controls
      </h2>
      <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
        Signed-in users can download a JSON export of profile metadata and saved
        check-ins, or permanently delete the account (cascades all check-ins and
        clears this browser session).
      </p>

      {error && (
        <div
          className="mt-4 rounded-xl border border-red-100 bg-red-50/80 px-4 py-3 text-sm text-red-800"
          role="alert"
        >
          {error}
        </div>
      )}

      {notice && !error && (
        <div
          className="mt-4 rounded-xl border border-amber-100 bg-amber-50/70 px-4 py-3 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-100"
          role="status"
        >
          {notice}
        </div>
      )}

      {!isAuthenticated() && !deleted && (
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
          <Link href="/login" className="font-medium text-teal-700 hover:underline">
            Log in
          </Link>{" "}
          to export or delete account data. You can still{" "}
          <Link href="/analyse" className="font-medium text-teal-700 hover:underline">
            analyse anonymously
          </Link>{" "}
          without saving history.
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          type="button"
          onClick={handleExport}
          disabled={isExporting || deleted || !isAuthenticated()}
          className="inline-flex h-11 items-center justify-center rounded-xl border border-slate-200 px-5 text-sm font-medium text-slate-700 transition-colors hover:border-teal-200 hover:bg-teal-50 hover:text-teal-800 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:text-slate-200"
        >
          {isExporting ? "Preparing export…" : "Export my data"}
        </button>

        <button
          type="button"
          onClick={handleDeleteData}
          disabled={isDeleting || deleted || !isAuthenticated()}
          className="inline-flex h-11 items-center justify-center rounded-xl border border-slate-200 px-5 text-sm font-medium text-slate-700 transition-colors hover:border-red-200 hover:bg-red-50 hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:text-slate-300"
        >
          {isDeleting
            ? "Deleting…"
            : confirmDelete
              ? "Confirm delete my account"
              : "Delete my account"}
        </button>

        {confirmDelete && !isDeleting && (
          <button
            type="button"
            onClick={() => {
              setConfirmDelete(false);
              setNotice(null);
            }}
            className="inline-flex h-11 items-center justify-center rounded-xl px-3 text-sm font-medium text-slate-500 hover:text-slate-700"
          >
            Cancel
          </button>
        )}
      </div>

      {deleted && (
        <p className="mt-3 text-sm text-teal-700">
          Your account and associated data have been deleted.
        </p>
      )}
    </div>
  );
}
