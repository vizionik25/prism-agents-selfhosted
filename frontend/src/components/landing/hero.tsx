import Link from "next/link"

export function LandingHero() {
  return (
    <section
      className="text-center py-24 px-6 relative overflow-hidden"
      style={{ background: "linear-gradient(160deg,#050510 0%,#0d0d2b 40%,#1a0533 70%,#050510 100%)" }}
    >
      <div className="absolute inset-0" style={{ background: "radial-gradient(ellipse at 50% 0%,rgba(0,245,255,0.07),transparent 60%)" }} />
      <div className="absolute top-0 left-0 right-0 h-px" style={{ background: "linear-gradient(90deg,transparent,#00f5ff,#ff00ff,transparent)" }} />
      <div className="relative max-w-2xl mx-auto">
        <div
          className="inline-block text-xs font-semibold uppercase tracking-widest px-4 py-1.5 rounded-full border mb-6"
          style={{ color: "#00f5ff", borderColor: "rgba(0,245,255,0.25)", background: "rgba(0,245,255,0.04)" }}
        >
          AI-Powered Media Generation
        </div>
        <h1 className="text-5xl font-black leading-tight mb-4" style={{ color: "white" }}>
          Generate{" "}
          <span style={{ color: "#00f5ff", textShadow: "0 0 24px rgba(0,245,255,0.35)" }}>anything</span>.
          <br />Every format.{" "}
          <span style={{ color: "#ff00ff", textShadow: "0 0 24px rgba(255,0,255,0.35)" }}>One workspace.</span>
        </h1>
        <p className="text-base leading-relaxed mb-8 max-w-md mx-auto" style={{ color: "rgba(255,255,255,0.5)" }}>
          Images, video, 3D models, music and more — all powered by AI, from a single chat interface.
        </p>
        <div className="flex gap-3 justify-center">
          <Link
            href="/login"
            className="px-6 py-3 rounded-lg text-sm font-bold"
            style={{ background: "linear-gradient(135deg,#00c8ff,#0070ff)", color: "#050510" }}
          >
            Start for free
          </Link>
          <a
            href="#use-cases"
            className="px-6 py-3 rounded-lg text-sm border"
            style={{ color: "white", background: "rgba(255,255,255,0.06)", borderColor: "rgba(255,255,255,0.12)" }}
          >
            See examples
          </a>
        </div>
        <p className="text-xs mt-4" style={{ color: "rgba(255,255,255,0.2)" }}>
          5 free generations. No credit card required.
        </p>
      </div>
    </section>
  )
}
