import { useState } from "react";
import axios from "axios";

const API_BASE = "https://your-api-url.railway.app";

export default function App() {
    const [scenario, setScenario] = useState("");
    const [cases, setCases] = useState([]);
    const [loading, setLoading] = useState(false);

    const searchCases = async () => {
        setLoading(true);
        try {
            const res = await axios.get(`${API_BASE}/search/`, { params: { scenario } });
            setCases(res.data.cases);
        } catch (error) {
            console.error("Error fetching cases:", error);
        }
        setLoading(false);
    };

    return (
        <div className="container">
            <h1>Find Case Law</h1>
            <input 
                type="text" 
                placeholder="Describe your legal scenario..." 
                value={scenario} 
                onChange={(e) => setScenario(e.target.value)}
            />
            <button onClick={searchCases} disabled={loading}>
                {loading ? "Searching..." : "Search"}
            </button>

            <div>
                {cases.length > 0 ? (
                    cases.map((c, index) => (
                        <div key={index} className="case-card">
                            <h3>{c.case_name}</h3>
                            <p>{c.summary}</p>
                            <a href={c.link} target="_blank" rel="noopener noreferrer">Read Full Case</a>
                        </div>
                    ))
                ) : (
                    <p>No cases found. Try another search.</p>
                )}
            </div>
        </div>
    );
}
