const USE_CASES = [
  { role: "Content Creator", prompt: "Generate a thumbnail for my YouTube video about productivity hacks", command: "/image", color: "#00f5ff" },
  { role: "Game Developer",  prompt: "Create a low-poly 3D tree asset for a fantasy RPG environment",        command: "/3d",    color: "#ff00ff" },
  { role: "Filmmaker",       prompt: "Generate a cinematic shot of a rainy Tokyo street at night",           command: "/video", color: "#bf5fff" },
  { role: "Music Producer",  prompt: "Compose a lo-fi hip-hop track with jazzy chords for a study playlist", command: "/music", color: "#00f5ff" },
]

export function UseCases() {
  return (
    <section id="use-cases" className="py-16 px-6 border-t" style={{ background: "#050510", borderColor: "rgba(255,255,255,0.04)" }}>
      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-10">
          <h2 className="text-2xl font-black mb-2" style={{ color: "white" }}>Built for every creative workflow</h2>
          <p className="text-sm" style={{ color: "rgba(255,255,255,0.4)" }}>Real prompts, real results</p>
        </div>
        <div className="grid grid-cols-2 gap-4">
          {USE_CASES.map((uc) => (
            <div key={uc.role} className="rounded-xl p-5 border" style={{ background: `${uc.color}06`, borderColor: `${uc.color}18` }}>
              <div className="text-xs font-bold uppercase tracking-wider mb-2" style={{ color: uc.color }}>{uc.role}</div>
              <p className="text-sm leading-relaxed mb-3" style={{ color: "rgba(255,255,255,0.65)" }}>&ldquo;{uc.prompt}&rdquo;</p>
              <code className="text-xs" style={{ color: "rgba(255,255,255,0.3)" }}>{uc.command}</code>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
