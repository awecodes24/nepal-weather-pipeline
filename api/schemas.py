from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class WeatherReadingOut(BaseModel):
    id:          int
    city:        str
    timestamp:   datetime
    temp_c:      float
    feels_like:  float
    humidity:    int
    pressure:    int
    wind_speed:  float
    rain_1h:     float
    clouds:      int
    description: str

    model_config = {"from_attributes": True}

class ForecastOut(BaseModel):
    city:         str
    forecast_for: datetime
    temp_c:       float
    temp_min:     float
    temp_max:     float
    humidity:     int
    rain_3h:      float
    description:  str
    wind_speed:   float

    model_config = {"from_attributes": True}

class CityStats(BaseModel):
    city:        str
    avg_temp:    float
    max_temp:    float
    min_temp:    float
    avg_humidity:float
    total_rain:  float
    reading_count: int

class ScrapeResult(BaseModel):
    cities_scraped: int
    readings_saved: int
    errors:         list[str] = []