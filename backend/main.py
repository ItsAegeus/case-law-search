import os
import logging
import requests
from fastapi import FastAPI
from openai import OpenAI
from fastapi.responses import JSONResponse
from typing import Optional

# Initialize FastAPI
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)

# OpenAI API Key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Base URL for CourtListener API
COURTLISTENER_API_URL = "https://www.courtlistener.com/api/rest/v4/search/?q={}&type=o&order_by=dateFiled%20desc"

# OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def fetch_case_law(query: str):
    """Fetch case law from CourtListener API."""
    try:
        response = requests.get(COURTLISTENER_API_URL.format(query))
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"❌ Failed to fetch case data: {str(e)}")
        return {"error": "Failed to fetch case data"}


def generate_ai_summary(case_summary: str) -> str:
    """Uses OpenAI GPT to summarize and analyze the case law."""
    if not client:
        return "AI Analysis not available (missing API key)."

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a legal AI assistant that summarizes case law."},
                {"role": "user", "content": f"Summarize this legal case and explain its significance:\n\n{case_summary}"}
            ],
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"❌ OpenAI API Error: {str(e)}")
        return "AI Analysis unavailable due to an API error."


@app.get("/search")
def search_case_law(query: str):
    logging.info(f"🔍 Searching case law for: {query}")

    # Fetch raw case data
    case_data = fetch_case_law(query)
    results = case_data.get("results", [])

    if not results:
        return {"message": f"No cases found for query: {query}"}

    # Process case results
    formatted_cases = []
    for case in results[:5]:  # Limit to 5 results for readability
        case_name = case.get("caseName", "Unknown Case")
        citation = case.get("citation", "No Citation")

        # ✅ Ensure "court" is properly checked before accessing "name"
        court_info = case.get("court", {})
        court = court_info["name"] if isinstance(court_info, dict) else "Unknown Court"

        date = case.get("dateFiled", "No Date Available")
        summary = case.get("summary", "No summary available.")
        full_case_link = case.get("absolute_url", "#")

        # Generate AI Summary
        ai_summary = generate_ai_summary(summary) if summary and summary != "No summary available." else "AI Summary not available."

        formatted_cases.append({
            "Case Name": case_name or "Unknown Case",
            "Citation": citation or "No Citation",
            "Court": court or "Unknown Court",
            "Date Decided": date or "No Date Available",
            "Summary": summary or "No summary available.",
            "AI Summary": ai_summary or "AI Summary not available.",
            "Full Case": f"https://www.courtlistener.com{full_case_link}" if full_case_link != "#" else "No link available."
        })

    return {"message": f"{len(formatted_cases)} case(s) found for query: {query}", "results": formatted_cases}

# Run the FastAPI app with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)