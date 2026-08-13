import { LandingNav } from "./landing-nav";
import { HeroSection } from "./hero-section";
import { ProductShotsSection } from "./product-shots-section";
import { SearchDemoSection } from "./search-demo-section";
import { BeforeAfterSection } from "./before-after-section";
import { PipelineSection } from "./pipeline-section";
import { EvolutionTimeline } from "./evolution-timeline";
import { StatsSection } from "./stats-section";
import { TrustSignalsSection } from "./trust-signals-section";
import { CtaSection } from "./cta-section";
import { Footer } from "./footer";

export function LandingPage() {
  return (
    <div style={{ background: "var(--background)" }}>
      <LandingNav />
      {/* T-A11Y-1 (Sprint 25): main 랜드마크 — skip-link 타깃. */}
      <main id="main-content">
        <HeroSection />
        <ProductShotsSection />
        <SearchDemoSection />
        <BeforeAfterSection />
        <PipelineSection />
        <EvolutionTimeline />
        <StatsSection />
        <TrustSignalsSection />
        <CtaSection />
      </main>
      <Footer />
    </div>
  );
}
