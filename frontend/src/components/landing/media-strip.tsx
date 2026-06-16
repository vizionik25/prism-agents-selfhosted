const MEDIA_TYPES = [
  { label: "Images",   abbr: "IMG", credits: "1 cr",  color: "#00f5ff" },
  { label: "Video",    abbr: "VID", credits: "5 cr",  color: "#ff00ff" },
  { label: "Music",    abbr: "MUS", credits: "3 cr",  color: "#bf5fff" },
  { label: "3D",       abbr: "3D",  credits: "10 cr", color: "#00f5ff" },
  { label: "Research", abbr: "RES", credits: "2 cr",  color: "#ff00ff" },
  { label: "Agents",   abbr: "AGT", credits: "2 cr",  color: "#bf5fff" },
]

export function MediaStrip() {
  return (
    <section className="py-8 px-6 border-t" style={{ background: "#07070f", borderColor: "rgba(255,255,255,0.04)" }}>
      <p className="text-center text-xs uppercase tracking-widest mb-5" style={{ color: "rgba(255,255,255,0.25)" }}>
        Everything you can create
      </p>
      <div className="max-w-2xl mx-auto grid grid-cols-6 gap-3">
        {MEDIA_TYPES.map((m) => (
          <div
            key={m.label}
            className="text-center py-3 px-1 rounded-lg border"
            style={{ borderColor: `${m.color}20`, background: `${m.color}08` }}
          >
            <div className="text-xs font-bold mb-1" style={{ color: m.color }}>{m.abbr}</div>
            <div className="text-xs font-semibold" style={{ color: "white" }}>{m.label}</div>
            <div className="text-xs" style={{ color: "rgba(255,255,255,0.25)" }}>{m.credits}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
