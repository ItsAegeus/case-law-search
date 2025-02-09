import React, { useState } from "react";
import axios from "axios";
import "./App.css"; // Import styles

const Search = () => {
  const [query, setQuery] = useState(""); // Search input
  const [results, setResults] = useState([]); // Search results
  const [loading, setLoading] = useState(false); // Loading state
  const [court, setCourt] = useState(""); // Court filter
  const [sort, setSort] = useState("relevance"); // Sorting option

  const handleSearch = async () => {
    if (!query.trim()) return; // Prevent empty searches

    setLoading(true); // Show loading bar
    setResults([]); // Clear previous results

    try {
      const response = await axios.get(
        `https://case-law-search-production.up.railway.app/search?query=${query}&court=${court}&sort=${sort}`
      );
      setResults(response.data.results);
    } catch (error) {
      console.error("❌ Error fetching case law:", error);
    }

    setLoading(false); // Hide loading bar after request
  };

  return (
    <div className="search-container">
      <h1>🔍 Case Law Search</h1>

      {/* Search Bar */}
      <div className="search-bar">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter case name or keyword..."
        />
        <button onClick={handleSearch}>Search</button>
      </div>

      {/* Filters */}
      <div className="filters">
        <select onChange={(e) => setCourt(e.target.value)}>
          <option value="">All Courts</option>
          <option value="supreme">Supreme Court</option>
          <option value="appeals">Appeals Court</option>
        </select>

        <select onChange={(e) => setSort(e.target.value)}>
          <option value="relevance">Relevance</option>
          <option value="date_desc">Newest First</option>
          <option value="date_asc">Oldest First</option>
        </select>
      </div>

      {/* Loading Bar */}
      {loading && <div className="loading-bar"></div>}

      {/* Search Results */}
      <div className="results">
        {results.length > 0 ? (
          results.map((caseItem, index) => (
            <div key={index} className="case-card">
              <h3>{caseItem["Case Name"] || "Unknown Case"}</h3>
              <p><strong>📜 Citation:</strong> {caseItem.Citation || "No Citation Available"}</p>
              <p><strong>⚖️ Court:</strong> {caseItem.Court || "Unknown Court"}</p>
              <p><strong>📅 Date Decided:</strong> {caseItem["Date Decided"] || "No Date Available"}</p>
              <p><strong>📝 Summary:</strong> {caseItem.Summary || "No Summary Available"}</p>
              <p><strong>🤖 AI Summary:</strong> {caseItem["AI Summary"] || "AI Summary Not Available"}</p>
              <a href={caseItem["Full Case"] || "#"} target="_blank" rel="noopener noreferrer">
                🔗 Read Full Case
              </a>
            </div>
          ))
        ) : (
          !loading && <p className="no-results">No results found.</p>
        )}
      </div>
    </div>
  );
};

export default Search;