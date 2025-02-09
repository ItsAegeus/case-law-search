import os
import json
import logging
import redis
import requests
import openai

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

# Configure logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
REDIS_URL = os.getenv("REDIS_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Ensure Redis and OpenAI API key are set
if not REDIS_URL:
    raise ValueError("❌ REDIS_URL is missing! Set it in Railway environment variables.")

if not OPENAI_API_KEY:
    logging.error("❌ Missing OPENAI_API_KEY! AI summaries will not work.")

# Initialize Redis client
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

# Initialize FastAPI app
app = FastAPI()

# Set up rate limiting (max 10 searches per minute per user)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)

# Mount the static folder for frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve index.html for the frontend
@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

# Function to fetch case law from CourtListener API (with Redis caching)
def fetch_case_law(query: str):
    """Fetches case law data from CourtListener API with Redis caching."""
    cache_key = f"case_law:{query}"
    cached_data = redis_client.get(cache_key)

    if cached_data:
        logging.info(f"✅ Cache HIT for: {query}")
        return json.loads(cached_data)  # Return cached result

    logging.info(f"❌ Cache MISS for: {query}. Fetching from API...")

    url = f"https://www.courtlistener.com/api/rest/v4/search/?q={query}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        # Store in Redis with a 10-minute expiration
        redis_client.setex(cache_key, 600, json.dumps(data))
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ API Error: {str(e)}")
        return {"error": "Failed to fetch case law data"}

# Function to generate AI case summaries (cached)
def generate_ai_summary(case_summary: str) -> str:
    """Uses OpenAI GPT to summarize case law, with Redis caching."""

    if not OPENAI_API_KEY:
        return "AI Analysis not available (missing API key)."

    cache_key = f"ai_summary:{hash(case_summary)}"
    cached_summary = redis_client.get(cache_key)

    if cached_summary:
        logging.info("✅ Cache HIT for AI Summary")
        return cached_summary

    logging.info("❌ Cache MISS for AI Summary. Generating with OpenAI...")

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)  # ✅ Correct new API usage

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a legal AI assistant that summarizes case law."},
                {"role": "user", "content": f"Summarize this legal case:\n\n{case_summary}"}
            ],
            temperature=0.7,
            max_tokens=500  # Increased from 300 to 500
        )

        summary = response.choices[0].message.content.strip()

        # Store AI summary in Redis for 24 hours
        redis_client.setex(cache_key, 86400, summary)
        return summary
    except Exception as e:
        logging.error(f"❌ OpenAI API Error: {str(e)}")
        return "AI Analysis unavailable due to an API error."

# Case law search endpoint (with filtering & sorting)
@app.get("/search")
@limiter.limit("10/minute")  # Max 10 searches per minute per user
async def search_case_law(request: Request, query: str, court: str = None, sort: str = "relevance"):
    """Handles search requests with filtering and sorting."""
    raw_data = fetch_case_law(query)

    if "error" in raw_data:
        return JSONResponse(content={"message": "Failed to fetch case law", "results": []}, status_code=500)

    results = raw_data.get("results", [])

    # 🔹 Apply Court Filtering
    if court:
        results = [case for case in results if case.get("court", "").lower() == court.lower()]

    # 🔹 Apply Sorting
    if sort == "date_desc":
        results.sort(key=lambda x: x.get("dateFiled", "0000-00-00"), reverse=True)
    elif sort == "date_asc":
        results.sort(key=lambda x: x.get("dateFiled", "9999-99-99"))

    return JSONResponse(content={"message": f"{len(results)} case(s) found for query: {query}", "results": results})

# Start FastAPI with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)