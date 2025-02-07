import { useState } from "react";
import axios from "axios";

function App() {
  const [query, setQuery] = useState("");
  const [cases, setCases] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const searchCases = async () => {
    if (!query.trim()) {
      setError("Please enter a search term.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await axios.get(`https://your-railway-url/search?query=${encodeURIComponent(query)}`);
      if (response.data.error) {
        setError(response.data.error);
      } else {
        setCases(response.data.cases);
      }
    } catch (err) {
      setError("Failed to fetch case data.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ textAlign: "center", padding: "20px" }}>
      <h1>Case Law Search</h1>
      <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Enter a legal scenario"/>
      <button onClick={searchCases}>Search</button>

      {loading && <p>Loading...</p>}
      {error && <p style={{ color: "red" }}>{error}</p>}

      <div>
        {cases.map((caseLaw, index) => (
          <div key={index}>
            <h3>{caseLaw.case_name}</h3>
            <p>{caseLaw.summary}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;