import os

PLANTS = [
    {"id": "RJ01", "name": "Rajasthan Solar", "lat": 27.0238, "lon": 74.2179, "capacity_mw": 100, "state": "Rajasthan", "sldc": "RLDC"},
    {"id": "GJ01", "name": "Gujarat Solar",   "lat": 23.2156, "lon": 72.6369, "capacity_mw": 80,  "state": "Gujarat",    "sldc": "WRLDC"},
    {"id": "TN01", "name": "Tamil Nadu Solar", "lat": 10.7905, "lon": 79.8083, "capacity_mw": 60,  "state": "Tamil Nadu", "sldc": "SRLDC"},
]

PLANT_MAP = {p["id"]: p for p in PLANTS}

WEATHER_POLL_INTERVAL_SEC  = 30
TELEMETRY_EMIT_INTERVAL_SEC = 10
WINDOW_DURATION_SEC         = 6 * 3600
WINDOW_HOP_SEC              = 300

DATA_DIR       = os.environ.get("DATA_DIR",  "/app/data")
DOCS_DIR       = os.environ.get("DOCS_DIR",  "/app/docs")
DISPATCH_JSONL = os.path.join(DATA_DIR, "dispatch_commands.jsonl")
ADVISORY_JSONL = os.path.join(DATA_DIR, "operator_advisory.jsonl")
ANOMALY_JSONL  = os.path.join(DATA_DIR, "anomaly_reports.jsonl")
HELD_JSONL     = os.path.join(DATA_DIR, "held_commands.jsonl")

RL_MODEL_PATH  = "/app/models/dispatch_policy.zip"
OPENAI_MODEL   = "gpt-4o-mini"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
