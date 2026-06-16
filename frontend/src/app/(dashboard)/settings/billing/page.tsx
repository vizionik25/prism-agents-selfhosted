"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { api } from "@/lib/api"
import { useBillingStore } from "@/stores"

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true"
const SELF_HOSTED = process.env.NEXT_PUBLIC_SELF_HOSTED === "true"

export default function BillingPage() {
  const router = useRouter()
  const { tier, subscriptionCredits, packCredits, creditsResetAt, fetchStatus } = useBillingStore()

  useEffect(() => {
    if (DEMO_MODE || SELF_HOSTED) {
      router.replace("/boards")
      return
    }
    fetchStatus()
  }, [fetchStatus, router])

  if (DEMO_MODE || SELF_HOSTED) return null

  return (
    <div className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Billing</h1>

      <div className="rounded-xl border p-5 mb-6 space-y-3">
        <h2 className="text-base font-semibold">Current Plan</h2>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Plan</span>
          <span className="font-semibold capitalize">{tier.replace("_", " ").toLowerCase()}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Subscription credits</span>
          <span className="font-semibold">{subscriptionCredits}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">Pack credits (never expire)</span>
          <span className="font-semibold">{packCredits}</span>
        </div>
        {creditsResetAt && (
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Credits reset</span>
            <span className="text-sm">{new Date(creditsResetAt).toLocaleDateString()}</span>
          </div>
        )}
      </div>

      <p className="text-sm text-muted-foreground">
        Billing is managed through Stripe in the cloud version. In self-hosted mode, you provide your own API keys.
      </p>
    </div>
  )
}

