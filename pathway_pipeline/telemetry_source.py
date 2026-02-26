"""
telemetry_source.py
Generates synthetic real-time telemetry for all solar plants.
Uses simulated daytime hours so generation is always visible during demo.
"""

import json, math, os, random, threading, time
from datetime import datetime, timezone
from pathway_pipeline.config import PLANTS, TELEMETRY_EMIT_INTERVAL_SEC, DATA_DIR

# ── DEMO MODE: simulate time at peak solar hours so generation is always visible
# Real hour cycles from 10am to 3pm repeatedly, making the demo always show
# active solar generation regardless of what time you actually run the demo.
_DEMO_START_HOUR = 10.0   # start at 10am solar time
_DEMO_HOUR_SPEED = 0.01   # how fast simulated time advances (slow = stable demo)
_PIPELINE_START  = time.time()

def _simulated_solar_hour() -> float:
    """Returns a simulated hour between 10 and 15 (peak solar window)."""
    elapsed_minutes = (time.time() - _PIPELINE_START) / 60.0
    hour = _DEMO_START_HOUR + (elapsed_minutes * _DEMO_HOUR_SPEED)
    # cycle between 10 and 15
    return 10.0 + (hour % 5.0)


def _load_injected_events() -> dict:
    event_file = os.path.join(DATA_DIR, "injected_events.json")
    if os.path.exists(event_file):
        try:
            with open(event_file) as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _ghi_from_hour(hour: float, cloud_fraction: float) -> float:
    """GHI in W/m² based on hour of day and cloud cover."""
    if hour < 6 or hour > 18:
        return 0.0
    solar_angle  = math.pi * (hour - 6) / 12
    base_ghi     = 1000 * math.sin(solar_angle)
    cloud_factor = 1.0 - (0.8 * cloud_fraction)
    return max(0, base_ghi * cloud_factor * random.uniform(0.95, 1.05))


def _simulate_plant(plant: dict, events: dict) -> dict:
    hour       = _simulated_solar_hour()
    base_cloud = {"RJ01": 0.15, "GJ01": 0.25, "TN01": 0.30}.get(plant["id"], 0.2)

    event = events.get(plant["id"], {})
    if event.get("type") == "cloud":
        extra      = {"low": 0.3, "medium": 0.5, "high": 0.75}.get(event.get("severity", "medium"), 0.5)
        base_cloud = min(1.0, base_cloud + extra)

    cloud_fraction      = min(1.0, base_cloud + random.uniform(-0.05, 0.05))
    ghi                 = _ghi_from_hour(hour, cloud_fraction)
    panel_area_m2       = plant["capacity_mw"] * 5000
    panel_efficiency    = 0.20
    inverter_efficiency = event.get("inverter_efficiency", 0.973)

    if event.get("type") == "inverter_fault":
        inverter_efficiency = random.uniform(0.88, 0.92)

    dc_power_mw = (ghi * panel_area_m2 * panel_efficiency) / 1_000_000
    ac_power_mw = max(0.0, min(dc_power_mw * inverter_efficiency, plant["capacity_mw"]))

    now = datetime.now(timezone.utc)
    return {
        "plant_id":            plant["id"],
        "plant_name":          plant["name"],
        "state":               plant["state"],
        "timestamp":           now.isoformat(),
        "unix_ts":             now.timestamp(),
        "simulated_hour":      round(hour, 2),
        "cloud_fraction":      round(cloud_fraction, 3),
        "ghi_wm2":             round(ghi, 2),
        "ac_power_mw":         round(ac_power_mw, 3),
        "inverter_efficiency": round(inverter_efficiency, 4),
        "capacity_mw":         plant["capacity_mw"],
        "injected_event":      event.get("type", "none"),
    }


def emit_telemetry_forever(output_file: str):
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    while True:
        events = _load_injected_events()
        for plant in PLANTS:
            row = _simulate_plant(plant, events)
            with open(output_file, "a") as f:
                f.write(json.dumps(row) + "\n")
        time.sleep(TELEMETRY_EMIT_INTERVAL_SEC)
