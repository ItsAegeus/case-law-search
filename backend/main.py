from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import requests
import logging
import json
import os

# Initialize FastAPI app
app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with frontend URL for better security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up logging
logging.basicConfig(level=logging.INFO)

# CourtListener API URL
COURTLISTENER_API_URL = "https://www.courtlistener.com/api/rest/v4/search/"

# ✅ Serve static files for frontend (Search page)
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def serve_homepage():
    """Serve the search bar page."""
    index_path = "static/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return JSONResponse(content={"error": "index.html not found. Please ensure it is in the 'static' folder."}, status_code=404)

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
            # ✅ Fix: Ensure 'court' is a dictionary before calling .get()
            court_info = result.get("court", "Unknown Court")
            if isinstance(court_info, str):  
                court_name = "Unknown Court"
            else:
                court_name = court_info.get("name", "Unknown Court")

            cases.append({
                "📌 Case Name": result.get("caseName", "Unknown"),
                "📜 Citation": result.get("citation", "No citation available"),
                "⚖️ Court": court_name,
                "📅 Date Decided": result.get("dateFiled", "Unknown Date"),
                "📄 Summary": result.get("snippet", "No summary available"),
                "🔗 Full Case": f"https://www.courtlistener.com/opinion/{result.get('id')}/"
            })

        response_data = {
            "message": f"✅ {len(cases)} case(s) found for query: '{query}'.",
            "query": query,
            "results": cases
        }

        # ✅ Pretty-print the JSON response before sending it
        formatted_json = json.dumps(response_data, indent=4)

        return JSONResponse(content=json.loads(formatted_json))

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Failed to fetch case law data: {str(e)}")
        raise HTTPException(status_code=500, detail="❌ Error: Could not fetch case law data.")

# ✅ Ensure FastAPI runs on Railway-compatible settings
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)