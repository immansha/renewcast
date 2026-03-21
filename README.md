# RenewCast — Autonomous Grid Intelligence System

> **Every weather event triggers a forecast, a dispatch decision, and a regulatory-grounded advisory fully autonomous, no human in the loop.**

Built for the **Hack For Green Bharat 2026** hackathon (Pathway track).

---

## What It Does

India's grid operators manage renewable intermittency reactively. When a dust storm drops a Rajasthan solar plant from 95 MW to 20 MW in 40 minutes, the grid already has a deficit before a peaker is called.

**RenewCast solves this by pre-scheduling fossil backup conservatively against the P10 lower bound** — so when generation disappoints, the peaker is already warming up, not being called from cold standby.

```
OpenWeatherMap (30s) + Synthetic Telemetry
              │
    Python Streaming Pipeline
              │
    River Online Forecast Model
    (P10 / P50 / P90 via quantile regression)
              │
    RL Dispatch Agent (rule-based, SB3 PPO architecture)
              │
    Compliance Gate (ramp rate + CERC must-run check)
              │
    ┌─────────────────────┐
    │                     │
dispatch_commands.jsonl   │
    │              Pathway Document Store
    │              CERC rules · Plant specs · DSM regs
    │                     │
    └──────── LLM Advisory Agent (GPT-4o-mini / Groq)
                          │
              operator_advisory.jsonl
                          │
              Streamlit Dashboard + FastAPI
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Streaming pipeline | Python (event-driven, 30s intervals) |
| Online ML | River — AdaptiveRandomForest + 3× QuantileRegressor |
| Probabilistic forecast | P10 / P50 / P90 via pinball loss quantile regression |
| Dispatch agent | Rule-based (architecture mirrors SB3 PPO policy) |
| RL training | Stable-Baselines3 PPO on GridDispatchEnv |
| RAG document store | FAISS + live file-watching, auto re-index on new docs |
| LLM advisories | GPT-4o-mini / Groq — RAG-grounded, anti-hallucination prompt |
| Compliance gate | Ramp-rate + CERC must-run enforcement, held command queue |
| API | FastAPI + SSE live stream |
| Dashboard | Streamlit |
| Deployment | Docker Compose (Railway) |

---

## Three Plants

| Plant ID | Location | Type | Capacity |
|---|---|---|---|
| RJ01 | Jodhpur, Rajasthan | Solar | 100 MW |
| GJ01 | Kutch, Gujarat | Solar + Wind | 80 MW |
| TN01 | Tirunelveli, Tamil Nadu | Wind | 60 MW |

---

## Quick Start

### Docker (Recommended)

```bash
# 1. Clone the repo
git clone https://github.com/yourhandle/renewcast
cd renewcast

# 2. Set up environment
cp .env.example .env
# Edit .env — both keys are OPTIONAL (see below)

# 3. Build and run
docker compose build
docker compose up

# 4. Open dashboard
# Streamlit: http://localhost:8501
# API:       http://localhost:8000/status
```

### Local (No Docker)

```bash
pip install -r requirements.pipeline.txt
python -m pathway_pipeline.main
```

---

## API Keys

Both keys are **optional**. The system runs fully without them.

| Key | Source | Without it |
|---|---|---|
| `OPENAI_API_KEY` | platform.openai.com | LLM advisories show placeholder text |
| `OPENWEATHER_API_KEY` | openweathermap.org (free tier) | Synthetic weather used automatically |

Everything else — forecasting, dispatch, compliance gate, anomaly detection — runs normally without any keys.

---

## API Endpoints

Base URL: `http://localhost:8000`

| Endpoint | Returns |
|---|---|
| `/dispatch?n=20` | Last N dispatch commands |
| `/advisories?n=10` | Last N LLM operator advisories |
| `/anomalies?n=10` | Last N anomaly reports |
| `/telemetry?n=30` | Raw telemetry stream |
| `/status` | Record counts + health check |
| `/stream/dispatch` | SSE live stream (real-time) |

---

## Demo Commands

```bash
# Inject a high-severity cloud event on RJ01
docker compose run --rm pathway_pipeline python scripts/inject_event.py --type=cloud --plant=RJ01 --severity=high

# Inject inverter fault on GJ01
docker compose run --rm pathway_pipeline python scripts/inject_event.py --type=inverter_fault --plant=GJ01

# Clear all injected events
docker compose run --rm pathway_pipeline python scripts/inject_event.py --clear

# Watch live output in terminal
bash scripts/watch_outputs.sh
```

### Demo Sequence (2 min 30 sec)

| Time | Action | What You See |
|---|---|---|
| 0:00 | `docker compose up` | Three plants on Streamlit, dispatch commands accumulating |
| 0:30 | Point at pipeline logs | River model tick counter, per-plant MAE improving |
| 1:00 | Inject cloud event on RJ01 | RJ01 P50 drops, RL agent increases gas backup |
| 1:20 | Show held command | Inject extreme action → appears in `held_commands.jsonl` with reason |
| 1:40 | Show LLM advisory | CERC document cited in plain-English explanation |


---

## Key Technical Details

### P10 / P50 / P90 — Quantile Regression

Three independent River `LinearRegression` models with pinball loss at α = 0.10, 0.50, and 0.90. This is statistically valid quantile regression — not variance subtracted from a point forecast.

```python
class QuantileRegressor:
    def __init__(self, alpha: float):
        self.model = compose.Pipeline(
            preprocessing.StandardScaler(),
            linear_model.LinearRegression(
                optimizer=optim.SGD(lr=0.01),
                loss=optim.losses.Quantile(alpha=alpha),  # pinball loss
            ),
        )
```

The P10 is the dispatch safety input  the RL agent pre-schedules backup conservatively against the pessimistic lower bound.

### River State Persistence

River model state is serialized to `models/river_state.pkl` every 50 ticks and restored on startup. State is keyed by `plant_id` so each plant's model is fully isolated.

### Compliance Gate

Every dispatch command passes through the compliance gate before reaching the SCADA output:

1. **Ramp rate check** — if MW change exceeds plant limit (RJ01: 25 MW, GJ01: 20 MW, TN01: 15 MW), command is held and adjusted
2. **CERC must-run check** — RAG query retrieves relevant regulatory context; if must-run constraint violated, command is held

Held commands go to `held_commands.jsonl` with reason attached. Only approved commands reach `dispatch_commands.jsonl`.

### Live RAG Document Store

FAISS-backed document store watches the `/docs/` folder. Drop a new PDF or `.txt` file and it is chunked, embedded, and indexed within seconds. The next LLM advisory will reference it automatically.

### Anomaly Detection

Persistent underperformance detection: if actual generation deviates more than 15% below P50 for 6 consecutive intervals, an anomaly report is generated and written to `anomaly_reports.jsonl`.

---

## Project Structure

```
renewcast/
├── docker-compose.yml              One command startup
├── Dockerfile.pipeline             Pipeline container
├── Dockerfile.api                  API container
├── requirements.pipeline.txt       Pipeline dependencies
├── requirements.api.txt            API dependencies
├── .env.example                    Copy to .env, add keys
│
├── pathway_pipeline/
│   ├── main.py                     Entry point
│   ├── config.py                   Plants, paths, settings
│   ├── telemetry_source.py         Synthetic sensor stream (30s)
│   ├── weather_source.py           OpenWeatherMap poller + fallback
│   ├── forecast_model.py           River online ML — P10/P50/P90
│   ├── rl_dispatch.py              Dispatch decision agent
│   ├── compliance_gate.py          Ramp rate + CERC constraint check
│   ├── document_store.py           Live FAISS RAG index
│   └── llm_agent.py                GPT-4o-mini advisory generation
│
├── api/
│   └── main.py                     FastAPI server + SSE stream
│
├── docs/                           Live-indexed regulatory documents
│   ├── cerc_merit_order_2025.txt
│   ├── plant_specs_RJ01.txt
│   └── gujarat_sldc_protocol.txt
│
├── streamlit_app.py                Live Streamlit dashboard
│
├── scripts/
│   ├── inject_event.py             Demo event injector
│   ├── train_rl_policy.py          Pre-train SB3 PPO policy
│   ├── demo_ui.html                Standalone browser dashboard
│   ├── run_local.sh                Local runner (no Docker)
│   └── watch_outputs.sh            Live terminal output watcher
│
└── data/                           Runtime outputs (auto-created)
    ├── dispatch_commands.jsonl     Approved SCADA commands
    ├── held_commands.jsonl         Compliance-held commands + reasons
    ├── operator_advisory.jsonl     LLM-generated advisories
    └── anomaly_reports.jsonl       Anomaly detection reports
```

---

## Adding a New Plant

1. Add to `PLANTS` list in `pathway_pipeline/config.py`
2. Add backup assets to `BACKUP_ASSETS` in `pathway_pipeline/rl_dispatch.py`
3. Add ramp limits to `RAMP_LIMIT_MW` in `pathway_pipeline/compliance_gate.py`
4. Drop a plant spec doc into `docs/plant_specs_XXXX.txt`
5. Restart pipeline — the new plant appears automatically

---

## Q&A

**How did you compute P10?**
Three separate River LinearRegression models with pinball loss at α = 0.10, 0.50, and 0.90. Pinball loss is the standard approach for online quantile regression. The P10 is a statistically valid 10th percentile estimate — not a margin subtracted from a point forecast.

**Is the model actually learning?**
Yes — River updates weights with every incoming data point (true online learning). MAE is tracked across ticks; the log shows `MAE=X.XXMWâ†"` when the model is improving. State is persisted across restarts.

**Does the LLM have real authority?**
Yes — the compliance gate runs before the SCADA write. Non-compliant commands are held in `held_commands.jsonl` with reasons. The LLM doesn't just explain; it gates.

**Does it scale?**
Every UDF, window, and document store query is keyed by `plant_id`. Adding a fourth plant is one config change. The architecture was built for three plants but designed for three hundred.

---

## License

MIT
