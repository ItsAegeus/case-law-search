import { useState } from "react";
import axios from "axios";

function App() {
  const [query, setQuery] = useState("");
  const [cases, setCases] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const searchCases = async () => {
    if (!query.trim()) {
      setError("Please enter a real-world scenario.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await axios.get(
        `https://your-railway-url/search?query=${encodeURIComponent(query)}`
      );

      if (response.data.error) {
        setError(response.data.error);
      } else {
        setCases(response.data.cases);
      }
    } catch (err) {
      setError("Failed to fetch case law. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ textAlign: "center", padding: "20px", fontFamily: "Arial" }}>
      <h1>Case Law Search for Officers</h1>
      <p>Enter a situation, and we’ll find relevant case law.</p>
      
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Example: Can I search a vehicle for drugs?"
        style={{ padding: "10px", width: "60%", margin: "10px" }}
      />
      
      <button onClick={searchCases} style={{ padding: "10px" }}>
        Search
      </button>

      {loading && <p>Loading...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      <div style={{ marginTop: "20px", textAlign: "left", maxWidth: "800px", margin: "auto" }}>
        {cases.length > 0 && <h2>Relevant Cases:</h2>}
        {cases.map((caseLaw, index) => (
          <div key={index} style={{ borderBottom: "1px solid #ccc", padding: "10px" }}>
            <h3>{caseLaw.case_name}</h3>
            <p><strong>Citation:</strong> {caseLaw.citation}</p>
            <p><strong>Court:</strong> {caseLaw.court}</p>
            <p><strong>Date:</strong> {caseLaw.date_decided}</p>
            <p><strong>Summary:</strong> {caseLaw.summary}</p>
            <a 
              href={`https://www.courtlistener.com/opinion/${caseLaw.id}/`} 
              target="_blank" 
              rel="noopener noreferrer"
            >
              Read Full Case
            </a>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;