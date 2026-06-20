import type { Metadata } from "next";
import { DashboardContent } from "@/components/DashboardContent";
import { Footer, Header } from "@/components/Header";
import { PageBackground } from "@/components/PageBackground";

export const metadata: Metadata = {
  title: "Dashboard — TrustMind AI",
  description:
    "Review your wellbeing check-in history, AI confidence trends, and saved analyses.",
};

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-[#fafbfc]">
      <Header />
      <main className="relative overflow-hidden">
        <PageBackground />
        <div className="relative mx-auto max-w-6xl px-6 py-12 lg:px-8 lg:py-16">
          <div className="mb-10">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-600">
              Your history
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-800 sm:text-4xl">
              Wellbeing dashboard
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-relaxed text-slate-600">
              A privacy-aware overview of your text-based check-ins. Review
              concern levels, AI confidence, and abstention history in one
              place.
            </p>
          </div>
          <DashboardContent />
        </div>
      </main>
      <Footer />
    </div>
  );
}
