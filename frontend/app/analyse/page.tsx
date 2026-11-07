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
        <div className="relative mx-auto max-w-3xl px-6 py-12 lg:px-8">
          <div className="mb-6 text-center">
            <h1 className="tracking-tight">Wellbeing Check-In</h1>
            <p className="mx-auto mt-2 max-w-xl text-sm text-[var(--color-text-muted)]">
              For anyone who needs a careful check-in. Not a diagnosis or
              therapy service. Anonymous is the default.
            </p>
          </div>
          <AnalyseForm />
        </div>
      </main>
      <Footer />
    </div>
  );
}
