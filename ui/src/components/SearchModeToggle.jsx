const MODES = [
  { id: "semantic", label: "🧠 Semantic",  desc: "Understands meaning"   },
  { id: "keyword",  label: "🔤 Keyword",   desc: "Exact word match"       },
  { id: "hybrid",   label: "⚡ Hybrid",    desc: "Best of both"           },
  { id: "compare",  label: "⚖️ Compare",   desc: "Side by side view"      },
];

export default function SearchModeToggle({ mode, onChange }) {
  return (
    <div className="mode-toggle">
      {MODES.map((m) => (
        <button
          key={m.id}
          onClick={() => onChange(m.id)}
          className={`mode-btn ${mode === m.id ? "active" : ""}`}
        >
          <span className="mode-label">{m.label}</span>
          <span className="mode-desc">{m.desc}</span>
        </button>
      ))}
    </div>
  );
}
