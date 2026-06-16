export function LandingFooter() {
  return (
    <footer className="py-5 px-6 border-t flex items-center justify-between" style={{ background: "#030309", borderColor: "rgba(255,255,255,0.04)" }}>
      <div className="flex items-center gap-2">
        <div className="w-1.5 h-1.5 rounded-full opacity-60" style={{ background: "#00f5ff" }} />
        <span className="text-xs" style={{ color: "rgba(255,255,255,0.2)" }}>2026 PrismAgents</span>
      </div>
      <div className="flex gap-5">
        {["Privacy", "Terms", "Contact"].map((link) => (
          <a key={link} href="#" className="text-xs" style={{ color: "rgba(255,255,255,0.2)" }}>{link}</a>
        ))}
      </div>
    </footer>
  )
}
