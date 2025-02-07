from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import requests
import logging
import json
import os
import uvicorn
import openai  # AI-powered case law analysis

# Load OpenAI API key (set in Railway environment variables)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize FastAPI app
app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
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
    """Serve the search page."""
    index_path = "static/index.html"
    if os.path.exists(index_path):
        return FileResponse(index_path)
    else:
        return JSONResponse(content={"error": "index.html not found. Please ensure it is in the 'static' folder."}, status_code=404)

@app.get("/search")
def search_case_law(query: str):
    """Search for case law based on user input and generate AI summaries."""
    
    if not query.strip():
        raise HTTPException(status_code=400, detail="Error: A query parameter is required.")

    logging.info(f"🔍 Searching case law for: {query}")

    try:
        # 🔹 Step 1: Search for cases
        response = requests.get(
            COURTLISTENER_API_URL,
            params={"q": query, "type": "o"},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        cases = []

        for result in data.get("results", []):
            case_id = result.get("id")
            case_url = f"https://www.courtlistener.com/api/rest/v4/opinions/{case_id}/"

            # 🔹 Step 2: Fetch full case details (including summary)
            try:
                case_response = requests.get(case_url, timeout=5)
                case_response.raise_for_status()
                case_details = case_response.json()
                case_summary = case_details.get("plain_text", "No summary available").strip()

                # Limit summary length for readability
                if len(case_summary) > 500:
                    case_summary = case_summary[:500] + "..."

            except requests.exceptions.RequestException:
                case_summary = "No summary available"

            # ✅ Fix: Ensure 'court' is a dictionary before calling .get()
            court_info = result.get("court", "Unknown Court")
            if isinstance(court_info, str):  
                court_name = "Unknown Court"
            else:
                court_name = court_info.get("name", "Unknown Court")

            # 🔹 Step 3: AI-generated analysis
            ai_analysis = generate_ai_summary(case_summary)

            cases.append({
                "📌 Case Name": result.get("caseName", "Unknown"),
                "📜 Citation": result.get("citation", "No citation available"),
                "⚖️ Court": court_name,
                "📅 Date Decided": result.get("dateFiled", "Unknown Date"),
                "📄 Summary": case_summary,  # ✅ Now includes the full case summary
                "💡 AI Analysis": ai_analysis,  # ✅ AI-generated legal insight
                "🔗 Full Case": f"https://www.courtlistener.com/opinion/{case_id}/"
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

def generate_ai_summary(case_summary: str) -> str:
    """Uses OpenAI GPT to summarize and analyze the case law."""
    if not OPENAI_API_KEY:
        return "AI Analysis not available (missing API key)."

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a legal AI assistant that summarizes and explains case law."},
                {"role": "user", "content": f"Summarize this legal case and explain its significance in simple terms:\n\n{case_summary}"}
            ],
            temperature=0.7,
            max_tokens=150
        )

        ai_summary = response["choices"][0]["message"]["content"]
        return ai_summary.strip()

    except Exception as e:
        logging.error(f"❌ OpenAI API Error: {str(e)}")
        return "AI Analysis unavailable due to an API error."

# ✅ Ensure FastAPI runs on Railway-compatible settings
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)