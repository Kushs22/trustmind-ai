import type { Metadata } from "next";
import Link from "next/link";
import { Footer, Header } from "@/components/Header";
import { PageBackground } from "@/components/PageBackground";
import { PrivacyActions } from "@/components/PrivacyActions";

export const metadata: Metadata = {
  title: "Privacy — TrustMind AI",
  description:
    "How TrustMind AI handles your data with transparency, privacy-first design, and GDPR-aligned practices.",
};

const storedItems = [
  "Optional saved check-in summaries (if you choose to save)",
  "Concern level, confidence, and abstention metadata",
  "Account email (only if you create an account)",
  "Anonymous session preferences",
];

const notStoredItems = [
  "Raw text after private mode deletion",
  "Diagnoses or clinical labels",
  "Location, contacts, or device identifiers",
  "Data used to train public AI models",
];

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#fafbfc]">
      <Header />
      <main className="relative overflow-hidden">
        <PageBackground />
        <div className="relative mx-auto max-w-4xl px-6 py-12 lg:px-8 lg:py-16">
          <div className="mb-10 text-center">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-600">
              Privacy & Safety
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-800 sm:text-4xl">
              Your data, your control
            </h1>
            <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-slate-600">
              TrustMind AI is built for transparency. We explain what we store,
              what we never store, and how you stay in control.
            </p>
          </div>

          <div className="space-y-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
              <h2 className="text-lg font-semibold text-slate-800">
                What data is stored
              </h2>
              <ul className="mt-4 space-y-3">
                {storedItems.map((item) => (
                  <li
                    key={item}
                    className="flex items-start gap-3 text-sm text-slate-700"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
              <h2 className="text-lg font-semibold text-slate-800">
                What is not stored
              </h2>
              <ul className="mt-4 space-y-3">
                {notStoredItems.map((item) => (
                  <li
                    key={item}
                    className="flex items-start gap-3 text-sm text-slate-700"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-2xl border border-teal-100 bg-gradient-to-br from-teal-50/80 to-blue-50/50 p-6 sm:p-8">
              <h2 className="text-lg font-semibold text-slate-800">
                Anonymous & private mode
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-700">
                You can use TrustMind AI without creating an account. When
                &quot;Analyse privately&quot; is enabled, your text is processed
                for insights without linking the check-in to your identity.
                Private sessions can be excluded from saved history entirely.
              </p>
              <p className="mt-3 text-sm leading-relaxed text-slate-700">
                Data is not used to train public models. Your wellbeing text is
                never fed into shared AI training datasets.
              </p>
            </div>

            <p className="rounded-xl border border-amber-100 bg-amber-50/60 px-4 py-3 text-sm text-slate-700">
              <strong className="font-medium text-amber-800">
                No diagnosis disclaimer:
              </strong>{" "}
              TrustMind AI provides supportive, text-based wellbeing insights
              only. It does not diagnose conditions or replace professional
              care.
            </p>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
              <h2 className="text-lg font-semibold text-slate-800">
                GDPR & privacy-first commitment
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-700">
                We follow privacy-by-design principles aligned with GDPR
                expectations: minimal collection, clear purpose, user access,
                and the right to deletion. You can export or delete your data at
                any time once backend services are connected.
              </p>
            </div>

            <PrivacyActions />

            <div className="text-center">
              <Link
                href="/analyse"
                className="inline-flex h-11 items-center justify-center rounded-xl bg-teal-600 px-6 text-sm font-medium text-white hover:bg-teal-700"
              >
                Start a private check-in
              </Link>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
