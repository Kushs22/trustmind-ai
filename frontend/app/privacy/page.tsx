import type { Metadata } from "next";
import Link from "next/link";
import { Footer, Header } from "@/components/Header";
import { PageBackground } from "@/components/PageBackground";
import { PrivacyActions } from "@/components/PrivacyActions";

export const metadata: Metadata = {
  title: "Privacy — TrustMind AI",
  description:
    "How TrustMind AI stores and processes check-in data for this student/dissertation demo.",
};

const sections: { title: string; body: string[] }[] = [
  {
    title: "What we store",
    body: [
      "Account: email and a hashed password if you sign up (plain passwords are never stored).",
      "Saved check-ins: concern level, confidence, explanations, previews, support-urgency metadata, and optional conversation_json chat threads when you choose to save history.",
      "Anonymous sessions: a temporary account id so the API can associate a browser session — not an email identity.",
    ],
  },
  {
    title: "Where data lives",
    body: [
      "Application data is stored in PostgreSQL hosted on Render (via DATABASE_URL on the API service).",
      "The frontend is served from Vercel; it keeps only your access token in the browser (localStorage), not your check-in history.",
      "This is a university dissertation / public demo — not a commercial clinical product.",
    ],
  },
  {
    title: "Passwords & access",
    body: [
      "Passwords are hashed before storage. We cannot read your password back.",
      "API requests use a bearer token after login. Logging out or deleting your account clears the token from this browser.",
    ],
  },
  {
    title: "Private & anonymous modes",
    body: [
      "You can continue anonymously without an email account.",
      "“Analyse privately” and turning off “save to history” limit what is written to Postgres — private saves may keep metadata without raw text, and unsaved sessions stay on the device for that visit only.",
      "Anonymous / private analyse still works without creating a lasting identity.",
    ],
  },
  {
    title: "Uploads (images & PDFs)",
    body: [
      "Images and PDFs are for analysis context only — not a permanent document vault.",
      "Files are processed in memory / short-lived temp storage on the server, then discarded. Binary uploads are not kept long-term in the database.",
      "If you save a check-in, derived text (for example extracted notes) may appear in previews or conversation history — the original file is not retained as a downloadable archive.",
    ],
  },
  {
    title: "AI / LLM processing",
    body: [
      "To generate insights, text (and extracted upload context) is sent to configured LLM providers (for example OpenAI, and optionally Groq or Gemini depending on deployment settings).",
      "Providers process requests under their own terms. We do not use your wellbeing text to train public models on our side.",
      "Crisis-related language may surface support links; that is not a clinical triage service.",
    ],
  },
  {
    title: "Retention & your rights",
    body: [
      "Saved history remains until you delete it or delete your account.",
      "Signed-in users can export their profile metadata and check-ins as JSON, or permanently delete their account and associated check-ins.",
      "Deleting your account removes your user row and cascaded check_ins from our database and invalidates the session in this browser.",
    ],
  },
];

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[#fafbfc] dark:bg-slate-950">
      <Header />
      <main className="relative overflow-hidden">
        <PageBackground />
        <div className="relative mx-auto max-w-4xl px-6 py-12 lg:px-8 lg:py-16">
          <div className="mb-10 text-center">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-600">
              Privacy & Safety
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-800 dark:text-slate-100 sm:text-4xl">
              Your data, your control
            </h1>
            <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-slate-600 dark:text-slate-400">
              Plain-language practices for this TrustMind AI demo. We explain
              what is stored, where it lives, and how you can export or delete
              it.
            </p>
          </div>

          <div className="space-y-6">
            {sections.map((section) => (
              <div
                key={section.title}
                className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:p-8"
              >
                <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
                  {section.title}
                </h2>
                <ul className="mt-4 space-y-3">
                  {section.body.map((item) => (
                    <li
                      key={item}
                      className="flex items-start gap-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300"
                    >
                      <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}

            <p className="rounded-xl border border-amber-100 bg-amber-50/60 px-4 py-3 text-sm text-slate-700 dark:border-amber-900 dark:bg-amber-950/40 dark:text-slate-300">
              <strong className="font-medium text-amber-800 dark:text-amber-400">
                Not a diagnosis:
              </strong>{" "}
              TrustMind AI offers supportive, text-based wellbeing insights
              only. It does not diagnose conditions, provide emergency services,
              or replace professional care. If you are in crisis, contact local
              emergency services or Samaritans (UK): 116 123.
            </p>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-900 sm:p-8">
              <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
                Honest scope
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                This policy describes how the demo is built today. It is not
                legal advice and is not a claim of GDPR certification or a law
                firm review. We aim for privacy-by-design: minimal collection,
                clear purpose, export, and deletion.
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
