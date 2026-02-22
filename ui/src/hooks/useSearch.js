import { useState, useCallback } from "react";
import { search, compareSearch } from "../api/searchApi";

export const useSearch = () => {
  const [results, setResults]       = useState([]);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState(null);
  const [latency, setLatency]       = useState(null);

  const runSearch = useCallback(async (query, mode, topK) => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    setComparison(null);

    const start = performance.now();
    try {
      if (mode === "compare") {
        const data = await compareSearch(query, topK);
        setComparison(data);
        setResults([]);
      } else {
        const data = await search(query, mode, topK);
        setResults(data);
      }
      setLatency((performance.now() - start).toFixed(0));
    } catch (err) {
      setError("Search failed. Is the API running?");
    } finally {
      setLoading(false);
    }
  }, []);

  return { results, comparison, loading, error, latency, runSearch };
};
