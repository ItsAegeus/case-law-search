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
    logging.warning("⚠️ Missing OPENAI_API_KEY! AI summaries will not work.")

# Initialize Redis client
try:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()  # Test Redis connection
    logging.info("✅ Connected to Redis!")
except redis.exceptions.ConnectionError:
    logging.error("❌ Could not connect to Redis. Check REDIS_URL.")
    redis_client = None  # Prevents crashes if Redis isn't working

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

# Function to fetch case law from CourtListener API
def fetch_case_law(query: str):
    """Fetches case law data from CourtListener API with Redis caching and logs data."""
    cache_key = f"case_law:{query}"
    
    # Check Redis cache
    if redis_client:
        cached_data = redis_client.get(cache_key)
        if cached_data:
            logging.info(f"✅ Cache HIT for: {query}")
            return json.loads(cached_data)

    logging.info(f"❌ Cache MISS for: {query}. Fetching from API...")

    url = f"https://www.courtlistener.com/api/rest/v4/search/?q={query}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()

        if "results" in data and data["results"]:
            logging.info(f"📜 First Case Data: {json.dumps(data['results'][0], indent=2)}")

        # Store in Redis cache (if available)
        if redis_client:
            redis_client.setex(cache_key, 600, json.dumps(data))

        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ API Error: {str(e)}")
        return {"error": "Failed to fetch case law data"}

# Function to generate AI summaries using full case text from CourtListener API
def generate_ai_summary(case):
    """Generates AI summaries by extracting full case text from CourtListener API."""

    if not OPENAI_API_KEY:
        logging.error("❌ Missing OpenAI API Key. AI summaries won't work.")
        return "AI Analysis not available (missing API key)."

    if not isinstance(case, dict):
        logging.error(f"❌ AI Summary Error: Expected dictionary but got {type(case)}")
        return "AI Summary Not Available (Invalid Case Data)."

    case_summary = case.get("summary", "").strip()

    # Try extracting `id` from opinions if missing
    opinion_id = case.get("id")

    if not opinion_id and "opinions" in case:
        opinions = case["opinions"]
        if isinstance(opinions, list) and opinions:
            opinion_id = opinions[0].get("id")  # Get the first opinion ID if available

    # Fallback to `cluster_id`
    if not opinion_id:
        cluster_id = case.get("cluster_id")
        if cluster_id:
            logging.warning(f"⚠️ No opinion ID found. Using cluster_id: {cluster_id}")
            opinion_id = cluster_id

    if not opinion_id:
        logging.error("⚠️ AI Summary Skipped: No valid opinion ID found.")
        return "AI Summary Not Available (No opinion ID)."

    # Fetch full case text from API
    api_url = f"https://www.courtlistener.com/api/rest/v4/opinions/{opinion_id}/"
    logging.info(f"📥 Fetching full case text from API: {api_url}")

    try:
        response = requests.get(api_url)
        response.raise_for_status()
        opinion_data = response.json()

        case_summary = opinion_data.get("plain_text", "").strip()

        if not case_summary:
            logging.warning("⚠️ API returned empty plain_text field.")
            return "AI Summary Not Available (No case text found)."

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Failed to fetch full case text from API: {str(e)}")
        return "AI Summary Not Available (Failed to fetch full case text)."

    if not case_summary.strip():
        logging.warning("⚠️ No usable case summary or text found.")
        return "AI Summary Not Available."

    cache_key = f"ai_summary:{hash(case_summary)}"
    cached_summary = redis_client.get(cache_key)

    if cached_summary:
        logging.info("✅ Cache HIT for AI Summary")
        return cached_summary

    logging.info("❌ Cache MISS for AI Summary. Sending request to OpenAI.")

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

        if not summary:
            logging.error("❌ OpenAI failed to generate a summary.")
            return "AI Summary Not Available."

        redis_client.setex(cache_key, 86400, summary)  # Cache for 24 hours
        return summary

    except Exception as e:
        logging.error(f"❌ OpenAI API Error: {str(e)}")
        return "AI Analysis unavailable due to an API error."

# FastAPI search endpoint
@app.get("/search")
async def search_case_law(request: Request, query: str):
    """Handles search requests with AI summaries using full case text if needed."""
    raw_data = fetch_case_law(query)

    if "error" in raw_data:
        logging.error(f"❌ API Fetch Error: {raw_data}")
        return JSONResponse(content={"message": "Failed to fetch case law", "results": []}, status_code=500)

    results = raw_data.get("results", [])

    formatted_results = []
    for index, case in enumerate(results):
        try:
            citation = case.get("citation", [])
            formatted_results.append({
                "Case Name": case.get("caseName", "Unknown Case"),
                "Citation": citation[0] if isinstance(citation, list) and citation else "No Citation Available",
                "AI Summary": generate_ai_summary(case),
            })

        except Exception as e:
            logging.error(f"❌ Error Processing Case [{index}]: {str(e)}")


    return JSONResponse(content={"message": f"{len(formatted_results)} case(s) found", "results": formatted_results})
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    