import { Header, Footer } from "@/components/Header";
import {
  HeroSection,
  FeaturesSection,
  PrivacySection,
  HowItWorksSection,
  CTASection,
} from "@/components/LandingSections";

export default function Home() {
  return (
    <div className="page-shell">
      <Header />
      <main>
        <HeroSection />
        <HowItWorksSection />
        <FeaturesSection />
        <PrivacySection />
        <CTASection />
      </main>
      <Footer />
    </div>
  );
}
