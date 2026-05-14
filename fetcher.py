# Fetch from API

import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

BASE_PATH = Path(__file__).resolve().parent.parent
DOTENV_PATH = BASE_PATH / '.env'

load_dotenv(DOTENV_PATH)

API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise ValueError("API_KEY not found in environment variables")


def fetch_weather(city: str) -> dict:
    """Fetch weather data for a given city"""
    
    uri = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

    try:
        response = requests.get(uri, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return {
            "city": data["name"],
            "temparature": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "weather": data["weather"][0]["description"],
        }
    
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Weather API requestion failed: {e}") from e


if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else "Dharan"
    weather = fetch_weather(city)
    print(weather)