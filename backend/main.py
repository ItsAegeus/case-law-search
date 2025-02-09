from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import requests
import os
import openai
import logging
import aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis = aioredis.from_url(REDIS_URL, decode_responses=True)

async def fetch_case_law(query: str):
    """Check cache before hitting CourtListener API."""
    cache_key = f"case_law:{query}"
    cached_data = await redis.get(cache_key)
    
    if cached_data:
        return json.loads(cached_data)

    # If not in cache, fetch from CourtListener
    url = f"https://www.courtlistener.com/api/rest/v4/search/?q={query}"
    response = requests.get(url)
    if response.status_code == 200:
        case_data = response.json()
        await redis.set(cache_key, json.dumps(case_data), ex=3600)  # Cache for 1 hour
        return case_data
    
    return {"error": "Failed to fetch case law data"}

# Load API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI()

# Mount the static folder for frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html when visiting root URL
@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

# Function to fetch case law from CourtListener API
def fetch_case_law(query: str):
    """Fetches case law data from CourtListener API."""
    url = f"https://www.courtlistener.com/api/rest/v4/search/?q={query}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching case law: {str(e)}")
        return {"error": "Failed to fetch case law data"}

# Function to generate AI summary using OpenAI API
def generate_ai_summary(case_summary: str) -> str:
    """Uses OpenAI GPT to summarize and analyze case law."""
    if not OPENAI_API_KEY:
        return "AI Analysis not available (missing API key)."

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)  # ✅ Correct API call

        response = client.chat.completions.create(
            model="gpt-4-turbo",  # Use GPT-4 Turbo for efficiency
            messages=[
                {"role": "system", "content": "You are a legal AI assistant that summarizes and explains case law."},
                {"role": "user", "content": f"Summarize this legal case in simple terms and explain its significance:\n\n{case_summary}"}
            ],
            temperature=0.7,
            max_tokens=200
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"❌ OpenAI API Error: {str(e)}")
        return "AI Analysis unavailable due to an API error."

# Case law search endpoint
@app.get("/search")
async def search_case_law(query: str):
    """Handles search requests and returns case law data."""
    raw_data = fetch_case_law(query)

    # Handle API errors
    if "error" in raw_data:
        return JSONResponse(content={"message": "Failed to fetch case law", "results": []}, status_code=500)

    results = []
    for case in raw_data.get("results", []):
        summary_text = case.get("summary", "No summary available")
        ai_summary = generate_ai_summary(summary_text) if summary_text else "AI Summary Not Available"

        case_data = {
            "Case Name": case.get("caseName", "Unknown Case"),
            "Citation": case.get("citation", "No Citation Available"),
            "Court": case.get("court", "Unknown Court"),
            "Date Decided": case.get("dateFiled", "No Date Available"),
            "Summary": summary_text,
            "AI Summary": ai_summary,
            "Full Case": case.get("absolute_url", "#")
        }
        results.append(case_data)

    return JSONResponse(content={"message": f"{len(results)} case(s) found for query: {query}", "results": results})

# ✅ Ensure Uvicorn starts when running locally
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)