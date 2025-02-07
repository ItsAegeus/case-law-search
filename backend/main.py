import openai
import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

# Initialize FastAPI app
app = FastAPI()

# Load OpenAI API Key from Environment Variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Validate API Key
if not OPENAI_API_KEY:
    raise ValueError("❌ OpenAI API Key is missing! Set it in Railway environment variables.")

openai.api_key = OPENAI_API_KEY  # ✅ Ensure API key is set

# Logging setup
logging.basicConfig(level=logging.INFO)

# API Model
class QueryRequest(BaseModel):
    query: str

# Function to fetch case law from CourtListener
def fetch_case_law(query: str):
    url = f"https://www.courtlistener.com/api/rest/v4/search/?q={query}&type=o&format=json"
    response = requests.get(url)

    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch case law.")

    return response.json()

# AI Summarization Function
def generate_ai_summary(case_summary: str) -> str:
    """Uses OpenAI GPT to summarize legal cases."""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Change to "gpt-3.5-turbo" if needed
            messages=[
                {"role": "system", "content": "You are a legal AI assistant that summarizes case law."},
                {"role": "user", "content": f"Summarize this legal case in simple terms:\n\n{case_summary}"}
            ],
            temperature=0.7,
            max_tokens=150,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}  # ✅ Ensure Bearer token is included
        )

        return response["choices"][0]["message"]["content"].strip()

    except Exception as e:
        logging.error(f"❌ OpenAI API Error: {str(e)}")
        return "AI Summary unavailable due to API error."

# API Endpoint
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
        court = case.get("court", {}).get("name", "Unknown Court")
        date = case.get("dateFiled", "No Date")
        summary = case.get("summary", "No summary available.")
        full_case_link = case.get("absolute_url", "#")

        # Generate AI Summary
        ai_summary = generate_ai_summary(summary) if summary else "No summary available."

        formatted_cases.append({
            "Case Name": case_name,
            "Citation": citation,
            "Court": court,
            "Date Decided": date,
            "Summary": summary,
            "AI Summary": ai_summary,
            "Full Case": f"https://www.courtlistener.com{full_case_link}"
        })

    return {"message": f"{len(formatted_cases)} case(s) found for query: {query}", "results": formatted_cases}

# Run app with Uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)