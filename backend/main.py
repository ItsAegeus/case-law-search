from fastapi import FastAPI, Query, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, Text, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import requests
import os
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Get database URL from Railway environment variables
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")  # Default to SQLite if missing
PORT = int(os.getenv("PORT", 8000))

# SQLAlchemy Database Setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define Case Law Table
class Case(Base):
    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    case_name = Column(String, nullable=False)
    citation = Column(String, nullable=False)
    court = Column(String, nullable=False)
    jurisdiction = Column(String, nullable=False)
    date_decided = Column(Date, nullable=False)
    summary = Column(Text, nullable=False)
    full_text = Column(Text, nullable=False)

# Create the tables in the database
Base.metadata.create_all(bind=engine)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Test Route (Check if API is Running)
@app.get("/")
def home():
    return {"message": "Case Law Search API is Running"}

# Search Endpoint (Will Later Connect to CourtListener)
@app.get("/search")
def search_cases(query: str = Query(..., description="Enter a legal keyword or case name")):
    try:
        # Placeholder response - replace with CourtListener API call later
        results = [
            {"case_name": "Terry v. Ohio", "citation": "392 U.S. 1 (1968)", "summary": "Stop and frisk ruling."},
            {"case_name": "Miranda v. Arizona", "citation": "384 U.S. 436 (1966)", "summary": "Miranda rights established."}
        ]
        return {"query": query, "cases": results}
    except Exception as e:
        logger.error(f"Error during search: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Run the server (For Local Development)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
