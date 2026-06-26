"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, deleteAccount } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";

export function PrivacyActions() {
  const router = useRouter();
  const [deleted, setDeleted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  async function handleDeleteData() {
    if (!isAuthenticated()) {
      setError("Sign in or continue anonymously before deleting your data.");
      return;
    }

    setError(null);
    setIsDeleting(true);

    try {
      await deleteAccount();
      setDeleted(true);
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
    <div className="rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-6 shadow-sm">
      <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Your controls</h2>
      <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
        You can request deletion of stored check-ins and account data at any
        time. This permanently removes your account and all associated history
        from the server.
      </p>

      {error && (
        <div
          className="mt-4 rounded-xl border border-red-100 bg-red-50/80 px-4 py-3 text-sm text-red-800"
          role="alert"
        >
          {error}
        </div>
      )}

      {!isAuthenticated() && !deleted && (
        <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
          <Link href="/login" className="font-medium text-teal-700 hover:underline">
            Log in
          </Link>{" "}
          or{" "}
          <Link href="/analyse" className="font-medium text-teal-700 hover:underline">
            continue anonymously
          </Link>{" "}
          to manage your data.
        </p>
      )}

      <button
        type="button"
        onClick={handleDeleteData}
        disabled={isDeleting || deleted || !isAuthenticated()}
        className="mt-4 inline-flex h-11 items-center justify-center rounded-xl border border-slate-200 px-5 text-sm font-medium text-slate-700 dark:text-slate-300 transition-colors hover:border-red-200 hover:bg-red-50 hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isDeleting ? "Deleting…" : "Delete my data"}
      </button>

      {deleted && (
        <p className="mt-3 text-sm text-teal-700">
          Your account and associated data have been deleted.
        </p>
      )}
    </div>
  );
}
