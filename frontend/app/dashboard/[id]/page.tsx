import type { Metadata } from "next";
import { CheckInDetailContent } from "@/components/CheckInDetailContent";
import { Footer, Header } from "@/components/Header";
import { PageBackground } from "@/components/PageBackground";

export const metadata: Metadata = {
  title: "Saved check-in — TrustMind AI",
  description: "Review a previous wellbeing check-in reflection and themes.",
};

export default async function CheckInDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <div className="min-h-screen bg-[#fafbfc] dark:bg-slate-950">
      <Header />
      <main className="relative overflow-hidden">
        <PageBackground />
        <div className="relative mx-auto max-w-3xl px-6 py-12 lg:px-8 lg:py-16">
          <CheckInDetailContent checkInId={id} />
        </div>
      </main>
      <Footer />
    </div>
  );
}
