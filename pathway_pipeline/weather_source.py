"""
weather_source.py
Polls OpenWeatherMap for each plant's weather every N seconds.
Falls back to synthetic data if no API key is set.
"""

import json, os, random, time
from datetime import datetime, timezone

import requests

from pathway_pipeline.config import PLANTS, WEATHER_POLL_INTERVAL_SEC, DATA_DIR

OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
OPENWEATHER_URL     = "https://api.openweathermap.org/data/2.5/weather"


def _synthetic_weather(plant: dict) -> dict:
    base_cloud = {"RJ01": 0.15, "GJ01": 0.25, "TN01": 0.30}.get(plant["id"], 0.2)
    return {
        "plant_id":          plant["id"],
        "source":            "synthetic",
        "timestamp":         datetime.now(timezone.utc).isoformat(),
        "cloud_fraction":    round(base_cloud + random.uniform(-0.05, 0.05), 3),
        "temp_c":            round(28 + random.uniform(-3, 5), 1),
        "wind_ms":           round(random.uniform(2, 8), 2),
        "weather_condition": "Clear" if base_cloud < 0.3 else "Clouds",
    }


def _fetch_weather(plant: dict) -> dict:
    if not OPENWEATHER_API_KEY or "your-" in OPENWEATHER_API_KEY:
        return _synthetic_weather(plant)
    try:
        resp = requests.get(OPENWEATHER_URL, params={
            "lat": plant["lat"], "lon": plant["lon"],
            "appid": OPENWEATHER_API_KEY, "units": "metric",
        }, timeout=10)
        resp.raise_for_status()
        d = resp.json()
        return {
            "plant_id":          plant["id"],
            "source":            "openweathermap",
            "timestamp":         datetime.now(timezone.utc).isoformat(),
            "cloud_fraction":    d.get("clouds", {}).get("all", 0) / 100.0,
            "temp_c":            d.get("main", {}).get("temp", 25),
            "wind_ms":           d.get("wind", {}).get("speed", 0),
            "weather_condition": d.get("weather", [{}])[0].get("main", "Clear"),
        }
    except Exception as e:
        print(f"[WeatherSource] Error for {plant['id']}: {e} — using synthetic")
        return _synthetic_weather(plant)


def emit_weather_forever(output_file: str):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    while True:
        for plant in PLANTS:
            row = _fetch_weather(plant)
            with open(output_file, "a") as f:
                f.write(json.dumps(row) + "\n")
        time.sleep(WEATHER_POLL_INTERVAL_SEC)
