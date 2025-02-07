from fastapi import FastAPI
import psycopg2
import requests
import os

app = FastAPI()

# Connect to PostgreSQL
def connect_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

# Fetch case law from CourtListener API
def fetch_case_law():
    API_URL = "https://www.courtlistener.com/api/rest/v3/opinions/"
    HEADERS = {"Authorization": f"Token {os.getenv('COURTLISTENER_API_TOKEN')}"}
    
    params = {
        "court": ["scotus", "ca7"],  # Supreme Court & Seventh Circuit
        "date_filed__gte": "2023-01-01",  # Cases from 2023 onward
        "order_by": "-date_filed",
        "page_size": 10  # Number of cases to fetch
    }

    response = requests.get(API_URL, headers=HEADERS, params=params)

    if response.status_code == 200:
        return response.json()["results"]
    else:
        return []

# Route to fetch and store cases in the database
@app.get("/fetch-cases/")
async def fetch_and_store_cases():
    cases = fetch_case_law()

    conn = connect_db()
    cursor = conn.cursor()

    for case in cases:
        cursor.execute("""
            INSERT INTO cases (case_name, court, jurisdiction, date_filed, citation, full_text_url, summary)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (full_text_url) DO NOTHING;
        """, (
            case["case_name"], case["court"], "Federal",
            case["date_filed"], case.get("citation", ""),
            case["absolute_url"], case.get("plain_text", "")
        ))

    conn.commit()
    cursor.close()
    conn.close()

    return {"message": f"Stored {len(cases)} cases in the database."}
