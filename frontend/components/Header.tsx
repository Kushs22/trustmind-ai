"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { BrandMark } from "@/components/BrandMark";
import { openHelpPanel } from "@/components/HelpChrome";
import { ThemeToggle } from "@/components/ThemeToggle";
import { AUTH_CHANGED_EVENT, isAuthenticated, logout } from "@/lib/auth";

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
    <header className="sticky top-0 z-[100] h-14 border-b border-[var(--color-border)] bg-[color-mix(in_srgb,var(--color-surface)_92%,transparent)] backdrop-blur-[16px] backdrop-saturate-[1.8] md:h-16">
      <nav className="page-wrap relative flex h-full items-center justify-between">
        <Link href="/" className="relative z-[101] shrink-0">
          <BrandMark />
        </Link>

        <div className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-8 lg:flex">
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
              className={`nav-link ${pathname === link.href ? "nav-link-active" : ""}`}
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="relative z-[101] flex items-center gap-3">
          {accountLink ? (
            <Link
              href={accountLink.href}
              className={`nav-link hidden sm:inline-flex ${
                pathname === accountLink.href ? "nav-link-active" : ""
              }`}
            >
              {accountLink.label}
            </Link>
          ) : (
            <button
              type="button"
              onClick={handleLogout}
              className="nav-link hidden sm:inline-flex"
            >
              Log out
            </button>
          )}
          <ThemeToggle />
          <Link href="/analyse" className="btn-nav-cta hidden sm:inline-flex">
            Check in
          </Link>
          <button
            type="button"
            onClick={() => setMobileOpen((open) => !open)}
            className="inline-flex h-12 w-12 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] lg:hidden"
            aria-expanded={mobileOpen}
            aria-label="Toggle navigation menu"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
              {mobileOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5M3.75 17.25h16.5" />
              )}
            </svg>
          </button>
        </div>
      </nav>

      {mobileOpen && (
        <div className="border-b border-[var(--color-border)] bg-[var(--color-surface)] lg:hidden">
          <div className="page-wrap flex flex-col">
            {[
              { href: sectionHref("how-it-works"), label: "How it works" },
              { href: sectionHref("features"), label: "Why TrustMind AI" },
            ].map((item) => (
              <a
                key={item.label}
                href={item.href}
                onClick={() => setMobileOpen(false)}
                className="nav-link flex min-h-12 items-center border-b border-[var(--color-border)]"
              >
                {item.label}
              </a>
            ))}
            {baseNavLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMobileOpen(false)}
                className="nav-link flex min-h-12 items-center border-b border-[var(--color-border)]"
              >
                {link.label}
              </Link>
            ))}
            {accountLink ? (
              <Link
                href={accountLink.href}
                onClick={() => setMobileOpen(false)}
                className="nav-link flex min-h-12 items-center border-b border-[var(--color-border)]"
              >
                {accountLink.label}
              </Link>
            ) : (
              <button
                type="button"
                onClick={handleLogout}
                className="nav-link flex min-h-12 items-center border-b border-[var(--color-border)] text-left"
              >
                Log out
              </button>
            )}
            <Link
              href="/analyse"
              onClick={() => setMobileOpen(false)}
              className="btn-nav-cta my-3 w-full"
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
    <footer className="border-t border-[var(--color-dark-border)] bg-[var(--color-dark-bg)] pt-16 pb-8 text-[var(--color-dark-text)]">
      <div className="page-wrap grid grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-4">
        <div className="lg:col-span-1">
          <BrandMark inverted />
          <p className="mt-3 max-w-sm text-[14px] text-[var(--color-dark-muted)]">
            A calm check-in for anyone who is struggling. Private by default,
            with trusted UK guidance and live Bristol support from Nyata AI.
          </p>
          <a
            href="https://nyataai.co.uk"
            target="_blank"
            rel="noopener noreferrer"
            className="mt-4 inline-flex items-center gap-1 text-[14px] text-[var(--color-dark-muted)] hover:text-[var(--color-dark-text)]"
          >
            Local listings powered by Nyata AI →
          </a>
        </div>

        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-dark-muted)]">
            Platform
          </p>
          <ul className="mt-3 space-y-2 text-[14px] text-[var(--color-dark-muted)]">
            <li><Link href="/analyse" className="hover:text-[var(--color-dark-text)]">Check in</Link></li>
            <li><Link href="/dashboard" className="hover:text-[var(--color-dark-text)]">Dashboard</Link></li>
            <li><Link href="/resources" className="hover:text-[var(--color-dark-text)]">Resources</Link></li>
            <li><Link href="/privacy" className="hover:text-[var(--color-dark-text)]">Privacy</Link></li>
          </ul>
        </div>

        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-dark-muted)]">
            Account
          </p>
          <ul className="mt-3 space-y-2 text-[14px] text-[var(--color-dark-muted)]">
            <li><Link href="/login" className="hover:text-[var(--color-dark-text)]">Login</Link></li>
            <li><Link href="/signup" className="hover:text-[var(--color-dark-text)]">Sign up</Link></li>
            <li><Link href="/analyse" className="hover:text-[var(--color-dark-text)]">Continue anonymously</Link></li>
          </ul>
        </div>

        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-dark-muted)]">
            Stay grounded
          </p>
          <ul className="mt-3 space-y-3 text-[14px] text-[var(--color-dark-muted)]">
            <li>HTTPS encrypted</li>
            <li>No ads · No data sold</li>
            <li>
              <button type="button" onClick={openHelpPanel} className="text-left hover:text-[var(--color-dark-text)]">
                Get help now
              </button>
            </li>
          </ul>
        </div>
      </div>

      <div className="page-wrap mt-10 flex flex-col gap-3 border-t border-[var(--color-dark-border)] pt-6 text-[13px] text-[var(--color-dark-muted)] md:flex-row md:items-center md:justify-between">
        <p>
          © {new Date().getFullYear()} TrustMind AI · Local Bristol listings in
          collaboration with{" "}
          <a
            href="https://nyataai.co.uk"
            className="hover:text-[var(--color-dark-text)]"
            target="_blank"
            rel="noopener noreferrer"
          >
            Nyata AI
          </a>
          .
        </p>
        <div className="flex gap-4">
          <a href="mailto:support@trustmind.ai?subject=TrustMind%20problem%20report" className="hover:text-[var(--color-dark-text)]">
            Report a problem
          </a>
          <Link href="/privacy" className="hover:text-[var(--color-dark-text)]">
            Privacy
          </Link>
        </div>
      </div>
      <p className="page-wrap mt-4 text-[13px] text-[var(--color-dark-muted)]">
        TrustMind AI is not a diagnosis, therapy, or crisis intervention
        service.
      </p>
    </footer>
  );
}
