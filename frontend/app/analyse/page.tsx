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
    <div className="min-h-screen bg-[#fafbfc] dark:bg-slate-950">
      <Header />
      <main className="relative overflow-hidden">
        <PageBackground />
        <div className="relative mx-auto max-w-3xl px-6 py-8 lg:px-8 lg:py-12">
          <div className="mb-6 text-center">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-800 dark:text-slate-100 sm:text-3xl">
              Wellbeing Check-In
            </h1>
            <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              Share how you&apos;re feeling — then keep the conversation going
              in one place. Not a diagnosis or therapy service.
            </p>
          </div>
          <AnalyseForm />
        </div>
      </main>
      <Footer />
    </div>
  );
}
