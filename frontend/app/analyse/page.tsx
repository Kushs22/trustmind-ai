import type { Metadata } from "next";
import { AnalyseForm } from "@/components/AnalyseForm";
import { Footer, Header } from "@/components/Header";
import { PageBackground } from "@/components/PageBackground";

export const metadata: Metadata = {
  title: "Wellbeing Check-In — TrustMind AI",
  description:
    "A calm, private text-based wellbeing check-in. This is not a diagnosis or therapy service.",
};

export default function AnalysePage() {
  return (
    <div className="page-shell">
      <Header />
      <main className="relative overflow-hidden">
        <PageBackground />
        <div className="relative mx-auto max-w-3xl px-4 pb-10 pt-8 sm:px-6 lg:px-8">
          <div className="mb-5 text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-800 dark:text-teal-300">
              Private check-in
            </p>
            <h1 className="font-display mt-2 text-4xl text-stone-900 dark:text-stone-50">
              How are you, really?
            </h1>
            <p className="mx-auto mt-2 max-w-lg text-sm leading-relaxed text-stone-600 dark:text-stone-400">
              Not a diagnosis or therapy service. Anonymous is the default.
            </p>
          </div>
          <AnalyseForm />
        </div>
      </main>
      <Footer />
    </div>
  );
}
