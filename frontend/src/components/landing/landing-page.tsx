import { LandingNav } from "./landing-nav";
import { HeroSection } from "./hero-section";
import { SearchDemoSection } from "./search-demo-section";
import { BeforeAfterSection } from "./before-after-section";
import { PipelineSection } from "./pipeline-section";
import { EvolutionTimeline } from "./evolution-timeline";
import { StatsSection } from "./stats-section";
import { CtaSection } from "./cta-section";
import { Footer } from "./footer";

export function LandingPage() {
  return (
    <div style={{ background: "var(--background)" }}>
      <LandingNav />
      <HeroSection />
      <SearchDemoSection />
      <BeforeAfterSection />
      <PipelineSection />
      <EvolutionTimeline />
      <StatsSection />
      <CtaSection />
      <Footer />
    </div>
  );
}
