"use client"

import { useState, useCallback } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { api } from "@/lib/api"
import { useBillingStore } from "@/stores"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { ExternalLink } from "lucide-react"

const DEMO_MODE = process.env.NEXT_PUBLIC_DEMO_MODE === "true"
const SELF_HOSTED = process.env.NEXT_PUBLIC_SELF_HOSTED === "true"

interface UpgradeModalProps {
  open: boolean
  onClose: () => void
}

export function UpgradeModal({ open, onClose }: UpgradeModalProps) {
  const [showEnterpriseInfo, setShowEnterpriseInfo] = useState(false)
  const { fetchStatus, tier } = useBillingStore()

  // Self-hosted mode: show enterprise info
  if (SELF_HOSTED) {
    return (
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent style={{ background: "#0a0a14", border: "1px solid rgba(0,245,255,0.15)" }}>
          <DialogHeader>
            <DialogTitle style={{ color: "white" }}>Enterprise Self-Hosted</DialogTitle>
            <DialogDescription style={{ color: "rgba(255,255,255,0.7)" }}>
              You are running PrismAgents Self-Hosted. All features are unlocked with unlimited credits.
              <br />
              <br />
              To use API endpoints, you need an Enterprise license which will be available on our website.
              For now, API key access requires a valid license key configured in your environment.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 pt-4">
            <Link
              href="/enterprise-license"
              className="flex items-center gap-2 px-4 py-2 bg-[#00f5ff] text-black font-semibold rounded-xl hover:opacity-90 transition-opacity"
            >
              View License Options
              <ExternalLink className="w-4 h-4" />
            </Link>
            <Button variant="outline" onClick={onClose} style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.1)" }}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  // Demo mode: show disabled message
  if (DEMO_MODE) {
    return (
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent style={{ background: "#0a0a14", border: "1px solid rgba(0,245,255,0.15)" }}>
          <DialogHeader>
            <DialogTitle style={{ color: "white" }}>Demo Mode</DialogTitle>
            <DialogDescription style={{ color: "rgba(255,255,255,0.7)" }}>
              Billing is disabled in demo mode. Upgrade to a paid plan in the cloud version.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={onClose} style={{ background: "rgba(255,255,255,0.1)", border: "1px solid rgba(255,255,255,0.1)" }}>
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  // Cloud mode: show original Stripe upgrade options
  const [view, setView] = useState<"pick" | "checkout">("pick")
  const [yearly, setYearly] = useState(false)
  const [clientSecret, setClientSecret] = useState<string | null>(null)

  const TIERS = [
    { key: "starter" as const, label: "Starter", monthly: 19, yearly: 15, credits: 30 },
    { key: "plus" as const, label: "Plus", monthly: 49, yearly: 39, credits: 100 },
    { key: "pro" as const, label: "Pro", monthly: 99, yearly: 79, credits: 250 },
  ]

  const PACKS = [
    { key: "small" as const, credits: 25, price: "14.99" },
    { key: "medium" as const, credits: 75, price: "39.99" },
    { key: "large" as const, credits: 200, price: "89.99" },
  ]

  const startSubscriptionCheckout = async (tier: "starter" | "plus" | "pro") => {
    const { client_secret } = await api.billing.createSubscriptionCheckout(tier, yearly ? "yearly" : "monthly")
    setClientSecret(client_secret)
    setView("checkout")
  }

  const startPackCheckout = async (pack: "small" | "medium" | "large") => {
    const { client_secret } = await api.billing.createPackCheckout(pack)
    setClientSecret(client_secret)
    setView("checkout")
  }

  const handleClose = () => {
    onClose()
    setView("pick")
    setClientSecret(null)
  }

  const handleCheckoutComplete = useCallback(async () => {
    await fetchStatus()
    handleClose()
  }, [fetchStatus])

  const fetchClientSecret = useCallback(() => Promise.resolve(clientSecret!), [clientSecret])

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) handleClose() }}>
      <DialogContent className="max-w-2xl" style={{ background: "#0a0a14", border: "1px solid rgba(0,245,255,0.15)" }}>
        <DialogHeader>
          <DialogTitle style={{ color: "white" }}>
            {view === "pick" ? "Upgrade your plan" : "Complete payment"}
          </DialogTitle>
        </DialogHeader>

        {view === "pick" && (
          <div className="space-y-6">
            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-semibold" style={{ color: "rgba(255,255,255,0.7)" }}>Subscriptions</p>
                <div className="inline-flex rounded border p-0.5 text-xs" style={{ borderColor: "rgba(255,255,255,0.1)", background: "rgba(255,255,255,0.04)" }}>
                  <button onClick={() => setYearly(false)} className="px-3 py-1 rounded" style={!yearly ? { background: "rgba(0,245,255,0.15)", color: "white" } : { color: "rgba(255,255,255,0.4)" }} aria-pressed={!yearly}>Monthly</button>
                  <button onClick={() => setYearly(true)} className="px-3 py-1 rounded" style={yearly ? { background: "rgba(0,245,255,0.15)", color: "white" } : { color: "rgba(255,255,255,0.4)" }} aria-pressed={yearly}>Yearly <span style={{ color: "#00f5ff" }}>-20%</span></button>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {TIERS.map((tier) => (
                  <button key={tier.key} onClick={() => startSubscriptionCheckout(tier.key)} className="rounded-xl p-4 border text-center transition-all hover:opacity-90" style={{ borderColor: "rgba(0,245,255,0.2)", background: "rgba(0,245,255,0.04)" }}>
                    <div className="text-xs uppercase tracking-wider mb-2" style={{ color: "#00f5ff" }}>{tier.label}</div>
                    <div className="text-2xl font-black" style={{ color: "white" }}>${yearly ? tier.yearly : tier.monthly}</div>
                    <div className="text-xs mt-1" style={{ color: "rgba(255,255,255,0.4)" }}>{tier.credits} credits/mo</div>
                  </button>
                ))}
              </div>
            </div>
            <div>
              <p className="text-sm font-semibold mb-3" style={{ color: "rgba(255,255,255,0.7)" }}>
                Credit packs <span className="text-xs font-normal" style={{ color: "rgba(255,255,255,0.4)" }}>— never expire</span>
              </p>
              <div className="grid grid-cols-3 gap-3">
                {PACKS.map((pack) => (
                  <button key={pack.key} onClick={() => startPackCheckout(pack.key)} className="rounded-xl p-4 border text-center transition-all hover:opacity-90" style={{ borderColor: "rgba(255,0,255,0.2)", background: "rgba(255,0,255,0.04)" }}>
                    <div className="text-lg font-black" style={{ color: "white" }}>{pack.credits} credits</div>
                    <div className="text-sm mt-1" style={{ color: "#ff00ff" }}>${pack.price}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {view === "checkout" && clientSecret && (
          <div className="p-8 text-center" style={{ color: "white" }}>
            <p>Stripe checkout would load here.</p>
            <Button variant="outline" onClick={handleClose} className="mt-4">
              Cancel
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}