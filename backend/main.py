from fastapi import FastAPI
import psycopg2
import os

app = FastAPI()

def connect_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"))

@app.get("/")
async def home():
    return {"message": "Case Law API is running!"}

@app.get("/search/")
async def search_case(scenario: str):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT case_name, summary, full_text_url FROM cases WHERE summary ILIKE %s LIMIT 5", (f"%{scenario}%",))
    cases = cursor.fetchall()
    cursor.close()
    conn.close()
    return [{"case_name": c[0], "summary": c[1], "link": c[2]} for c in cases]
