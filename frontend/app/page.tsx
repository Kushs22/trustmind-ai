import { Header, Footer } from "@/components/Header";
import {
  HeroSection,
  TrustBar,
  FeaturesSection,
  PrivacySection,
  HowItWorksSection,
  SocialProofSection,
  CTASection,
} from "@/components/LandingSections";

export default function Home() {
  return (
    <div className="page-shell">
      <Header />
      <main>
        <HeroSection />
        <TrustBar />
        <HowItWorksSection />
        <FeaturesSection />
        <SocialProofSection />
        <PrivacySection />
        <CTASection />
      </main>
      <Footer />
    </div>
  );
}
