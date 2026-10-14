import { Hero } from '@/components/landing/Hero'
import {
  BilingualSection,
  EvidenceSection,
  FaqSection,
  FeaturesSection,
  FinalCta,
  HowItWorksSection,
  LimitsSection,
  PrivacySection,
  ProblemSection,
  TopicsSection,
} from '@/components/landing/Sections'

export default function LandingPage() {
  return (
    <>
      <Hero />
      <ProblemSection />
      <FeaturesSection />
      <HowItWorksSection />
      <TopicsSection />
      <BilingualSection />
      <PrivacySection />
      <EvidenceSection />
      <LimitsSection />
      <FaqSection />
      <FinalCta />
    </>
  )
}
