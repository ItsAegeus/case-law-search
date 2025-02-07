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

# New CourtListener API v4 (Publicly Accessible)
COURTLISTENER_API_V4 = "https://www.courtlistener.com/api/v4/search/"

@app.get("/")
def home():
    return {"message": "Case Law Search API is Running"}

@app.get("/search")
def search_cases(query: str = Query(..., description="Enter legal keywords or case name")):
    try:
        logger.info(f"Searching for case law with query: {query}")

        # New API v4 format
        params = {
            "q": query,  
            "type": "opinion",  # Only get case opinions
            "size": 5,  # Limit results to 5 cases
            "format": "json"  # Ensure JSON response
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; CaseLawBot/1.0; +https://your-website.com)",
            "Accept": "application/json"
        }

        # Make a request to CourtListener v4 API
        response = requests.get(COURTLISTENER_API_V4, params=params, headers=headers)

        # Log response status and text
        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Text: {response.text}")

        if response.status_code != 200:
            logger.error(f"Failed to fetch data from CourtListener v4: {response.text}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch data: {response.text}")

        data = response.json()
        results = []

        # Extract relevant case data
        for case in data.get("results", []):
            results.append({
                "case_name": case.get("caseName", "Unknown"),
                "citation": case.get("citation", "N/A"),
                "court": case.get("court", {}).get("name", "Unknown Court"),
                "date_decided": case.get("dateFiled", "Unknown"),
                "summary": case.get("snippet", "No summary available")[:500]  # Use snippet for preview
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
