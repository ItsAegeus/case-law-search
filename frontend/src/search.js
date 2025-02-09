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
        {/* Court Filter */}
        <select onChange={(e) => setCourt(e.target.value)}>
          <option value="">All Courts</option>
          <option value="supreme">Supreme Court</option>
          <option value="appeals">Appeals Court</option>
        </select>

        {/* Sorting Dropdown */}
        <select onChange={(e) => setSort(e.target.value)}>