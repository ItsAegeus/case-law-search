import { useState } from "react";
import axios from "axios";

const SearchBar = () => {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);

  const fetchCases = async (q) => {
    if (!q) return;
    try {
      const { data } = await axios.get(`/search?query=${q}`);
      setResults(data.results);
    } catch (error) {
      console.error("Error fetching cases:", error);
    }
  };

  let timeout;
  const handleInputChange = (e) => {
    setQuery(e.target.value);
    clearTimeout(timeout);
    timeout = setTimeout(() => fetchCases(e.target.value), 500); // 500ms debounce
  };

  return (
    <input type="text" value={query} onChange={handleInputChange} placeholder="Search case law..." />
  );
};

export default SearchBar;
