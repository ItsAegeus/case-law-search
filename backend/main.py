from fastapi import FastAPI, Query, HTTPException
import requests
import os
import logging
import time  # Import time module for delay

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI()

# Environment Variables
PORT = int(os.getenv("PORT", 8000))

# Correct CourtListener API v4 Endpoint for case law (opinions)
COURTLISTENER_API_V4 = "https://www.courtlistener.com/api/rest/v4/opinions/"

# Read API key from Railway
API_KEY = os.getenv("COURTLISTENER_API_KEY")

@app.get("/")
def home():
    return {"message": "Case Law Search API v4 is Running"}

@app.get("/search")
def search_cases(query: str = Query(..., description="Enter legal keywords or case name")):
    try:
        logger.info(f"Searching for case law with query: {query}")

        # API v4 parameters (use "search" instead of "q")
        params = {
            "search": query,  
            "page_size": 3,   # Limit to 3 results
            "format": "json"
        }

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; CaseLawBot/1.0; +https://your-website.com)",
            "Accept": "application/json"
        }

        # Add API key if available
        if API_KEY:
            headers["Authorization"] = f"Token {API_KEY}"

        # Try up to 3 times if the response is 202
        for attempt in range(3):
            response = requests.get(COURTLISTENER_API_V4, params=params, headers=headers)
            logger.info(f"Response Status: {response.status_code}")

            if response.status_code == 200:
                break  # Successful request, proceed
            elif response.status_code == 202:
                logger.info(f"Request still processing (202). Waiting before retrying...")
                time.sleep(2)  # Wait 2 seconds before retrying
            else:
                return {"error": "Failed to fetch case data", "status_code": response.status_code, "response": response.text}

        # Ensure response is JSON
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            return {"error": "Invalid JSON response", "response": response.text[:500]}

        # Ensure results exist
        if "results" not in data or not data["results"]:
            return {"error": "No case law results found", "query": query}

        results = []

        for case in data["results"]:
            results.append({
                "case_name": case.get("caseName", "Unknown"),
                "citation": case.get("citation", "N/A"),
                "court": case.get("court", {}).get("name", "Unknown Court"),
                "date_decided": case.get("dateFiled", "Unknown"),
                "summary": case.get("plain_text", "No summary available")[:250]  # Use plain_text for summary
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