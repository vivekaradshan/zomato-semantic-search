import { useState } from "react";
import SearchBar          from "./components/SearchBar";
import SearchModeToggle   from "./components/SearchModeToggle";
import ResultCard         from "./components/ResultCard";
import ComparisonView     from "./components/ComparisonView";
import { useSearch }      from "./hooks/useSearch";

export default function App() {
  const [mode, setMode]   = useState("semantic");
  const [query, setQuery] = useState("");
  const [topK, setTopK]   = useState(10);

  const { results, comparison, loading, error, latency, runSearch } = useSearch();

  const handleSearch = (q) => {
    setQuery(q);
    runSearch(q, mode, topK);
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <h1>🍽️ Semantic Restaurant Search</h1>
        <p className="subtitle">
          Find restaurants by mood, craving, or experience — powered by OpenSearch vector search
        </p>
      </header>

      {/* Search Controls */}
      <main className="main">
        <SearchBar onSearch={handleSearch} loading={loading} />
        <SearchModeToggle mode={mode} onChange={setMode} />

        <div className="top-k-control">
          <label>Results: <strong>{topK}</strong></label>
          <input
            type="range" min="5" max="20"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
          />
        </div>

        {/* Stats bar */}
        {latency && !loading && (
          <div className="stats-bar">
            ⚡ {mode === "compare" ? "Dual search" : `${mode} search`}{" "}
            completed in <strong>{latency}ms</strong>
            {results.length > 0 && ` · ${results.length} results`}
          </div>
        )}

        {/* Error */}
        {error && <div className="error-banner">⚠️ {error}</div>}

        {/* Loading */}
        {loading && (
          <div className="loading">
            <div className="spinner" />
            <p>Searching through restaurants...</p>
          </div>
        )}

        {/* Compare Mode */}
        {!loading && comparison && (
          <ComparisonView comparison={comparison} query={query} />
        )}

        {/* Normal Results */}
        {!loading && results.length > 0 && (
          <div className="results-grid">
            {results.map((r, i) => (
              <ResultCard key={r.restaurant_id} result={r} rank={i + 1} />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && !comparison && results.length === 0 && query && (
          <div className="empty-state">
            No results found. Try a different query.
          </div>
        )}
      </main>
    </div>
  );
}
