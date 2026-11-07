"use client";

import type { LocalSupport } from "@/lib/api";

export function LocalSupportCard({ support }: { support: LocalSupport }) {
  if (!support.listings.length && !support.summary) {
    return null;
  }

  return (
    <section className="rounded-2xl border border-indigo-200/80 bg-indigo-50/40 px-4 py-4 shadow-sm dark:border-indigo-900/70 dark:bg-indigo-950/20">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-indigo-800 dark:text-indigo-300">
          Nearby in Bristol · Nyata AI
        </p>
        <span className="text-[11px] font-medium text-indigo-700 dark:text-indigo-400">
          Live local listings
        </span>
      </div>
      {support.summary ? (
        <p className="mt-2 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
          {support.summary}
        </p>
      ) : null}
      {support.listings.length > 0 ? (
        <ul className="mt-3 space-y-3">
          {support.listings.map((item) => (
            <li
              key={`${item.name}-${item.address}`}
              className="rounded-xl border border-indigo-100 bg-white/90 px-3 py-3 dark:border-indigo-900 dark:bg-slate-900/70"
            >
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-50">
                    {item.name}
                  </p>
                  {item.organisation ? (
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      {item.organisation}
                    </p>
                  ) : null}
                </div>
                {item.distance_km != null ? (
                  <span className="text-xs font-medium text-indigo-700 dark:text-indigo-300">
                    {item.distance_km.toFixed(1)} km
                  </span>
                ) : null}
              </div>
              {item.badges.length > 0 ? (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {item.badges.map((badge) => (
                    <span
                      key={badge}
                      className="rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-medium text-indigo-800 dark:bg-indigo-950 dark:text-indigo-200"
                    >
                      {badge}
                    </span>
                  ))}
                </div>
              ) : null}
              {item.when ? (
                <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
                  {item.when}
                </p>
              ) : null}
              {item.address ? (
                <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                  {item.address}
                  {item.postcode ? ` · ${item.postcode}` : ""}
                </p>
              ) : null}
              {item.booking_warning ? (
                <p className="mt-2 text-xs text-amber-800 dark:text-amber-300">
                  {item.booking_warning}
                </p>
              ) : null}
              {item.directions_url ? (
                <a
                  href={item.directions_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-block text-xs font-semibold text-indigo-700 underline dark:text-indigo-300"
                >
                  Directions
                </a>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      {support.disclaimer ? (
        <p className="mt-3 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
          {support.disclaimer}
        </p>
      ) : null}
    </section>
  );
}
