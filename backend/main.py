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

# CourtListener API v4 (Publicly Accessible)
COURTLISTENER_API_V4 = "https://www.courtlistener.com/api/v4/search/"

@app.get("/")
def home():
    return {"message": "Case Law Search API is Running"}

@app.get("/search")
def search_cases(query: str = Query(..., description="Enter legal keywords or case name")):
    try:
        logger.info(f"Searching for case law with query: {query}")

        # API v4 parameters (reduced result size)
        params = {
            "q": query,  
            "type": "opinion",  # Fetch only case opinions
            "size": 2,  # Limit results to 2 cases (further reducing response size)
            "format": "json"  # Ensure JSON response
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; CaseLawBot/1.0; +https://your-website.com)",
            "Accept": "application/json"
        }

        # Make request to CourtListener API
        response = requests.get(COURTLISTENER_API_V4, params=params, headers=headers)

        if response.status_code != 200:
            logger.error(f"Failed to fetch data from CourtListener v4: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to fetch case data")

        data = response.json()

        if "results" not in data:
            logger.error(f"Unexpected API response: {data}")
            raise HTTPException(status_code=500, detail="Invalid API response format")

        results = []

        # Extract only necessary case details
        for case in data["results"]:
            case_info = {
                "case_name": case.get("caseName", "Unknown"),
                "citation": case.get("citation", "N/A"),
                "court": case.get("court", {}).get("name", "Unknown Court"),
                "date_decided": case.get("dateFiled", "Unknown"),
                "summary": case.get("snippet", "No summary available")[:250]  # Shorter summary
            }
            results.append(case_info)

        logger.info(f"Found {len(results)} cases for query: {query}")

        # Return JSON response properly (not as a dumped string)
        return {"query": query, "cases": results}

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to connect to CourtListener")

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Run the server (For Local Development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)