 RenewCast v4 — Grid Intelligence Pipeline

Fully autonomous solar grid dispatch. Every weather event triggers a forecast,
a dispatch decision, and a regulatory-grounded natural language advisory.

---

## Quick Start (Docker — Recommended on Windows)

```bash
# 1. Copy and edit environment file
copy .env.example .env
# Open .env in Notepad and add your API keys (optional)

# 2. Build and start
docker compose build
docker compose up

# 3. Check it's working — open in browser:
#    http://localhost:8000/status
#    http://localhost:8000/dispatch

# 4. Open the live dashboard
#    Double-click scripts/demo_ui.html in File Explorer
```

---

## Demo Commands

```bash
# Inject a cloud event on RJ01
docker compose run --rm pathway_pipeline python scripts/inject_event.py --type=cloud --plant=RJ01 --severity=high

# Inject inverter fault on GJ01
docker compose run --rm pathway_pipeline python scripts/inject_event.py --type=inverter_fault --plant=GJ01

# Clear all events
docker compose run --rm pathway_pipeline python scripts/inject_event.py --clear

# Watch outputs live (Linux/Mac/WSL)
bash scripts/watch_outputs.sh
```

---

## API Endpoints  (all at http://localhost:8000)

| Endpoint | What it returns |
|----------|----------------|
| /dispatch?n=20 | Last N dispatch commands |
| /advisories?n=10 | Last N LLM operator advisories |
| /anomalies?n=10 | Last N anomaly reports |
| /telemetry?n=30 | Raw telemetry stream |
| /status | Record counts + health |
| /stream/dispatch | SSE live stream |

---

## Project Files

```
renewcast/
├── docker-compose.yml          Start everything
├── Dockerfile.pipeline         Pipeline container
├── Dockerfile.api              API container
├── requirements.pipeline.txt   Python deps for pipeline
├── requirements.api.txt        Python deps for API
├── .env.example                Copy to .env and add keys
│
├── pathway_pipeline/
│   ├── main.py                 Entry point — start here
│   ├── config.py               Plants, paths, settings
│   ├── telemetry_source.py     Synthetic sensor stream
│   ├── weather_source.py       OpenWeatherMap poller
│   ├── forecast_model.py       River online ML (P10/P50/P90)
│   ├── rl_dispatch.py          Dispatch decision agent
│   ├── document_store.py       Live FAISS RAG index
│   └── llm_agent.py            GPT-4o-mini advisories
│
├── api/
│   └── main.py                 FastAPI server
│
├── docs/                       Live-indexed regulatory docs
│   ├── cerc_merit_order_2025.txt
│   ├── plant_specs_RJ01.txt
│   └── gujarat_sldc_protocol.txt
│
├── scripts/
│   ├── inject_event.py         Demo event injector
│   ├── train_rl_policy.py      Pre-train RL policy (optional)
│   ├── demo_ui.html            Browser dashboard
│   ├── run_local.sh            Local runner (no Docker)
│   └── watch_outputs.sh        Live terminal watcher
│
└── data/                       Runtime outputs (auto-created)
    ├── dispatch_commands.jsonl
    ├── operator_advisory.jsonl
    └── anomaly_reports.jsonl
```

---

## API Keys

Both are OPTIONAL. System runs fully without them.

- OPENAI_API_KEY — from platform.openai.com (costs ~1 rupee for full demo)
- OPENWEATHER_API_KEY — from openweathermap.org (free tier is enough)

Without keys: weather is synthetic, LLM shows placeholder text.
Everything else (forecasting, dispatch, anomaly detection) runs normally.

---

## Adding a New Plant

1. Add to PLANTS list in pathway_pipeline/config.py
2. Add backup assets to BACKUP_ASSETS in pathway_pipeline/rl_dispatch.py
3. Add plant spec doc to docs/plant_specs_XXXX.txt
4. Restart pipeline
