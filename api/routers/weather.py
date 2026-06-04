from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta
from typing import Annotated
from ..database import get_db
from ..models import WeatherReading, ForecastReading
from ..schemas import WeatherReadingOut, CityStats, ForecastOut
from ..fetcher import scrape_all

router = APIRouter(prefix="/weather", tags=["weather"])

CITIES = ["Dharan", "Kathmandu", "Pokkhara", "Biratnagar", "Butwal"]

@router.get("/latest", response_model=list[WeatherReadingOut])
async def get_latest(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Latest reading for each city - used by dashboard header cards.
    Uses a subquery to get the most recent timestamp per city.
    """
    subq = (
        select(
            WeatherReading.city,
        func.max(WeatherReading.timestamp).label("max_ts")
        )
        .group_by(WeatherReading.city)
        .subquery()
    )
    result = await db.execute(
        select(WeatherReading).join(
            subq,
            (WeatherReading.city == subq.c.city) & 
            (WeatherReading.timestamp == subq.c.max_ts)
        )
    )
    return result.scalars().all()

@router.get("/history", response_model=list[WeatherReadingOut])
async def get_history(
    city: str = Query(..., description="City name"),
    days: int = Query(7, ge=1, le=90, description="Days of history"),
    db : Annotated[AsyncSession, Depends(get_db)] = None,
):
    """Time-series readings for one city over N days."""
    since = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(WeatherReading)
        .where(
            WeatherReading.city == city, 
            WeatherReading.timestamp >= since,
        )
        .order_by(WeatherReading.timestamp)
    )
    readings = result.scalars().all()
    if not readings:
        raise HTTPException(
            404, f"No data found for {city} in last {days} days"
        )
    return readings

@router.get("/stats", response_model=list[CityStats])
async def get_stats(
    days: int = Query(7, ge=1, le=90),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """Aggregate stats per city - used by comparison charts."""
    since = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(
            WeatherReading.city,
            func.avg(WeatherReading.temp_c).label("avg_temp"),
            func.max(WeatherReading.temp_c).label("max_temp"),
            func.min(WeatherReading.temp_c).label("min_temp"),
            func.avg(WeatherReading.humidity).label("avg_humidity"),
            func.sum(WeatherReading.rain_1h).label("total_rain"),
            func.count(WeatherReading.id).label("reading_count"),
        )
        .where(WeatherReading.timestamp >= since)
        .group_by(WeatherReading.city)
        .order_by(WeatherReading.city)
    )
    rows = result.mappings().all()
    return [CityStats(**dict(r)) for r in rows]

@router.get("/cities", response_model=list[str])
async def get_cities(
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """List all cities with data in the database."""
    result = await db.execute(
        select(WeatherReading.city).distinct()
    )
    return [row[0] for row in result.all()]

@router.get("/scrape", response_model=dict)
async def trigger_scrape():
    """
    Manually trigger a scrape - useful for testing.
    The schedular also calls this every hour automatically.
    """
    result = await scrape_all()
    return result

@router.get("/forecast", response_model=list[ForecastOut])
async def get_forecast(
    city: str = Query(..., description="City name"),
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    """Get forecast readings for a specific city (case-insensitive)."""
    result = await db.execute(
        select(ForecastReading)
        .where(ForecastReading.city.ilike(city))
        .order_by(ForecastReading.forecast_for)
    )
    forecasts = result.scalars().all()
    if not forecasts:
        raise HTTPException(
            404, f"No forecast found for {city}. Use /weather/cities to see available cities."
        )
    return forecasts