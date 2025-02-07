from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import logging
import uvicorn

# Initialize FastAPI app
app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with frontend URL for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up logging
logging.basicConfig(level=logging.INFO)

# CourtListener API URL
COURTLISTENER_API_URL = "https://www.courtlistener.com/api/rest/v4/search/"

@app.get("/")
def home():
    return {
        "message": "Welcome to the Case Law Search API!",
        "instructions": "Use /search?query=your_search_term to search case law."
    }

@app.get("/search")
def search_case_law(query: str):
    """Search for case law based on user input."""
    
    if not query.strip():
        raise HTTPException(status_code=400, detail="Error: A query parameter is required.")

    logging.info(f"🔍 Searching case law for: {query}")

    try:
        response = requests.get(
            COURTLISTENER_API_URL,
            params={"q": query, "type": "o"},
            timeout=10
        )
        response.raise_for_status()

        data = response.json()
        cases = []

        for result in data.get("results", []):
            cases.append({
                "📌 Case Name": result.get("caseName", "Unknown"),
                "📜 Citation": result.get("citation", "No citation available"),
                "⚖️ Court": result.get("court", {}).get("name", "Unknown Court"),
                "📅 Date Decided": result.get("dateFiled", "Unknown Date"),
                "📄 Summary": result.get("snippet", "No summary available"),
                "🔗 Full Case": f"https://www.courtlistener.com/opinion/{result.get('id')}/"
            })

        if not cases:
            return {
                "message": "No cases found for this query.",
                "query": query,
                "cases": []
            }

        return {
            "message": f"✅ {len(cases)} case(s) found for query: '{query}'.",
            "query": query,
            "results": cases
        }

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Failed to fetch case law data: {str(e)}")
        raise HTTPException(status_code=500, detail="❌ Error: Could not fetch case law data.")

# ✅ Ensure FastAPI runs on Railway-compatible settings
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)