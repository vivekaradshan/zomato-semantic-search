import { useState } from "react";
import { Search } from "lucide-react";

export default function SearchBar({ onSearch, loading }) {
  const [query, setQuery] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    onSearch(query);
  };

  return (
    <form onSubmit={handleSubmit} className="search-bar">
      <div className="search-input-wrapper">
        <Search size={20} className="search-icon" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='Try "something light and healthy" or "romantic dinner"...'
          className="search-input"
        />
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="search-button"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>
    </form>
  );
}
