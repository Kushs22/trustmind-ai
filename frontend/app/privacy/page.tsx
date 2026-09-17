import type { Metadata } from "next";
import Link from "next/link";
import { Footer, Header } from "@/components/Header";
import { PageBackground } from "@/components/PageBackground";
import { PrivacyActions } from "@/components/PrivacyActions";

export const metadata: Metadata = {
  title: "Privacy — TrustMind AI",
  description:
    "How TrustMind AI handles your information, including what we collect and how you can export or delete it.",
};

const sections: { title: string; body: string[] }[] = [
  {
    title: "What we collect",
    body: [
      "If you create an account, we keep your email and a securely stored password. We never store your password in readable form.",
      "If you choose to save a check-in, we keep the reflection you received and the notes needed to show it in your history.",
      "You can also use TrustMind without an account. In that case we do not create a lasting identity for you.",
    ],
  },
  {
    title: "Passwords and access",
    body: [
      "Passwords are stored securely. We cannot see or recover your password.",
      "Choose a password of at least 8 characters, including a letter and a number or symbol.",
      "Signing out or deleting your account ends access from this browser.",
    ],
  },
  {
    title: "Private and anonymous use",
    body: [
      "You can continue without signing up.",
      "If you analyse privately or turn off save to history, your check-in is not kept as a saved record.",
      "Anonymous use still works, and it does not create a lasting account.",
    ],
  },
  {
    title: "Files you upload",
    body: [
      "You can attach an image or PDF to give extra context for a check-in.",
      "Uploads are used only to generate that reflection, then discarded. We do not keep a file library.",
      "If you save a check-in, a short extract may appear in your history. The original file is not stored for download.",
    ],
  },
  {
    title: "How long we keep information",
    body: [
      "Saved history stays until you delete it or delete your account.",
      "You can download a copy of your information, or permanently delete your account and saved check-ins.",
      "Deleting your account removes your profile and history, and signs you out of this browser.",
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
              We keep only what we need to run your check-in, and you can
              export or delete it at any time.
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
                This page describes how we handle information today. It is not
                legal advice. We collect as little as we can, explain why we
                need it, and let you export or delete it.
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
