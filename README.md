Here it is directly — copy this whole thing into your `README.md` file:

```markdown
# 🌱 RenewCast v4
## Autonomous Grid Dispatch System — Pathway Native

> Real-time renewable forecasting, RL-based backup dispatch, and regulatory-grounded AI advisories — all inside a single streaming pipeline.

---

## 🚀 One-Line Pitch

**RenewCast** is a fully autonomous grid dispatch system where every new weather event triggers:

1. Online quantile forecast update (P10 / P50 / P90)
2. RL-based backup allocation (PPO agent)
3. Compliance-gated dispatch decision (RAG + constraint check)
4. Regulatory-grounded AI advisory (CERC-cited, LLM-generated)

All inside a **single Pathway pipeline**. No cron jobs. No batch inference. No human trigger.

---

## 🖥️ Live Demo Screenshots

### Dashboard — Live Grid Dispatch System
![RenewCast Live Dashboard](s4.jpeg)

### Generation Forecast — P10 / P50 / P90 Charts
![Forecast Charts](s3.jpeg)

### Autonomous Dispatch Commands (Live)
![Dispatch Commands](s2.jpeg)

### Compliance-Held Commands + AI Advisory
![Compliance Gate and Advisory](s1.jpeg)

---

## 🏗️ Architecture Overview

```
OpenWeatherMap API (30s polling)     Synthetic Telemetry Stream
         |                                      |
         +──────────────────────────────────────+
                          |
                Pathway HTTP Connector
                + Python Input Connector
                          |
                Pathway Sliding Window (6h per plant)
                          |
          River Online Forecast Model (P10 / P50 / P90)
                          |
          +───────────────+────────────────+
          |                                |
RL Dispatch Agent (SB3 PPO)       Pathway Document Store
                                  CERC rules | Plant specs
          +───────────────+────────────────+
                          |
       Pathway LLM xPack — Grid Intelligence Agent
                          |
          dispatch_commands.jsonl + operator_advisory.jsonl
                          |
                Streamlit Dashboard (live)
```

---

## 🔁 Real-Time Flow

```
Weather Event (30s)
        ↓
Pathway Sliding Window (6h per plant)
        ↓
River Quantile Model (P10 / P50 / P90)
        ↓
RL Dispatch Agent (PPO)
        ↓
Compliance Gate (RAG + ramp-rate + must-run check)
        ↓
Approved Command → dispatch_commands.jsonl
Held Command    → held_commands.jsonl (with reason)
        ↓
LLM Advisory (CERC-cited, RAG-grounded)
        ↓
Streamlit Live Dashboard
```

---

## 🧠 Core Technologies

| Component | Technology |
|---|---|
| Streaming Engine | Pathway |
| Online ML | River — QuantileRegressor (α = 0.1 / 0.5 / 0.9) |
| RL Agent | Stable Baselines3 PPO |
| RAG | Pathway Document Store + GPT-4o-mini / Groq |
| Compliance Gate | Ramp-rate + CERC constraint check |
| UI | Streamlit |
| Deployment | Docker Compose |

---

## 🌍 Three Plants

| Plant ID | Location | Type | Capacity |
|---|---|---|---|
| RJ01 | Jodhpur, Rajasthan | Solar | 100 MW |
| GJ01 | Kutch, Gujarat | Solar + Wind | 80 MW |
| TN01 | Tirunelveli, Tamil Nadu | Wind | 60 MW |

---

## 🛡️ Compliance Authority — Not Decorative AI

Commands are **held before execution** if they:
- Exceed ramp rate limits
- Violate CERC must-run constraints

Held commands appear in `held_commands.jsonl` with full reason and adjusted MW. The LLM advisory explains the violation citing the live CERC document.

> "The LLM doesn't just explain — it gates."

---

## 📚 Live RAG Re-Index Demo

Drop a new PDF into `/docs/` → Document Store re-indexes in seconds → next advisory references the updated regulation automatically.

---

## 🧪 How to Run

### 1. Clone
```bash
git clone https://github.com/immansha/renewcast.git
cd renewcast
```

### 2. Set API Keys
```bash
cp .env.example .env
# add your keys to .env
```

### 3. Start Everything
```bash
docker compose up --build
```

### 4. Open Dashboard
```
http://localhost:8501
```

---

## 🌪️ Inject a Demo Event

```bash
python scripts/inject_event.py --type=cloud --plant=RJ01 --severity=high
python scripts/inject_event.py --type=inverter_fault --plant=GJ01
python scripts/inject_event.py --clear
```

---

## 📂 Project Structure

```
renewcast/
├── docker-compose.yml
├── .env.example
├── pathway_pipeline/
│   ├── main.py
│   ├── weather_source.py
│   ├── telemetry_source.py
│   ├── forecast_model.py
│   ├── rl_dispatch.py
│   ├── document_store.py
│   └── llm_agent.py
├── api/
│   └── main.py
├── scripts/
│   ├── inject_event.py
│   └── train_rl_policy.py
├── docs/
│   ├── cerc_merit_order_2025.pdf
│   └── gujarat_sldc_protocol.pdf
├── data/
│   ├── dispatch_commands.jsonl
│   ├── held_commands.jsonl
│   └── operator_advisory.jsonl
└── models/
    └── dispatch_policy.zip
```

---

## 🏆 Hackathon Track — Hack for Green Bharat 2026

| Requirement | Status |
|---|---|
| Pathway-native streaming pipeline | ✅ |
| Online ML with River | ✅ |
| RAG with actual decision authority | ✅ |
| Document Store live re-index | ✅ |
| Real-time autonomous decision loop | ✅ |
| Streamlit demo UI | ✅ |
| Docker Compose one-command startup | ✅ |

---

*Built with Pathway, River, Stable Baselines3, and a lot of coffee. ☕*
```

Just make sure `s1.jpeg`, `s2.jpeg`, `s3.jpeg`, `s4.jpeg` are in the **same folder as README.md** when you push to GitHub and the images will show up automatically.
