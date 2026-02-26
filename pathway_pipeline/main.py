"""
main.py — RenewCast Pipeline Entry Point
Orchestrates all components: telemetry, weather, forecasting, dispatch, LLM.
"""

import json, logging, os, sys, time, threading
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathway_pipeline.config           import DATA_DIR
from pathway_pipeline.telemetry_source import emit_telemetry_forever
from pathway_pipeline.weather_source   import emit_weather_forever
from pathway_pipeline.forecast_model   import update_and_predict
from pathway_pipeline.rl_dispatch      import compute_dispatch, write_dispatch
from pathway_pipeline.compliance_gate  import gate_dispatch
from pathway_pipeline.llm_agent        import (generate_dispatch_advisory,
                                                generate_anomaly_report,
                                                write_advisory, write_anomaly)
from pathway_pipeline.document_store   import get_store

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("renewcast")

TELEMETRY_FILE    = os.path.join(DATA_DIR, "telemetry_stream.jsonl")
WEATHER_FILE      = os.path.join(DATA_DIR, "weather_stream.jsonl")
_TELEMETRY_CURSOR = 0
_WEATHER_CACHE: dict = {}

# Track previous dispatch per plant to detect changes (for demo highlight)
_LAST_DISPATCH: dict = {}


def start_background_threads():
    os.makedirs(DATA_DIR, exist_ok=True)
    for f in [TELEMETRY_FILE, WEATHER_FILE]:
        if os.path.exists(f):
            os.remove(f)

    threading.Thread(target=emit_telemetry_forever, args=(TELEMETRY_FILE,),
                     daemon=True, name="Telemetry").start()
    log.info("✓ Telemetry emitter started (3 plants @ 10s intervals)")

    threading.Thread(target=emit_weather_forever, args=(WEATHER_FILE,),
                     daemon=True, name="Weather").start()
    log.info("✓ Weather poller started (OpenWeatherMap / synthetic fallback)")

    store = get_store()
    threading.Thread(target=store.watch_forever, args=(5,),
                     daemon=True, name="DocStore").start()
    log.info("✓ Document store watcher started (live RAG index)")


def read_new_telemetry() -> list:
    global _TELEMETRY_CURSOR
    rows = []
    if not os.path.exists(TELEMETRY_FILE):
        return rows
    with open(TELEMETRY_FILE) as f:
        f.seek(_TELEMETRY_CURSOR)
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        _TELEMETRY_CURSOR = f.tell()
    return rows


def update_weather_cache():
    if not os.path.exists(WEATHER_FILE):
        return
    with open(WEATHER_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    row = json.loads(line)
                    pid = row.get("plant_id")
                    if pid:
                        _WEATHER_CACHE[pid] = row
                except json.JSONDecodeError:
                    pass


def process_row(row: dict):
    global _LAST_DISPATCH
    plant_id = row.get("plant_id")
    if not plant_id:
        return

    weather = _WEATHER_CACHE.get(plant_id, {})
    merged  = {**row, **{k: v for k, v in weather.items() if k not in row}}

    # ── Forecast ──────────────────────────────────────────────────────────────
    forecast = update_and_predict(plant_id, merged)

    # Build a rich log line showing learning progress
    mae_str = ""
    if forecast.get("mae") is not None:
        arrow = "↓" if forecast.get("mae_improving") else "~"
        mae_str = f" | MAE={forecast['mae']:.2f}MW{arrow}"

    cloud_pct = int(row.get("cloud_fraction", 0) * 100)
    sim_hour  = row.get("simulated_hour", "?")

    log.info(
        f"[{plant_id}] ☀ {forecast['actual_mw']:.1f}MW actual "
        f"| P50={forecast['p50_mw']:.1f}MW "
        f"| cloud={cloud_pct}% "
        f"| hour={sim_hour:.1f} "
        f"| n={forecast['n_trained']}"
        f"{mae_str}"
    )

    # ── Dispatch + Compliance Gate ───────────────────────────────────────────
    dispatch_raw = compute_dispatch(forecast)
    dispatch = gate_dispatch(dispatch_raw)
    if dispatch.get("status") != "held":
        write_dispatch(dispatch)

    # Highlight if dispatch changed from last tick (event response visible)
    prev     = _LAST_DISPATCH.get(plant_id, {})
    changed  = prev.get("allocated_mw") != dispatch.get("allocated_mw")
    marker   = " ◄ DISPATCH CHANGED" if changed else ""

    log.info(
        f"[{plant_id}] ⚡ {dispatch.get('selected_asset','none')} "
        f"{dispatch.get('allocated_mw',0):.1f}MW backup "
        f"| gap={dispatch.get('expected_gap_mw',0):.1f}MW "
        f"| CERC-{dispatch.get('cerc_merit_class')} "
        f"| status={dispatch.get('status','approved')}"
        f"{marker}"
    )
    _LAST_DISPATCH[plant_id] = dispatch

    # ── LLM Advisory — every 6th tick per plant ───────────────────────────────
    if forecast["n_trained"] % 6 == 1:
        log.info(f"[{plant_id}] 📋 Generating LLM advisory (RAG → CERC docs)...")
        advisory = generate_dispatch_advisory(dispatch, merged)
        write_advisory(advisory, dispatch)
        log.info(f"[{plant_id}] 📋 Advisory written: {advisory[:100]}...")

    # ── Anomaly Detection ─────────────────────────────────────────────────────
    if forecast["anomaly_detected"]:
        log.warning(
            f"[{plant_id}] 🚨 ANOMALY DETECTED — "
            f"underperforming P50 for {len(forecast['deviation_history'])} "
            f"consecutive intervals. Generating report..."
        )
        report = generate_anomaly_report(plant_id, forecast, merged)
        write_anomaly(report, plant_id, forecast)
        log.warning(f"[{plant_id}] 🚨 Anomaly report written")


def main():
    log.info("=" * 60)
    log.info("  RenewCast — Autonomous Grid Intelligence Pipeline")
    log.info("  3 plants | Online ML | Live RAG | LLM Advisories")
    log.info("=" * 60)

    if not os.environ.get("OPENAI_API_KEY") or "your-" in os.environ.get("OPENAI_API_KEY", ""):
        log.warning("⚠  OPENAI_API_KEY not set — advisories in demo mode")
    else:
        log.info("✓ OpenAI API key loaded — real LLM advisories enabled")

    if not os.environ.get("OPENWEATHER_API_KEY") or "your-" in os.environ.get("OPENWEATHER_API_KEY", ""):
        log.warning("⚠  OPENWEATHER_API_KEY not set — using synthetic weather")
    else:
        log.info("✓ OpenWeatherMap key loaded — live weather enabled")

    start_background_threads()

    log.info("Waiting 3s for data sources to initialise...")
    time.sleep(3)

    log.info(f"Pipeline is LIVE → outputs in {DATA_DIR}/")
    log.info("Endpoints: http://localhost:8000/dispatch | /advisories | /status")
    log.info("-" * 60)

    while True:
        update_weather_cache()
        for row in read_new_telemetry():
            try:
                process_row(row)
            except Exception as e:
                log.error(f"Error processing {row.get('plant_id')}: {e}")
        time.sleep(2)


if __name__ == "__main__":
    main()
