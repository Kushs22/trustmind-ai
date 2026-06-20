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
    <div className="min-h-screen bg-[#fafbfc]">
      <Header />
      <main className="relative overflow-hidden">
        <PageBackground />
        <div className="relative mx-auto max-w-3xl px-6 py-12 lg:px-8 lg:py-16">
          <div className="mb-10 text-center">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-600">
              Private check-in
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-800 sm:text-4xl">
              Wellbeing Check-In
            </h1>
            <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-slate-600">
              Share how you&apos;ve been feeling in your own words. TrustMind AI
              will review your text and offer thoughtful, evidence-informed
              insights.
            </p>
            <p className="mx-auto mt-4 inline-flex rounded-full border border-slate-200 bg-white/80 px-4 py-2 text-sm text-slate-600">
              This is not a diagnosis or therapy service.
            </p>
          </div>

          <AnalyseForm />
        </div>
      </main>
      <Footer />
    </div>
  );
}
