"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, createAnonymousSession, login, register } from "@/lib/api";

type AuthFormProps = {
  mode: "login" | "signup";
};

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isAnonymousLoading, setIsAnonymousLoading] = useState(false);

  const isLogin = mode === "login";

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, password);
      }
      router.push("/dashboard");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to connect. Is the backend running?",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleAnonymous() {
    setError(null);
    setIsAnonymousLoading(true);

    try {
      await createAnonymousSession();
      router.push("/analyse");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to connect. Is the backend running?",
      );
    } finally {
      setIsAnonymousLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-slate-200/80 bg-white dark:border-slate-700/80 dark:bg-slate-900 p-6 shadow-sm sm:p-8">
      {error && (
        <div
          className="mb-5 rounded-xl border border-red-100 bg-red-50/80 px-4 py-3 text-sm text-red-800"
          role="alert"
        >
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        <div>
          <label
            htmlFor={`${mode}-email`}
            className="block text-sm font-medium text-slate-800 dark:text-slate-100"
          >
            Email
          </label>
          <input
            id={`${mode}-email`}
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            required
            disabled={isSubmitting}
            className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/50 px-4 py-3 text-slate-800 dark:text-slate-100 placeholder:text-slate-400 focus:border-teal-300 focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-100 disabled:opacity-60"
          />
        </div>

        <div>
          <label
            htmlFor={`${mode}-password`}
            className="block text-sm font-medium text-slate-800 dark:text-slate-100"
          >
            Password
          </label>
          <input
            id={`${mode}-password`}
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••"
            required
            minLength={isLogin ? 1 : 8}
            disabled={isSubmitting}
            className="mt-2 w-full rounded-xl border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/50 px-4 py-3 text-slate-800 dark:text-slate-100 placeholder:text-slate-400 focus:border-teal-300 focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-100 disabled:opacity-60"
          />
          {!isLogin && (
            <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
              At least 8 characters
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="inline-flex h-12 w-full items-center justify-center rounded-xl bg-teal-600 text-base font-medium text-white shadow-md shadow-teal-600/20 transition-all hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting
            ? "Please wait…"
            : isLogin
              ? "Log in"
              : "Create account"}
        </button>
      </form>

      <div className="mt-6 space-y-4 border-t border-slate-100 pt-6">
        <button
          type="button"
          onClick={handleAnonymous}
          disabled={isAnonymousLoading || isSubmitting}
          className="inline-flex h-11 w-full items-center justify-center rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 text-sm font-medium text-slate-700 dark:text-slate-300 transition-colors hover:border-teal-200 hover:bg-teal-50/50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isAnonymousLoading ? "Starting session…" : "Continue anonymously"}
        </button>
        <p className="text-center text-sm text-slate-500 dark:text-slate-400">
          {isLogin ? "Don't have an account?" : "Already have an account?"}{" "}
          <Link
            href={isLogin ? "/signup" : "/login"}
            className="font-medium text-teal-700 hover:underline"
          >
            {isLogin ? "Sign up" : "Log in"}
          </Link>
        </p>
      </div>
    </div>
  );
}
