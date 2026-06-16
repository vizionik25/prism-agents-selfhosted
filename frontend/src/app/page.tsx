"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { LandingNav } from "@/components/landing/nav"
import { LandingHero } from "@/components/landing/hero"
import { MediaStrip } from "@/components/landing/media-strip"
import { UseCases } from "@/components/landing/use-cases"
import { PricingSection } from "@/components/landing/pricing"
import { LandingFooter } from "@/components/landing/footer"
import { AuthRedirect } from "@/components/landing/auth-redirect"

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true"

export default function LandingPage() {
  const router = useRouter()

  useEffect(() => {
    if (DEMO_MODE) {
      router.replace("/boards")
    }
  }, [router])

  if (DEMO_MODE) return null

  return (
    <main style={{ background: "#050510", minHeight: "100vh" }}>
      <AuthRedirect />
      <LandingNav />
      <LandingHero />
      <MediaStrip />
      <UseCases />
      <PricingSection />
      <LandingFooter />
    </main>
  )
}
