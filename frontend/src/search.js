import React, { useState } from "react";
import axios from "axios";
import "./App.css"; // Import styles

const Search = () => {
  const [query, setQuery] = useState(""); // Search input
  const [results, setResults] = useState([]); // Search results
  const [loading, setLoading] = useState(false); // Loading state

  const handleSearch = async () => {
    if (!query.trim()) return; // Prevent empty searches

    setLoading(true); // Show loading bar
    setResults([]); // Clear previous results

    try {
      const response = await axios.get(
        `https://case-law-search-production.up.railway.app/search?query=${query}`
      );
      setResults(response.data.results);
    } catch (error) {
      console.error("❌ Error fetching case law:", error);
    }

    setLoading(false); // Hide loading bar
  };

  return (
    <div className="search-container">
      <h1>🔍 Case Law Search</h1>
      
      {/* Search Input & Button */}
      <div className="search-bar">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Enter case name or keyword..."
        />
        <button onClick={handleSearch}>Search</button>
      </div>

      {/* Loading Bar */}
      {loading && <div className="loading-bar"></div>}

      {/* Search Results */}
      <div className="results">
        {results.length > 0 ? (
          results.map((caseItem, index) => (
            <div key={index} className="case-card">
              <h3>{caseItem["Case Name"]}</h3>
              <p><strong>Court:</strong> {caseItem.Court}</p>
              <p><strong>Date:</strong> {caseItem["Date Decided"]}</p>
              <p><strong>AI Summary:</strong> {caseItem["AI Summary"]}</p>
              <a href={caseItem["Full Case"]} target="_blank" rel="noopener noreferrer">
                📖 Read Full Case
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