import asyncio
import httpx    # async HTTP client — replaces requests
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from .database import AsyncSessionLocal, settings
from .models import WeatherReading, ForecastReading

BASE_URL = "https://api.openweathermap.org/data/2.5"
CITIES   = [
    "Dharan,NP", "Kathmandu,NP", "Pokhara,NP",
    "Biratnagar,NP", "Butwal,NP",
]

async def fetch_city(client: httpx.AsyncClient,
                     city: str) -> dict | None:
    """Async HTTP GET - non-blocking, releases thread while waiting."""
    try:
        resp = await client.get(
            f"{BASE_URL}/weather",
            params={"q": city, "appid": settings.API_KEY,
                    "units": "metric"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        print(f"[ERROR] {city}: {e}")
        return None
    
async def fetch_forecast(client: httpx.AsyncClient,
                         city: str) -> dict | None:
    try:
        resp = await client.get(
            f"{BASE_URL}/forecast",
            params={"q": city, "appid": settings.API_KEY,
                    "units": "metric"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        print(f"[ERROR] forecast {city}: {e}")
        return None

async def scrape_all() -> dict:
    """
    Fetch all cities CONCURRENTLY using asyncio.gather.
    Old version: fetched cities one-by-one (sequential).
    New version: fetches all 5 cities at the same time.
    5 sequential HTTP calls: ~5 seconds.
    5 concurrent HTTP calls: ~1 second.
    """
    saved, errors = 0, []

    async with httpx.AsyncClient() as client:
        # Fire all 5 weather requests at the same time
        weather_tasks = [fetch_city(client, c) for c in CITIES]
        weather_results = await asyncio.gather(*weather_tasks, return_exceptions=True)
        
        # Fire all 5 forecast requests at the same time
        forecast_tasks = [fetch_forecast(client, c) for c in CITIES]
        forecast_results = await asyncio.gather(*forecast_tasks, return_exceptions=True)

    async with AsyncSessionLocal() as session:
        # Save weather data
        for city, raw in zip(CITIES, weather_results):
            if isinstance(raw, Exception) or raw is None:
                errors.append(str(city))
                continue
            try:
                rain = raw.get("rain", {}).get("1h", 0.0)
                reading = WeatherReading(
                    city = raw["name"],
                    country = raw["sys"]["country"],
                     timestamp   = datetime.utcfromtimestamp(
                                      raw["dt"]),
                    temp_c      = raw["main"]["temp"],
                    feels_like  = raw["main"]["feels_like"],
                    temp_min    = raw["main"]["temp_min"],
                    temp_max    = raw["main"]["temp_max"],
                    humidity    = raw["main"]["humidity"],
                    pressure    = raw["main"]["pressure"],
                    wind_speed  = raw["wind"]["speed"],
                    rain_1h     = rain,
                    clouds      = raw["clouds"]["all"],
                    description = raw["weather"][0]["description"],
                )
                session.add(reading)
                await session.flush()
                saved += 1
                print(f"   {reading.city}: "
                      f"{reading.temp_c}°C, "
                      f"{reading.humidity}%")
            except IntegrityError:
                await session.rollback()
                print(f"   Duplicate skipped: {city}")
            except Exception as e:
                errors.append(f"{city}: {e}")

        # Save forecast data
        for city, raw in zip(CITIES, forecast_results):
            if isinstance(raw, Exception) or raw is None:
                continue
            try:
                # Use city name from API response to match weather data
                city_name = raw["city"]["name"]
                for forecast_item in raw.get("list", []):
                    rain = forecast_item.get("rain", {}).get("3h", 0.0)
                    forecast = ForecastReading(
                        city = city_name,
                        forecast_for = datetime.utcfromtimestamp(forecast_item["dt"]),
                        fetched_at = datetime.utcnow(),
                        temp_c = forecast_item["main"]["temp"],
                        temp_min = forecast_item["main"]["temp_min"],
                        temp_max = forecast_item["main"]["temp_max"],
                        humidity = forecast_item["main"]["humidity"],
                        rain_3h = rain,
                        description = forecast_item["weather"][0]["description"],
                        wind_speed = forecast_item["wind"]["speed"],
                    )
                    session.add(forecast)
                await session.flush()
                print(f"   {city_name}: saved {len(raw.get('list', []))} forecast items")
            except IntegrityError:
                await session.rollback()
                print(f"   Forecast duplicates skipped: {city}")
            except Exception as e:
                await session.rollback()
                errors.append(f"Forecast {city}: {e}")
                print(f"[ERROR] Forecast {city}: {e}")

        await session.commit()
    print(f"Scrape done: {saved} saved, {len(errors)} errors")
    return {"saved": saved, "errors": errors}