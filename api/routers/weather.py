from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta
from typing import Annotated
from ..database import get_db
from ..models import WeatherReading
from ..schemas import WeatherReadingOut, CityStats
from ..fetcher import scrape_all

router = APIRouter(prefix="/weather", tags=["weather"])

CITIES = ["Dharan", "Kathmandu", "Pokkhara", "Biratnagar", "Butwal"]

@router.get("/latest", response_model=list[WeatherReadingOut])
async def get_latest(db: Annotated[AsyncSession, Depends(get_db)]):
    """
    Latest reading for each city - used by dashboard header cards.
    Uses a subquery to get the most recent timestamp per city.
    """
    
    