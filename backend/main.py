from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests
import logging

# Initialize FastAPI app
app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with your frontend domain for better security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up logging
logging.basicConfig(level=logging.INFO)

# CourtListener API Base URL
COURTLISTENER_API_URL = "https://www.courtlistener.com/api/rest/v4/search/"

@app.get("/")
def home():
    return {"message": "Welcome to the Case Law Search API!"}

@app.get("/search")
def search_case_law(query: str):
    """Search for case law based on user input."""
    
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required.")

    logging.info(f"Searching case law for query: {query}")

    try:
        response = requests.get(
            COURTLISTENER_API_URL,
            params={"q": query, "type": "o"},
            timeout=10  # Timeout to prevent slow requests
        )
        response.raise_for_status()  # Raise error for bad responses

        data = response.json()

        # Extract relevant case details
        cases = []
        for result in data.get("results", []):
            cases.append({
                "case_name": result.get("caseName", "Unknown"),
                "citation": result.get("citation", "No citation available"),
                "court": result.get("court", {}).get("name", "Unknown Court"),
                "date_decided": result.get("dateFiled", "Unknown Date"),
                "summary": result.get("snippet", "No summary available"),
                "full_case_url": f"https://www.courtlistener.com/opinion/{result.get('id')}/"
            })

        if not cases:
            return {"message": "No cases found for this query.", "cases": []}

        return {"query": query, "cases": cases}

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch case law data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch case law data.")