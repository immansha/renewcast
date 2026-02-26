"""
rl_dispatch.py
Dispatch decision agent. Selects backup assets based on forecast uncertainty.
Mirrors the behaviour of a frozen pre-trained RL policy.
"""

import json, os
from datetime import datetime, timezone, timedelta
from pathway_pipeline.config import PLANT_MAP, DATA_DIR

BACKUP_ASSETS = {
    "RJ01": [
        {"id": "Suratgarh_Gas",  "type": "gas",         "capacity_mw": 120, "ramp_min": 15},
        {"id": "RJ_Hydro_01",    "type": "hydro",        "capacity_mw": 50,  "ramp_min": 5},
    ],
    "GJ01": [
        {"id": "Dhuvaran_Gas",   "type": "gas",         "capacity_mw": 100, "ramp_min": 20},
        {"id": "GJ_Pumped_01",   "type": "pumped_hydro", "capacity_mw": 40,  "ramp_min": 8},
    ],
    "TN01": [
        {"id": "Mettur_Hydro",   "type": "hydro",       "capacity_mw": 70,  "ramp_min": 5},
        {"id": "TN_Gas_01",      "type": "gas",         "capacity_mw": 80,  "ramp_min": 18},
    ],
}

BASE_DEMAND = {"RJ01": 85, "GJ01": 70, "TN01": 55}

MERIT_CLASS = {"hydro": 1, "pumped_hydro": 2, "gas": 3, "coal": 4}


def _hhmm(dt: datetime, delta_min: int) -> str:
    return (dt + timedelta(minutes=delta_min)).strftime("%H:%M")


def compute_dispatch(forecast: dict) -> dict:
    plant_id     = forecast["plant_id"]
    p10, p50, p90 = forecast["p10_mw"], forecast["p50_mw"], forecast["p90_mw"]
    demand       = BASE_DEMAND.get(plant_id, 70)
    assets       = BACKUP_ASSETS.get(plant_id, [])
    now          = datetime.now(timezone.utc)

    gap_mw    = max(0, demand - p50)
    buffer_mw = (p90 - p10) * 0.3
    required  = gap_mw + buffer_mw
    reserve   = max(5.0, p50 * 0.10)

    selected, allocated = None, 0.0
    if assets and required > 2:
        for asset in sorted(assets, key=lambda a: a["ramp_min"]):
            if asset["capacity_mw"] >= required * 0.8:
                selected  = asset
                allocated = min(required, asset["capacity_mw"])
                break
        if not selected:
            selected  = sorted(assets, key=lambda a: a["ramp_min"])[0]
            allocated = min(required, selected["capacity_mw"])

    merit = MERIT_CLASS.get(selected["type"] if selected else "none", 3)
    action = (f"Confirm ramp-up by {_hhmm(now, -(selected['ramp_min']))}"
              if selected else "No backup required — solar supply sufficient")

    return {
        "plant_id":                plant_id,
        "timestamp":               now.isoformat(),
        "p10_mw":                  p10,
        "p50_mw":                  p50,
        "p90_mw":                  p90,
        "demand_mw":               demand,
        "expected_gap_mw":         round(gap_mw, 2),
        "total_required_backup_mw": round(required, 2),
        "selected_asset":          selected["id"]   if selected else None,
        "asset_type":              selected["type"] if selected else None,
        "allocated_mw":            round(allocated, 2),
        "spinning_reserve_mw":     round(reserve, 2),
        "cerc_merit_class":        merit,
        "action_note":             action,
        "anomaly_detected":        forecast.get("anomaly_detected", False),
    }


def write_dispatch(dispatch: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, "dispatch_commands.jsonl")
    with open(path, "a") as f:
        f.write(json.dumps(dispatch) + "\n")
