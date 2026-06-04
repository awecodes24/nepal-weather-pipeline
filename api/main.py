from fastapi import FastAPI
from sqlalchemy import text

app = FastAPI()

@app.on_event("startup")
async def startup():
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            print("DB Connected")
    except Exception as e:
        print("DB Connection Failed:", e)