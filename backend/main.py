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
COURTLISTENER_API_V4 = "https://www.courtlistener.com/api/v4/search/"
API_KEY = os.getenv("COURTLISTENER_API_KEY")  # Read API key from Railway

@app.get("/")
def home():
    return {"message": "Case Law Search API is Running"}

@app.get("/search")
def search_cases(query: str = Query(..., description="Enter legal keywords or case name")):
    try:
        logger.info(f"Searching for case law with query: {query}")

        # API v4 parameters
        params = {
            "q": query,  
            "type": "opinion",
            "size": 2,
            "format": "json"
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; CaseLawBot/1.0; +https://your-website.com)",
            "Accept": "application/json"
        }

        # Add API key if available
        if API_KEY:
            headers["Authorization"] = f"Token {API_KEY}"

        # Make request to CourtListener API
        response = requests.get(COURTLISTENER_API_V4, params=params, headers=headers)

        logger.info(f"Response Status: {response.status_code}")
        logger.info(f"Response Text: {response.text[:500]}")  # Log only first 500 chars to avoid flooding logs

        # If response is not 200, return raw response
        if response.status_code != 200:
            return {"error": "Failed to fetch case data", "status_code": response.status_code, "response": response.text}

        # Ensure response is JSON
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            return {"error": "Invalid JSON response", "response": response.text[:500]}

        # Ensure results exist
        if "results" not in data:
            return {"error": "Unexpected API response format", "raw_response": data}

        results = []

        for case in data["results"]:
            results.append({
                "case_name": case.get("caseName", "Unknown"),
                "citation": case.get("citation", "N/A"),
                "court": case.get("court", {}).get("name", "Unknown Court"),
                "date_decided": case.get("dateFiled", "Unknown"),
                "summary": case.get("snippet", "No summary available")[:250]
            })

        logger.info(f"Found {len(results)} cases for query: {query}")
        return {"query": query, "cases": results}

    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return {"error": "Failed to connect to CourtListener", "details": str(e)}

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"error": "Internal server error", "details": str(e)}

# Run the server (For Local Development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)