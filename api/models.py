from sqlalchemy import (
    Integer, Float, String, DateTime,
    UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from .database import Base

class WeatherReading(Base):
    __tablename__ = "weather_readings"

    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    city : Mapped[str] = mapped_column(String(100), nullable=False)
    country : Mapped[str] = mapped_column(String(10), default="NP")
    timestamp : Mapped[datetime] = mapped_column(DateTime, nullable=False)
    temp_c : Mapped[float] = mapped_column(Float)
    feels_like : Mapped[float] = mapped_column(Float)
    temp_min : Mapped[float] = mapped_column(Float)
    temp_max : Mapped[float] = mapped_column(Float)
    humidity : Mapped[int] = mapped_column(Integer)
    pressure : Mapped[int] = mapped_column(Integer)
    wind_speed : Mapped[float] = mapped_column(Float)
    rain_1h : Mapped[float] = mapped_column(Float, default=0.0)
    clouds : Mapped[int] = mapped_column(Integer)
    description : Mapped[str] = mapped_column(String(100))

    __table_args__ = (
        # Prevent duplicate readings
        UniqueConstraint("city", "timestamp", name="uq_city_ts"),
        # Speed up time-range queries
        Index("ix_city_timestamp", "city", "timestamp"),
        # Speed up city-only queries
        Index("ix_city", "city"),
    )
    
    
class ForecastReading(Base):
    __tablename__ = "forecast_readings"

    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    city : Mapped[str] = mapped_column(String(100), nullable=False)
    forecast_for : Mapped[datetime] = mapped_column(DateTime, nullable=False)
    fetched_at : Mapped[datetime] = mapped_column(DateTime, default=datetime.now(datetime.timezone.utc))
    temp_c : Mapped[float] = mapped_column(Float)
    temp_min : Mapped[float] = mapped_column(Float)
    temp_max : Mapped[float] = mapped_column(Float)
    humidity : Mapped[int] = mapped_column(Integer)
    rain_3h : Mapped[float] = mapped_column(Float, default=0.0)
    description : Mapped[str] = mapped_column(String(100))
    wind_speed : Mapped[float] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint("city", "forecast_for", name="uq_forecast"),
        Index("ix_forecast_city_ts", "city", "forecast_for"),
    )   