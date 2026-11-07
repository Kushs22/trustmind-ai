"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { openHelpPanel } from "@/components/HelpChrome";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AUTH_CHANGED_EVENT, isAuthenticated, logout } from "@/lib/auth";

function LogoMark() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className="shrink-0"
    >
      <rect width="32" height="32" rx="10" className="fill-teal-800 dark:fill-teal-500" />
      <path
        d="M8 16c0-4.4 3.6-8 8-8s8 3.6 8 8-3.6 8-8 8"
        stroke="white"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="16" cy="16" r="3" className="fill-teal-100" />
    </svg>
  );
}

const baseNavLinks = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/resources", label: "Resources" },
  { href: "/privacy", label: "Privacy" },
] as const;

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);

  useEffect(() => {
    function syncAuth() {
      setLoggedIn(isAuthenticated());
    }
    syncAuth();
    window.addEventListener(AUTH_CHANGED_EVENT, syncAuth);
    window.addEventListener("storage", syncAuth);
    return () => {
      window.removeEventListener(AUTH_CHANGED_EVENT, syncAuth);
      window.removeEventListener("storage", syncAuth);
    };
  }, []);

  function sectionHref(id: string) {
    return pathname === "/" ? `#${id}` : `/#${id}`;
  }

  function handleLogout() {
    logout();
    setMobileOpen(false);
    router.push("/");
  }

  const accountLink = loggedIn
    ? null
    : ({ href: "/login", label: "Login" } as const);

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--line)] bg-[color-mix(in_srgb,var(--background)_88%,transparent)] backdrop-blur-md">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5">
          <LogoMark />
          <span className="font-display text-xl tracking-tight text-stone-900 dark:text-stone-50">
            TrustMind
          </span>
        </Link>

        <div className="hidden items-center gap-6 lg:flex">
          <a
            href={sectionHref("how-it-works")}
            className="text-sm font-medium text-stone-600 transition-colors hover:text-teal-800 dark:text-stone-400 dark:hover:text-teal-300"
          >
            How it works
          </a>
          <a
            href={sectionHref("features")}
            className="text-sm font-medium text-stone-600 transition-colors hover:text-teal-800 dark:text-stone-400 dark:hover:text-teal-300"
          >
            Why TrustMind AI
          </a>
          {baseNavLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-sm font-medium transition-colors hover:text-teal-800 dark:hover:text-teal-300 ${
                pathname === link.href
                  ? "text-teal-800 dark:text-teal-300"
                  : "text-stone-600 dark:text-stone-400"
              }`}
            >
              {link.label}
            </Link>
          ))}
          {accountLink ? (
            <Link
              href={accountLink.href}
              className={`text-sm font-medium transition-colors hover:text-teal-800 dark:hover:text-teal-300 ${
                pathname === accountLink.href
                  ? "text-teal-800 dark:text-teal-300"
                  : "text-stone-600 dark:text-stone-400"
              }`}
            >
              {accountLink.label}
            </Link>
          ) : (
            <button
              type="button"
              onClick={handleLogout}
              className="text-sm font-medium text-stone-600 transition-colors hover:text-teal-800 dark:text-stone-400 dark:hover:text-teal-300"
            >
              Log out
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <button
            type="button"
            onClick={openHelpPanel}
            className="hidden rounded-full border border-rose-200 px-3 py-1.5 text-xs font-semibold text-rose-800 hover:bg-rose-50 dark:border-rose-900 dark:text-rose-200 dark:hover:bg-rose-950/50 sm:inline-flex"
          >
            Get help now
          </button>
          <ThemeToggle />
          <Link
            href="/analyse"
            className="hidden rounded-full bg-teal-800 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-900 sm:inline-flex dark:bg-teal-500 dark:text-teal-950 dark:hover:bg-teal-400"
          >
            Check in
          </Link>
          <button
            type="button"
            onClick={() => setMobileOpen((open) => !open)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[var(--line)] text-stone-600 dark:text-stone-400 lg:hidden"
            aria-expanded={mobileOpen}
            aria-label="Toggle navigation menu"
          >
            <svg
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth="1.5"
              aria-hidden="true"
            >
              {mobileOpen ? (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M6 18L18 6M6 6l12 12"
                />
              ) : (
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M3.75 6.75h16.5M3.75 12h16.5M3.75 17.25h16.5"
                />
              )}
            </svg>
          </button>
        </div>
      </nav>

      {mobileOpen && (
        <div className="border-t border-[var(--line)] bg-[var(--surface)] px-6 py-4 lg:hidden">
          <div className="flex flex-col gap-3">
            <a
              href={sectionHref("how-it-works")}
              onClick={() => setMobileOpen(false)}
              className="text-sm font-medium text-stone-600 dark:text-stone-400"
            >
              How it works
            </a>
            <a
              href={sectionHref("features")}
              onClick={() => setMobileOpen(false)}
              className="text-sm font-medium text-stone-600 dark:text-stone-400"
            >
              Why TrustMind AI
            </a>
            {baseNavLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="text-sm font-medium text-stone-600 dark:text-stone-400"
              >
                {link.label}
              </Link>
            ))}
            {accountLink ? (
              <Link
                href={accountLink.href}
                onClick={() => setMobileOpen(false)}
                className="text-sm font-medium text-stone-600 dark:text-stone-400"
              >
                {accountLink.label}
              </Link>
            ) : (
              <button
                type="button"
                onClick={handleLogout}
                className="text-left text-sm font-medium text-stone-600 dark:text-stone-400"
              >
                Log out
              </button>
            )}
            <Link
              href="/analyse"
              onClick={() => setMobileOpen(false)}
              className="mt-2 inline-flex h-11 items-center justify-center rounded-full bg-teal-800 text-sm font-medium text-white dark:bg-teal-500 dark:text-teal-950"
            >
              Check in
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-[var(--line)] bg-[var(--surface)]">
      <div className="mx-auto max-w-6xl px-6 py-12 lg:px-8">
        <div className="grid gap-10 md:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-2">
            <div className="flex items-center gap-2.5">
              <LogoMark />
              <span className="font-display text-lg text-stone-900 dark:text-stone-50">TrustMind</span>
            </div>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-stone-500 dark:text-stone-400">
              A calm check-in for anyone who is struggling. Private by default,
              with trusted UK guidance and live Bristol support from Nyata AI.
            </p>
          </div>

          <div>
            <p className="text-sm font-semibold text-stone-800 dark:text-stone-100">Platform</p>
            <ul className="mt-3 space-y-2 text-sm text-stone-500 dark:text-stone-400">
              <li>
                <Link href="/analyse" className="hover:text-teal-700">
                  Check in
                </Link>
              </li>
              <li>
                <Link href="/dashboard" className="hover:text-teal-700">
                  Dashboard
                </Link>
              </li>
              <li>
                <Link href="/resources" className="hover:text-teal-700">
                  Resources
                </Link>
              </li>
              <li>
                <Link href="/privacy" className="hover:text-teal-700">
                  Privacy
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <p className="text-sm font-semibold text-stone-800 dark:text-stone-100">Account</p>
            <ul className="mt-3 space-y-2 text-sm text-stone-500 dark:text-stone-400">
              <li>
                <Link href="/login" className="hover:text-teal-700">
                  Login
                </Link>
              </li>
              <li>
                <Link href="/signup" className="hover:text-teal-700">
                  Sign up
                </Link>
              </li>
              <li>
                <Link href="/analyse" className="hover:text-teal-700">
                  Continue anonymously
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 rounded-2xl border border-[var(--line)] bg-[var(--background)] px-4 py-3 text-center text-sm text-stone-600 dark:text-stone-400">
          TrustMind is not a diagnosis, therapy, or crisis intervention
          service.{" "}
          <a
            href="mailto:support@trustmind.ai?subject=TrustMind%20problem%20report"
            className="text-teal-800 underline-offset-2 hover:underline dark:text-teal-300"
          >
            Report a problem
          </a>
        </div>

        <div className="mt-6 border-t border-[var(--line)] pt-6 text-center text-sm text-stone-400">
          © {new Date().getFullYear()} TrustMind AI · Local Bristol listings in
          collaboration with{" "}
          <a
            href="https://nyataai.co.uk"
            className="text-teal-700 hover:underline dark:text-teal-400"
            target="_blank"
            rel="noopener noreferrer"
          >
            Nyata AI
          </a>
          .
        </div>
      </div>
    </footer>
  );
}
