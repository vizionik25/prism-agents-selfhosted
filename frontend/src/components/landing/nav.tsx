import Link from "next/link"

export function LandingNav() {
  return (
    <header
      className="sticky top-0 z-50 border-b"
      style={{ background: "rgba(5,5,16,0.95)", borderColor: "rgba(0,245,255,0.08)", backdropFilter: "blur(12px)" }}
    >
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full" style={{ background: "#00f5ff", boxShadow: "0 0 8px #00f5ff" }} />
          <span className="text-sm font-black uppercase tracking-widest" style={{ color: "white" }}>PrismAgents</span>
        </div>
        <nav className="flex items-center gap-6">
          <a href="#use-cases" className="text-sm" style={{ color: "rgba(255,255,255,0.5)" }}>Use Cases</a>
          <a href="#pricing" className="text-sm" style={{ color: "rgba(255,255,255,0.5)" }}>Pricing</a>
          <Link href="/login" className="text-sm px-4 py-1.5 rounded border" style={{ color: "#00f5ff", borderColor: "rgba(0,245,255,0.4)" }}>
            Sign in
          </Link>
        </nav>
      </div>
    </header>
  )
}
