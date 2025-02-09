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

# Function to generate AI case summaries with retry mechanism
def generate_ai_summary(case_summary: str, retry_count=0) -> str:
    """Generates AI summaries with retries if OpenAI returns an empty response."""
    
    if not OPENAI_API_KEY:
        logging.error("❌ Missing OpenAI API Key. AI summaries won't work.")
        return "AI Analysis not available (missing API key)."

    if not case_summary.strip():
        logging.warning("⚠️ Empty case summary received. Using fallback response.")
        return "AI Summary Not Available. This case may lack a public summary."

    cache_key = f"ai_summary:{hash(case_summary)}"
    cached_summary = redis_client.get(cache_key)

    if cached_summary:
        logging.info("✅ Cache HIT for AI Summary")
        return cached_summary

    logging.info(f"❌ Cache MISS for AI Summary. Attempt {retry_count + 1}")

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a legal AI assistant that summarizes case law."},
                {"role": "user", "content": f"Summarize this legal case:\n\n{case_summary}"}
            ],
            temperature=0.7,
            max_tokens=500
        )

        summary = response.choices[0].message.content.strip()

        if not summary and retry_count < 2:  # Retry if OpenAI returns empty
            logging.warning(f"⚠️ OpenAI returned an empty summary. Retrying (Attempt {retry_count + 2})...")
            return generate_ai_summary(case_summary, retry_count + 1)

        if not summary:  # If still empty after retries, return a fallback summary
            logging.error("❌ OpenAI failed to generate a summary after retries.")
            return "AI Summary Not Available. This case may require manual review."

        redis_client.setex(cache_key, 86400, summary)  # Cache for 24 hours
        return summary

    except Exception as e:
        logging.error(f"❌ OpenAI API Error: {str(e)}")
        return "AI Analysis unavailable due to an API error."

# Case law search endpoint (with filtering & sorting)
@app.get("/search")
@limiter.limit("10/minute")
async def search_case_law(request: Request, query: str, court: str = None, sort: str = "relevance"):
    """Handles search requests with filtering, sorting, and AI summaries."""
    raw_data = fetch_case_law(query)

    if "error" in raw_data:
        return JSONResponse(content={"message": "Failed to fetch case law", "results": []}, status_code=500)

    results = raw_data.get("results", [])

    # Apply Court Filtering
    if court:
        results = [case for case in results if case.get("court", "").lower() == court.lower()]

    # Apply Sorting
    if sort == "date_desc":
        results.sort(key=lambda x: x.get("dateFiled", "0000-00-00"), reverse=True)
    elif sort == "date_asc":
        results.sort(key=lambda x: x.get("dateFiled", "9999-99-99"))

    # Generate AI Summaries (Only if a case summary exists)
    formatted_results = []
    for case in results:
        formatted_results.append({
            "Case Name": case.get("caseName") or "Unknown Case",
            "Citation": case.get("citation") or "No Citation Available",
            "Court": case.get("court") or "Unknown Court",
            "Date Decided": case.get("dateFiled") or "No Date Available",
            "Summary": case.get("summary") or "No Summary Available",
            "AI Summary": generate_ai_summary(case.get("summary", "")) if case.get("summary") else "AI Summary Not Available",
            "Full Case": case.get("absolute_url") or "#"
        })

    return JSONResponse(content={"message": f"{len(formatted_results)} case(s) found", "results": formatted_results})

@app.delete("/clear-cache")
async def clear_cache():
    """Clears Redis cache (AI summaries & search results)."""
    redis_client.flushall()
    return {"message": "✅ Redis cache cleared successfully!"}

# Start FastAPI with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)