from fastapi import FastAPI, Query, HTTPException
import requests
import os
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI()

# Environment Variables
PORT = int(os.getenv("PORT", 8000))
COURTLISTENER_API = "https://www.courtlistener.com/api/rest/v3/opinions/"

@app.get("/")
def home():
    return {"message": "Case Law Search API is Running"}

@app.get("/search")
def search_cases(query: str = Query(..., description="Enter legal keywords or case name")):
    try:
        logger.info(f"Searching for case law with query: {query}")

        # Make a request to CourtListener API
        response = requests.get(COURTLISTENER_API, params={"q": query, "page_size": 5})

        # Check if the request was successful
        if response.status_code != 200:
            logger.error(f"Failed to fetch data from CourtListener: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to fetch data from CourtListener")

        data = response.json()
        results = []

        # Extract case details from the API response
        for case in data.get("results", []):
            results.append({
                "case_name": case.get("caseName", "Unknown"),
                "citation": case.get("citation", "N/A"),
                "court": case.get("court", {}).get("name", "Unknown Court"),
                "date_decided": case.get("dateFiled", "Unknown"),
                "summary": case.get("plain_text", "No summary available")[:500]  # Limit summary length
            })

        logger.info(f"Found {len(results)} cases for query: {query}")
        return {"query": query, "cases": results}

    except Exception as e:
        logger.error(f"Error during case search: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Run the server (For Local Development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
