import { LandingNav } from "./landing-nav";
import { HeroSection } from "./hero-section";
import { FeaturesSection } from "./features-section";
import { DemoSection } from "./demo-section";
import { PricingSection } from "./pricing-section";
import { Footer } from "./footer";

export function LandingPage() {
  return (
    <div style={{ background: "var(--background)" }}>
      <LandingNav />
      <HeroSection />
      <FeaturesSection />
      <DemoSection />
      <PricingSection />
      <Footer />
    </div>
  );
}
