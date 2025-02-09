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
import httpx

async def fetch_case_law(query: str):
    """Use async requests for faster API calls."""
    cache_key = f"case_law:{query}"
    cached_data = await redis.get(cache_key)
    
    if cached_data:
        return json.loads(cached_data)

    url = f"https://www.courtlistener.com/api/rest/v4/search/?q={query}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        if response.status_code == 200:
            case_data = response.json()
            await redis.set(cache_key, json.dumps(case_data), ex=3600)
            return case_data

    return {"error": "Failed to fetch case law data"}


# Function to generate AI summary using OpenAI API
async def generate_ai_summary(case_summary: str):
    """Check Redis cache before making OpenAI API call."""
    cache_key = f"ai_summary:{hash(case_summary)}"
    cached_summary = await redis.get(cache_key)
    
    if cached_summary:
        return cached_summary  # Return cached AI summary

    if not OPENAI_API_KEY:
        return "AI Analysis not available (missing API key)."

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a legal AI assistant."},
                {"role": "user", "content": f"Summarize this case:\n{case_summary}"}
            ],
            temperature=0.7,
            max_tokens=200
        )
        ai_summary = response.choices[0].message.content.strip()

        # Cache AI summary for 24 hours
        await redis.set(cache_key, ai_summary, ex=86400)  
        return ai_summary

    except Exception as e:
        logging.error(f"OpenAI API Error: {str(e)}")
        return "AI Analysis unavailable due to an API error."

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