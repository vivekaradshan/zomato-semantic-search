import ResultCard from "./ResultCard";

export default function ComparisonView({ comparison, query }) {
  return (
    <div className="comparison-wrapper">
      <div className="comparison-header">
        <p className="comparison-query">Results for: <strong>"{query}"</strong></p>
      </div>

      <div className="comparison-grid">
        {/* Keyword Column */}
        <div className="comparison-col">
          <div className="col-header keyword-header">
            🔤 Keyword Search
            <span className="col-subtitle">Matches exact words</span>
          </div>
          {comparison.keyword.map((r, i) => (
            <ResultCard key={r.restaurant_id} result={r} rank={i + 1} />
          ))}
        </div>

        {/* Semantic Column */}
        <div className="comparison-col">
          <div className="col-header semantic-header">
            🧠 Semantic Search
            <span className="col-subtitle">Understands meaning</span>
          </div>
          {comparison.semantic.map((r, i) => (
            <ResultCard key={r.restaurant_id} result={r} rank={i + 1} />
          ))}
        </div>
      </div>
    </div>
  );
}
