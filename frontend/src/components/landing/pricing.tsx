"use client"

import { useState } from "react"
import Link from "next/link"

const TIERS = [
  { name: "Starter", monthly: 19, yearly: 15, credits: 30,  color: "rgba(255,255,255,0.15)", highlight: false },
  { name: "Plus",    monthly: 49, yearly: 39, credits: 100, color: "#00f5ff",                highlight: true  },
  { name: "Pro",     monthly: 99, yearly: 79, credits: 250, color: "#ff00ff",                highlight: false },
]

const PACKS = [
  { credits: 25,  price: "14.99", highlight: false },
  { credits: 75,  price: "39.99", highlight: true  },
  { credits: 200, price: "89.99", highlight: false },
]

export function PricingSection() {
  const [yearly, setYearly] = useState(false)

  return (
    <section id="pricing" className="py-16 px-6 border-t" style={{ background: "#07070f", borderColor: "rgba(255,255,255,0.04)" }}>
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-black mb-4" style={{ color: "white" }}>Simple, credit-based pricing</h2>
          <div className="inline-flex rounded-lg p-0.5 border" style={{ background: "rgba(255,255,255,0.05)", borderColor: "rgba(255,255,255,0.1)" }}>
            <button
              onClick={() => setYearly(false)}
              className="px-5 py-2 rounded-md text-sm font-semibold transition-all"
              style={!yearly ? { background: "rgba(0,245,255,0.15)", border: "1px solid rgba(0,245,255,0.3)", color: "white" } : { color: "rgba(255,255,255,0.4)" }}
              aria-pressed={!yearly}
            >
              Monthly
            </button>
            <button
              onClick={() => setYearly(true)}
              className="px-5 py-2 rounded-md text-sm font-semibold transition-all"
              style={yearly ? { background: "rgba(0,245,255,0.15)", border: "1px solid rgba(0,245,255,0.3)", color: "white" } : { color: "rgba(255,255,255,0.4)" }}
              aria-pressed={yearly}
            >
              Yearly <span style={{ color: "#00f5ff" }}>-20%</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-8">
          {TIERS.map((tier) => (
            <div
              key={tier.name}
              className="rounded-xl p-5 border text-center"
              style={{
                borderColor: tier.highlight ? tier.color : "rgba(255,255,255,0.1)",
                background:  tier.highlight ? `${tier.color}08` : "transparent",
                boxShadow:   tier.highlight ? `0 0 16px ${tier.color}14` : "none",
              }}
            >
              <div className="text-xs uppercase tracking-widest mb-3" style={{ color: tier.highlight ? tier.color : "rgba(255,255,255,0.4)" }}>{tier.name}</div>
              <div className="text-3xl font-black mb-1" style={{ color: "white" }}>${yearly ? tier.yearly : tier.monthly}</div>
              <div className="text-xs mb-4" style={{ color: "rgba(255,255,255,0.3)" }}>/month{yearly ? " billed yearly" : ""}</div>
              <div className="text-xs mb-5" style={{ color: "rgba(255,255,255,0.5)" }}>{tier.credits} credits/mo</div>
              <Link
                href="/login"
                className="block text-xs font-semibold py-2 px-3 rounded-lg"
                style={{ background: tier.highlight ? tier.color : "rgba(255,255,255,0.08)", color: tier.highlight ? "#050510" : "white" }}
              >
                Get started
              </Link>
            </div>
          ))}
          <div className="rounded-xl p-5 border text-center" style={{ borderColor: "rgba(255,255,255,0.08)" }}>
            <div className="text-xs uppercase tracking-widest mb-3" style={{ color: "rgba(255,255,255,0.4)" }}>Enterprise</div>
            <div className="text-xl font-black mb-1" style={{ color: "white" }}>Custom</div>
            <div className="text-xs mb-5 mt-4" style={{ color: "rgba(255,255,255,0.5)" }}>Unlimited credits</div>
            <a href="mailto:hello@prismagents.com" className="block text-xs font-semibold py-2 px-3 rounded-lg" style={{ background: "rgba(255,255,255,0.08)", color: "white" }}>
              Contact sales
            </a>
          </div>
        </div>

        <div className="rounded-xl p-5 border" style={{ borderColor: "rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.02)" }}>
          <p className="text-center text-xs mb-4" style={{ color: "rgba(255,255,255,0.4)" }}>Need more? Top up with credit packs — they never expire</p>
          <div className="grid grid-cols-3 gap-3">
            {PACKS.map((pack) => (
              <div
                key={pack.credits}
                className="text-center py-3 px-2 rounded-lg border"
                style={{
                  borderColor: pack.highlight ? "rgba(0,245,255,0.25)" : "rgba(255,255,255,0.07)",
                  background:  pack.highlight ? "rgba(0,245,255,0.04)" : "transparent",
                }}
              >
                <div className="text-base font-bold" style={{ color: "white" }}>{pack.credits} credits</div>
                <div className="text-sm" style={{ color: pack.highlight ? "#00f5ff" : "rgba(255,255,255,0.4)" }}>${pack.price}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
