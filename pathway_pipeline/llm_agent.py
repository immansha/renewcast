"""
llm_agent.py
Grid Intelligence Agent.
Supports OpenAI, Groq (free), or Google Gemini (free).
Set which provider to use via environment variables.
"""

import json, os
from datetime import datetime, timezone
from pathway_pipeline.config import DATA_DIR
from pathway_pipeline.document_store import get_store

# ── Provider Detection ─────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

def _get_provider():
    if GROQ_API_KEY and "your-" not in GROQ_API_KEY:
        return "groq"
    if OPENAI_API_KEY and "your-" not in OPENAI_API_KEY:
        return "openai"
    if GEMINI_API_KEY and "your-" not in GEMINI_API_KEY:
        return "gemini"
    return "demo"

PROVIDER = _get_provider()
print(f"[LLMAgent] Using provider: {PROVIDER}")

# ── Client Setup ───────────────────────────────────────────────────────────────
_client = None

if PROVIDER == "groq":
    try:
        from groq import Groq
        _client = Groq(api_key=GROQ_API_KEY)
        LLM_MODEL = "llama-3.1-8b-instant"   # free, fast
        print(f"[LLMAgent] Groq client ready (model: {LLM_MODEL})")
    except ImportError as e:
        print(f"[LLMAgent] ❌ groq package not installed — {e}")
        PROVIDER = "demo"
    except Exception as e:
        print(f"[LLMAgent] ❌ Groq initialization failed — {e}")
        PROVIDER = "demo"

elif PROVIDER == "openai":
    try:
        from openai import OpenAI
        _client = OpenAI(api_key=OPENAI_API_KEY)
        LLM_MODEL = "gpt-4o-mini"
        print(f"[LLMAgent] OpenAI client ready (model: {LLM_MODEL})")
    except ImportError:
        print("[LLMAgent] openai package not installed — falling back to demo mode")
        PROVIDER = "demo"

elif PROVIDER == "gemini":
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _client = genai.GenerativeModel("gemini-1.5-flash")
        LLM_MODEL = "gemini-1.5-flash"
        print(f"[LLMAgent] Gemini client ready (model: {LLM_MODEL})")
    except ImportError:
        print("[LLMAgent] google-generativeai not installed — falling back to demo mode")
        PROVIDER = "demo"


def _call_llm(system: str, user: str) -> str:
    """Call whichever LLM provider is configured."""
    if PROVIDER == "demo" or _client is None:
        return (
            "Grid Advisory: Solar generation is tracking within expected bounds. "
            "Backup dispatch has been pre-positioned per CERC merit order requirements. "
            "Spinning reserve maintained above minimum threshold. "
            "[Add GROQ_API_KEY or OPENAI_API_KEY to .env for full AI-generated advisories]"
        )

    try:
        if PROVIDER == "groq":
            response = _client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                temperature=0.3,
                max_tokens=350,
            )
            return response.choices[0].message.content.strip()

        elif PROVIDER == "openai":
            response = _client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                temperature=0.3,
                max_tokens=350,
            )
            return response.choices[0].message.content.strip()

        elif PROVIDER == "gemini":
            prompt = f"{system}\n\n{user}"
            response = _client.generate_content(prompt)
            return response.text.strip()

    except Exception as e:
        print(f"[LLMAgent] {PROVIDER} error: {e}")
        return f"[LLM temporarily unavailable: {str(e)[:100]}]"


def _rag(query: str) -> str:
    chunks = get_store().query(query, top_k=3)
    parts  = [f"[From {c.get('source','?')}]\n{c.get('text','').strip()}"
              for c in chunks if c.get("text")]
    return "\n\n".join(parts) or "No regulatory documents available."


# ── Advisory Generation ────────────────────────────────────────────────────────

ADVISORY_SYSTEM = """You are a Grid Intelligence Agent for India's renewable energy grid.
Write a precise, actionable one-paragraph dispatch advisory for grid operators.
Include: current forecast conditions, the dispatch decision made, regulatory basis
from the CERC documents provided, recommended operator action with timing, and
reserve guidance. Be specific with MW numbers. Cite the document you reference."""

def generate_dispatch_advisory(dispatch: dict, telemetry: dict) -> str:
    rag_ctx = _rag(f"CERC merit order class {dispatch.get('cerc_merit_class',3)} dispatch rules solar backup")
    user = f"""
Plant: {dispatch['plant_id']} ({telemetry.get('state','India')})
Current cloud cover: {telemetry.get('cloud_fraction',0.2)*100:.0f}%
GHI: {telemetry.get('ghi_wm2',500):.0f} W/m²
Actual generation: {telemetry.get('ac_power_mw',0):.1f} MW
P10 forecast: {dispatch['p10_mw']:.1f} MW
P50 forecast: {dispatch['p50_mw']:.1f} MW
P90 forecast: {dispatch['p90_mw']:.1f} MW
Demand: {dispatch['demand_mw']:.1f} MW
Dispatch decision: Allocate {dispatch.get('allocated_mw',0):.1f} MW from {dispatch.get('selected_asset','none')}
CERC merit order class: {dispatch.get('cerc_merit_class',3)}
Action required: {dispatch.get('action_note','')}
Spinning reserve: {dispatch.get('spinning_reserve_mw',10):.1f} MW

Regulatory context from live document index:
{rag_ctx}

Write the operator dispatch advisory in one paragraph.
"""
    return _call_llm(ADVISORY_SYSTEM, user)


# ── Anomaly Report ─────────────────────────────────────────────────────────────

ANOMALY_SYSTEM = """You are a Grid Intelligence Agent analyzing renewable energy anomalies.
Write a clear technical anomaly report for engineers. Include: statistical deviation
summary, most likely technical root cause, reference to applicable plant specs or
maintenance protocols from the documents provided, and recommended immediate action
with specific steps."""

def generate_anomaly_report(plant_id: str, forecast: dict, telemetry: dict) -> str:
    actual   = forecast.get("actual_mw", 0)
    p50      = forecast.get("p50_mw", 0)
    dev_pct  = ((actual - p50) / p50 * 100) if p50 > 0 else 0
    history  = forecast.get("deviation_history", [])
    inv_eff  = telemetry.get("inverter_efficiency", 0.973)
    spec_ctx = _rag(f"plant {plant_id} inverter efficiency maintenance inspection protocol")

    user = f"""
Plant: {plant_id}
Actual generation: {actual:.1f} MW
P50 forecast: {p50:.1f} MW
Deviation: {dev_pct:.1f}%
Consecutive underperformance intervals: {len(history)}
Deviation values: {[f'{d*100:.0f}%' for d in history]}
Measured inverter efficiency: {inv_eff*100:.1f}%
Expected inverter efficiency: 97.3%

Plant specifications and protocols:
{spec_ctx}

Generate the anomaly report with root cause and recommended action.
"""
    return _call_llm(ANOMALY_SYSTEM, user)


# ── Output Writers ─────────────────────────────────────────────────────────────

def write_advisory(advisory: str, dispatch: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    record = {
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "plant_id":     dispatch.get("plant_id"),
        "type":         "dispatch_advisory",
        "advisory":     advisory,
        "llm_provider": PROVIDER,
        "dispatch_ref": {
            "asset":            dispatch.get("selected_asset"),
            "allocated_mw":     dispatch.get("allocated_mw"),
            "cerc_merit_class": dispatch.get("cerc_merit_class"),
        },
    }
    with open(os.path.join(DATA_DIR, "operator_advisory.jsonl"), "a") as f:
        f.write(json.dumps(record) + "\n")


def write_anomaly(report: str, plant_id: str, forecast: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    record = {
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "plant_id":   plant_id,
        "type":       "anomaly_report",
        "report":     report,
        "p50_mw":     forecast.get("p50_mw"),
        "actual_mw":  forecast.get("actual_mw"),
    }
    with open(os.path.join(DATA_DIR, "anomaly_reports.jsonl"), "a") as f:
        f.write(json.dumps(record) + "\n")
