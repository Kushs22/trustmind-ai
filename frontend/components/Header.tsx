"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

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
      <rect width="32" height="32" rx="8" className="fill-teal-600" />
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

const navLinks = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/resources", label: "Resources" },
  { href: "/privacy", label: "Privacy" },
  { href: "/login", label: "Login" },
] as const;

export function Header() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  function sectionHref(id: string) {
    return pathname === "/" ? `#${id}` : `/#${id}`;
  }

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/80 backdrop-blur-md">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5">
          <LogoMark />
          <span className="text-lg font-semibold tracking-tight text-slate-800">
            TrustMind AI
          </span>
        </Link>

        <div className="hidden items-center gap-6 lg:flex">
          <a
            href={sectionHref("how-it-works")}
            className="text-sm font-medium text-slate-600 transition-colors hover:text-teal-700"
          >
            How it works
          </a>
          <a
            href={sectionHref("features")}
            className="text-sm font-medium text-slate-600 transition-colors hover:text-teal-700"
          >
            Why TrustMind AI
          </a>
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={`text-sm font-medium transition-colors hover:text-teal-700 ${
                pathname === link.href ? "text-teal-700" : "text-slate-600"
              }`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <Link
            href="/analyse"
            className="hidden rounded-lg bg-teal-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-teal-700 sm:inline-flex"
          >
            Start Analysis
          </Link>
          <button
            type="button"
            onClick={() => setMobileOpen((open) => !open)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-600 lg:hidden"
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
        <div className="border-t border-slate-200/80 bg-white px-6 py-4 lg:hidden">
          <div className="flex flex-col gap-3">
            <a
              href={sectionHref("how-it-works")}
              onClick={() => setMobileOpen(false)}
              className="text-sm font-medium text-slate-600"
            >
              How it works
            </a>
            <a
              href={sectionHref("features")}
              onClick={() => setMobileOpen(false)}
              className="text-sm font-medium text-slate-600"
            >
              Why TrustMind AI
            </a>
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="text-sm font-medium text-slate-600"
              >
                {link.label}
              </Link>
            ))}
            <Link
              href="/analyse"
              onClick={() => setMobileOpen(false)}
              className="mt-2 inline-flex h-11 items-center justify-center rounded-lg bg-teal-600 text-sm font-medium text-white"
            >
              Start Analysis
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-6xl px-6 py-12 lg:px-8">
        <div className="grid gap-10 md:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-2">
            <div className="flex items-center gap-2.5">
              <LogoMark />
              <span className="font-semibold text-slate-800">TrustMind AI</span>
            </div>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-slate-500">
              Trustworthy AI wellbeing support for students and everyday users.
              Text-based analysis with privacy, transparency, and care.
            </p>
          </div>

          <div>
            <p className="text-sm font-semibold text-slate-800">Platform</p>
            <ul className="mt-3 space-y-2 text-sm text-slate-500">
              <li>
                <Link href="/analyse" className="hover:text-teal-700">
                  Start Analysis
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
            <p className="text-sm font-semibold text-slate-800">Account</p>
            <ul className="mt-3 space-y-2 text-sm text-slate-500">
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

        <div className="mt-10 rounded-xl border border-slate-200 bg-slate-50/80 px-4 py-3 text-center text-sm text-slate-600">
          TrustMind AI is not a diagnosis, therapy, or crisis intervention
          service.
        </div>

        <div className="mt-6 border-t border-slate-100 pt-6 text-center text-sm text-slate-400">
          © {new Date().getFullYear()} TrustMind AI. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
