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
      <rect width="32" height="32" rx="10" fill="var(--color-accent)" />
      <path
        d="M8 16c0-4.4 3.6-8 8-8s8 3.6 8 8-3.6 8-8 8"
        stroke="white"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="16" cy="16" r="3" fill="var(--color-accent-soft)" />
    </svg>
  );
}

const baseNavLinks = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/resources", label: "Resources" },
  { href: "/privacy", label: "Privacy" },
] as const;

function navClass(active: boolean) {
  return `nav-link inline-flex min-h-12 items-center lg:min-h-0 ${
    active ? "nav-link-active" : ""
  }`;
}

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
    <header className="sticky top-0 z-50 border-b border-[var(--color-border)] bg-[color-mix(in_srgb,var(--color-surface)_95%,transparent)] backdrop-blur-[8px]">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5">
          <LogoMark />
          <span className="text-[17px] font-bold text-[var(--color-accent)]">
            TrustMind AI
          </span>
        </Link>

        <div className="hidden items-center gap-6 lg:flex">
          <a href={sectionHref("how-it-works")} className="nav-link">
            How it works
          </a>
          <a href={sectionHref("features")} className="nav-link">
            Why TrustMind AI
          </a>
          {baseNavLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={navClass(pathname === link.href)}
            >
              {link.label}
            </Link>
          ))}
          {accountLink ? (
            <Link
              href={accountLink.href}
              className={navClass(pathname === accountLink.href)}
            >
              {accountLink.label}
            </Link>
          ) : (
            <button type="button" onClick={handleLogout} className="nav-link">
              Log out
            </button>
          )}
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={openHelpPanel}
            className="btn-crisis hidden min-h-12 items-center px-2 lg:inline-flex"
          >
            Get help now
          </button>
          <ThemeToggle />
          <Link href="/analyse" className="btn-nav-cta hidden sm:inline-flex">
            Check in
          </Link>
          <button
            type="button"
            onClick={() => setMobileOpen((open) => !open)}
            className="inline-flex h-12 w-12 items-center justify-center rounded-[10px] border border-[var(--color-border)] text-[var(--color-text)] lg:hidden"
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
        <div className="border-t border-[var(--color-border)] bg-[var(--color-surface)] px-6 py-2 lg:hidden">
          <div className="flex flex-col">
            <a
              href={sectionHref("how-it-works")}
              onClick={() => setMobileOpen(false)}
              className="nav-link inline-flex min-h-12 items-center"
            >
              How it works
            </a>
            <a
              href={sectionHref("features")}
              onClick={() => setMobileOpen(false)}
              className="nav-link inline-flex min-h-12 items-center"
            >
              Why TrustMind AI
            </a>
            {baseNavLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="nav-link inline-flex min-h-12 items-center"
              >
                {link.label}
              </Link>
            ))}
            {accountLink ? (
              <Link
                href={accountLink.href}
                onClick={() => setMobileOpen(false)}
                className="nav-link inline-flex min-h-12 items-center"
              >
                {accountLink.label}
              </Link>
            ) : (
              <button
                type="button"
                onClick={handleLogout}
                className="nav-link inline-flex min-h-12 items-center text-left"
              >
                Log out
              </button>
            )}
            <button
              type="button"
              onClick={() => {
                setMobileOpen(false);
                openHelpPanel();
              }}
              className="btn-crisis inline-flex min-h-12 items-center text-left"
            >
              Get help now
            </button>
            <Link
              href="/analyse"
              onClick={() => setMobileOpen(false)}
              className="btn-nav-cta mt-2 mb-3 w-full"
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
    <footer className="bg-[#1a1a1a] text-white">
      <div className="mx-auto max-w-6xl px-6 py-16 lg:px-8">
        <div className="grid gap-10 md:grid-cols-2 lg:grid-cols-4">
          <div className="lg:col-span-1">
            <div className="flex items-center gap-2.5">
              <LogoMark />
              <span className="text-[17px] font-bold text-white">
                TrustMind AI
              </span>
            </div>
            <p className="mt-3 max-w-md text-sm leading-relaxed text-[#c8c4be]">
              A calm check-in for anyone who is struggling. Private by default,
              with trusted UK guidance and live Bristol support from Nyata AI.
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#9a9590]">
              Platform
            </p>
            <ul className="mt-3 space-y-2 text-sm text-[#c8c4be]">
              <li>
                <Link href="/analyse" className="hover:text-white">
                  Check in
                </Link>
              </li>
              <li>
                <Link href="/dashboard" className="hover:text-white">
                  Dashboard
                </Link>
              </li>
              <li>
                <Link href="/resources" className="hover:text-white">
                  Resources
                </Link>
              </li>
              <li>
                <Link href="/privacy" className="hover:text-white">
                  Privacy
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#9a9590]">
              Account
            </p>
            <ul className="mt-3 space-y-2 text-sm text-[#c8c4be]">
              <li>
                <Link href="/login" className="hover:text-white">
                  Login
                </Link>
              </li>
              <li>
                <Link href="/signup" className="hover:text-white">
                  Sign up
                </Link>
              </li>
              <li>
                <Link href="/analyse" className="hover:text-white">
                  Continue anonymously
                </Link>
              </li>
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#9a9590]">
              Contact
            </p>
            <ul className="mt-3 space-y-2 text-sm text-[#c8c4be]">
              <li>
                <button
                  type="button"
                  onClick={openHelpPanel}
                  className="text-left hover:text-white"
                >
                  Get help now
                </button>
              </li>
              <li>
                <a
                  href="mailto:support@trustmind.ai?subject=TrustMind%20problem%20report"
                  className="hover:text-white"
                >
                  Report a problem
                </a>
              </li>
              <li>
                <a
                  href="https://nyataai.co.uk"
                  className="hover:text-white"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Nyata AI
                </a>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 border-t border-white/10 pt-6 text-center text-[12px] text-[#9a9590]">
          TrustMind AI is not a diagnosis, therapy, or crisis intervention
          service.
        </div>

        <div className="mt-3 text-center text-[12px] text-[#9a9590]">
          © {new Date().getFullYear()} TrustMind AI · Local Bristol listings in
          collaboration with{" "}
          <a
            href="https://nyataai.co.uk"
            className="text-[#d8f3dc] hover:text-white"
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
