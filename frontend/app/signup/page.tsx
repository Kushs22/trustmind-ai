import type { Metadata } from "next";
import { AuthForm } from "@/components/AuthForm";
import { Footer, Header } from "@/components/Header";
import { PageBackground } from "@/components/PageBackground";

export const metadata: Metadata = {
  title: "Sign up — TrustMind AI",
  description: "Create a TrustMind AI account or continue anonymously.",
};

export default function SignupPage() {
  return (
    <div className="min-h-screen bg-[#fafbfc]">
      <Header />
      <main className="relative overflow-hidden">
        <PageBackground />
        <div className="relative mx-auto max-w-md px-6 py-12 lg:px-8 lg:py-16">
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-semibold tracking-tight text-slate-800">
              Create your account
            </h1>
            <p className="mt-3 text-sm leading-relaxed text-slate-600">
              Save check-ins and track your wellbeing over time. UI preview only
              — authentication is not connected yet.
            </p>
          </div>
          <AuthForm mode="signup" />
        </div>
      </main>
      <Footer />
    </div>
  );
}
