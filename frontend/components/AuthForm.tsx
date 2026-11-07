"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, createAnonymousSession, login, register } from "@/lib/api";
import {
  MIN_PASSWORD_LENGTH,
  validatePasswordStrength,
} from "@/lib/password";

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
  const [showWakeHint, setShowWakeHint] = useState(false);

  const isLogin = mode === "login";
  const busy = isSubmitting || isAnonymousLoading;

  useEffect(() => {
    if (!busy) {
      setShowWakeHint(false);
      return;
    }
    const timer = window.setTimeout(() => setShowWakeHint(true), 4000);
    return () => window.clearTimeout(timer);
  }, [busy]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (!isLogin) {
      const passwordError = validatePasswordStrength(password);
      if (passwordError) {
        setError(passwordError);
        return;
      }
    }

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
          ? err.status === 429
            ? err.message || "Too many attempts. Please wait a minute and try again."
            : err.message
          : "Unable to reach the service right now. It may be waking up — wait a few seconds and try again.",
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
          : "Unable to reach the service right now. It may be waking up — wait a few seconds and try again.",
      );
    } finally {
      setIsAnonymousLoading(false);
    }
  }

  return (
    <div className="surface-card p-6 sm:p-8">
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
            className="block text-sm font-medium text-[var(--color-text)]"
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
            className="mt-2 w-full disabled:opacity-60"
          />
        </div>

        <div>
          <label
            htmlFor={`${mode}-password`}
            className="block text-sm font-medium text-[var(--color-text)]"
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
            minLength={isLogin ? 1 : MIN_PASSWORD_LENGTH}
            disabled={isSubmitting}
            className="mt-2 w-full disabled:opacity-60"
          />
          {!isLogin && (
            <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
              At least {MIN_PASSWORD_LENGTH} characters, with a letter and a
              number or special character
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting
            ? showWakeHint
              ? "Waking the service…"
              : "Please wait…"
            : isLogin
              ? "Log in"
              : "Create account"}
        </button>
      </form>

      {showWakeHint && busy && (
        <p className="mt-3 text-center text-xs text-slate-500 dark:text-slate-400" role="status">
          First request after idle can take up to a minute while the free API
          wakes up.
        </p>
      )}

      <div className="mt-6 space-y-4 border-t border-[var(--color-border)] pt-6">
        <button
          type="button"
          onClick={handleAnonymous}
          disabled={isAnonymousLoading || isSubmitting}
          className="btn-secondary w-full disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isAnonymousLoading
            ? showWakeHint
              ? "Waking the service…"
              : "Starting session…"
            : "Continue anonymously"}
        </button>
        <p className="text-center text-sm text-slate-500 dark:text-slate-400">
          {isLogin ? "Don't have an account?" : "Already have an account?"}{" "}
          <Link
            href={isLogin ? "/signup" : "/login"}
            className="font-medium text-[var(--color-accent)]"
          >
            {isLogin ? "Sign up" : "Log in"}
          </Link>
        </p>
      </div>
    </div>
  );
}
