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

# Function to fetch case law from CourtListener API
def fetch_case_law(query: str):
    """Fetches case law data from CourtListener API with Redis caching and logs data."""
    cache_key = f"case_law:{query}"
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

        # 🔹 Log first case response for debugging
        if data.get("results"):
            logging.info(f"📜 First Case Data: {json.dumps(data['results'][0], indent=2)}")

        redis_client.setex(cache_key, 600, json.dumps(data))  # Cache for 10 minutes
        return data
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ API Error: {str(e)}")
        return {"error": "Failed to fetch case law data"}

# Function to generate AI summaries using full case text from CourtListener API
def generate_ai_summary(case):
    """Generates AI summaries by correctly extracting full case text from CourtListener API."""
    
    if not OPENAI_API_KEY:
        logging.error("❌ Missing OpenAI API Key. AI summaries won't work.")
        return "AI Analysis not available (missing API key)."

    case_summary = case.get("summary", "").strip()

    # 🔹 If no summary, fetch full case text via API
    if not case_summary:
        opinion_id = case.get("id")
        if opinion_id:
            api_url = f"https://www.courtlistener.com/api/rest/v4/opinions/{opinion_id}/"
            logging.info(f"📥 Fetching full case text from API: {api_url}")
            try:
                response = requests.get(api_url)
                response.raise_for_status()
                opinion_data = response.json()

                # ✅ Extract the full case text correctly
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

    # 🔹 Log what is actually being sent to OpenAI
    logging.info(f"✅ Case Text Extracted (First 500 chars): {case_summary[:500]}...")

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

# Case law search endpoint (with AI summaries using full case text)
@app.get("/search")
@limiter.limit("10/minute")
async def search_case_law(request: Request, query: str):
    """Handles search requests with AI summaries using full case text if needed."""
    raw_data = fetch_case_law(query)

    if "error" in raw_data:
        logging.error(f"❌ API Fetch Error: {raw_data}")
        return JSONResponse(content={"message": "Failed to fetch case law", "results": []}, status_code=500)

    results = raw_data.get("results", [])

    formatted_results = []
    for case in results:
        try:
            logging.info(f"🧐 Processing Case Data: {case}")  # DEBUG LOG

            # Ensure 'case' is a dictionary before using `.get()`
            if not isinstance(case, dict):
                logging.error(f"❌ Unexpected Data Type ({type(case)}): {case}")
                continue  # Skip invalid entries

            citation = case.get("citation", [])
            formatted_results.append({
                "Case Name": case.get("caseName", "Unknown Case"),
                "Citation": citation[0] if isinstance(citation, list) and citation else "No Citation Available",
                "Court": case.get("court", {}).get("name", "Unknown Court"),
                "Date Decided": case.get("dateFiled", "No Date Available"),
                "Summary": case.get("summary", "No Summary Available"),
                "AI Summary": generate_ai_summary(case),
                "Full Case": f"https://www.courtlistener.com{case.get('absolute_url', '')}"
            })

        except Exception as e:
            logging.error(f"❌ Error Processing Case: {str(e)}")

    return JSONResponse(content={"message": f"{len(formatted_results)} case(s) found", "results": formatted_results})

# Start FastAPI with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)