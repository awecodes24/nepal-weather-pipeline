from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .database import engine, Base
from .routers import weather
from .fetcher import scrape_all

scheduler = AsyncIOScheduler(timezone="Asia/Kathmandu")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup and shutdown.
    Creates DB tables, starts scheduler, scrapes immediately.
    Lifespan replaces the old @app.on_event("startup") pattern.
    """
    
    # Create tables if they don't exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Scrape once immediately at startup
    await scrape_all()

    # Then every hour (Nepal timezone)
    scheduler.add_job(scrape_all, "interval", hours=1,
                      id="weather_scraper")
    scheduler.start()
    print("Scheduler started - scraping every hour.")
    
    yield # app runs here
    
    # Shutdown
    scheduler.shutdown()
    await engine.dispose()

app = FastAPI(
    title= "Nepal Weather API",
    description= "Real-time weather data for Nepali cities",
    version="2.0.0",
    lifespan=lifespan,
)
    
app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["http://localhost:8501"],  # Streamlit
    allow_methods  = ["*"],
    allow_headers  = ["*"],
)

app.include_router(weather.router)

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


