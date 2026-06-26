import pytest
from httpx import AsyncClient
from datetime import datetime
from api.models import WeatherReading

@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

@pytest.mark.asyncio
async def test_get_latest_empty(client: AsyncClient):
    """Should return empty list when no data exists."""
    resp = await client.get("/weather/latest")
    assert resp.status_code == 200
    assert resp.json() == []

@pytest.mark.asyncio
async def test_get_history_not_found(client: AsyncClient):
    """Should return 404 when city has no data."""
    resp = await client.get(
        "/weather/history",
        params={"city": "Nonexistent", "days": 7}
    )
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_get_history_with_data(
    client: AsyncClient,
    db_session
):
    """Insert a reading, then verify /history returns it."""
    reading = WeatherReading(
        city        = "Dharan",
        country     = "NP",
        timestamp   = datetime.utcnow(),
        temp_c      = 28.5,
        feels_like  = 30.0,
        temp_min    = 25.0,
        temp_max    = 32.0,
        humidity    = 72,
        pressure    = 1013,
        wind_speed  = 3.2,
        rain_1h     = 0.0,
        clouds      = 45,
        description = "partly cloudy",
    )
    db_session.add(reading)
    await db_session.flush()

    resp = await client.get(
        "/weather/history",
        params={"city": "Dharan", "days": 7}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["city"] == "Dharan"
    assert data[0]["temp_c"] == pytest.approx(28.5)

@pytest.mark.asyncio
async def test_get_cities(client: AsyncClient, db_session):
    """Cities endpoint returns distinct city names."""
    for city in ["Dharan", "Kathmandu", "Dharan"]:
        db_session.add(WeatherReading(
            city="Dharan" if city == "Dharan" else "Kathmandu",
            country="NP", timestamp=datetime.utcnow(),
            temp_c=25.0, feels_like=26.0, temp_min=22.0,
            temp_max=28.0, humidity=70, pressure=1012,
            wind_speed=2.5, rain_1h=0.0, clouds=30,
            description="clear",
        ))
    await db_session.flush()

    resp = await client.get("/weather/cities")
    assert resp.status_code == 200
    cities = resp.json()
    assert "Dharan" in cities
    assert len(set(cities)) == len(cities)  # no duplicates