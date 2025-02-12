from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import requests
import os
import openai
import logging
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ✅ Logging Setup
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ Load Environment Variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

# ✅ Initialize FastAPI App
app = FastAPI()

# ✅ Serve Static Files (Frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ Serve `index.html` for frontend UI
@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

# ✅ Database Setup
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ✅ Define Case Law Database Model
class CaseLaw(Base):
    __tablename__ = "case_law"

    id = Column(Integer, primary_key=True, index=True)
    query = Column(String, index=True)
    case_name = Column(String, nullable=False)
    citation = Column(String, nullable=True)
    court = Column(String, nullable=True)
    date_decided = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    full_case_url = Column(String, nullable=True)

# ✅ Create Database Tables
Base.metadata.create_all(bind=engine)

# ✅ Database Dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ Fetch Case Law from CourtListener API
def fetch_case_law(query: str):
    """Fetches case law from CourtListener API."""
    url = f"https://www.courtlistener.com/api/rest/v4/search/?q={query}&type=o"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Error fetching case law: {str(e)}")
        return {"error": "Failed to fetch case law data"}

# ✅ OpenAI AI Summarization Function
def generate_ai_summary(case_summary: str) -> str:
    """Uses OpenAI GPT to summarize and analyze case law."""
    if not OPENAI_API_KEY:
        return "AI Analysis not available (missing API key)."

    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)  

        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a legal AI assistant that summarizes and explains case law."},
                {"role": "user", "content": f"Summarize this legal case in simple terms and explain its significance:\n\n{case_summary}"}
            ],
            temperature=0.7,
            max_tokens=200,
            request_timeout=5  # ✅ Prevents long response times
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logging.error(f"❌ OpenAI API Error: {str(e)}")
        return "AI Analysis unavailable due to an API error."

# ✅ Search Case Law (Only Returns Summarizable Cases)
@app.get("/search")
async def search_case_law(query: str, db: Session = Depends(get_db)):
    """Searches case law and returns only cases that can be summarized."""

    # ✅ Fetch Data from CourtListener API
    raw_data = fetch_case_law(query)

    if "error" in raw_data:
        return JSONResponse(content={"message": "Failed to fetch case law", "results": []}, status_code=500)

    results = []
    for case in raw_data.get("results", []):
        summary_text = case.get("summary", "").strip()

        # ✅ Ignore cases without valid summaries
        if not summary_text or summary_text.lower() in ["no summary available", ""]:
            continue  # Skips cases that cannot be summarized

        # ✅ Generate AI Summary
        ai_summary = generate_ai_summary(summary_text)

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

        # ✅ Store in Database for Future Queries
        new_case = CaseLaw(
            query=query,
            case_name=case_data["Case Name"],
            citation=case_data["Citation"],
            court=case_data["Court"],
            date_decided=case_data["Date Decided"],
            summary=case_data["Summary"],
            full_case_url=case_data["Full Case"]
        )
        db.add(new_case)

    db.commit()

    return {"message": f"{len(results)} case(s) found for query: {query}", "results": results}

# ✅ Ensure Uvicorn Starts on Railway Deployment
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)