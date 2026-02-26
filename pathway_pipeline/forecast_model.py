"""
forecast_model.py
Online forecasting using River. One model per plant.
Learns from every data point — no batch retraining ever.
Logs MAE improvement so judges can see the model getting smarter live.
"""

import math, threading, os, pickle
from datetime import datetime
from typing import Dict

try:
    from river import compose, linear_model, preprocessing, optim, metrics
    HAS_RIVER = True
except ImportError:
    HAS_RIVER = False
    print("[ForecastModel] River not installed — using heuristic forecasts")

_MODELS:  Dict[str, dict] = {}
_LOCK     = threading.Lock()
_HISTORY: Dict[str, list] = {}
HISTORY_WINDOW = 6

# Track MAE history per plant for visible learning demonstration
_MAE_HISTORY: Dict[str, list] = {}

STATE_PATH = os.environ.get("RIVER_STATE_PATH", "/app/models/river_state.pkl")


def _make_model():
    if not HAS_RIVER:
        return {"n_trained": 0}

    class QuantileRegressor:
        def __init__(self, alpha: float):
            self.alpha = alpha
            self.model = compose.Pipeline(
                preprocessing.StandardScaler(),
                linear_model.LinearRegression(
                    optimizer=optim.SGD(lr=0.01),
                    loss=optim.losses.Quantile(alpha=alpha),
                ),
            )

        def learn_one(self, x, y):
            self.model.learn_one(x, y)

        def predict_one(self, x):
            return self.model.predict_one(x)

    return {
        "p10":       QuantileRegressor(alpha=0.10),
        "p50":       QuantileRegressor(alpha=0.50),
        "p90":       QuantileRegressor(alpha=0.90),
        "mae":       metrics.MAE(),
        "n_trained": 0,
    }


def _load_state():
    if not HAS_RIVER:
        return
    if not os.path.exists(STATE_PATH):
        return
    try:
        with open(STATE_PATH, "rb") as f:
            state = pickle.load(f)
        if isinstance(state, dict):
            _MODELS.update(state.get("models", {}))
            _MAE_HISTORY.update(state.get("mae_history", {}))
            print(f"[ForecastModel] Restored River state for {len(_MODELS)} plants")
    except Exception:
        # Safe to ignore — will rebuild state online
        pass


def _save_state():
    if not HAS_RIVER:
        return
    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "wb") as f:
            pickle.dump(
                {"models": _MODELS, "mae_history": _MAE_HISTORY},
                f,
            )
    except Exception:
        # Persistence is best-effort; failures shouldn't break pipeline
        pass


_load_state()


def _features(row: dict) -> dict:
    # Use simulated_hour if available (demo mode), else real hour
    if "simulated_hour" in row:
        hour = float(row["simulated_hour"])
    else:
        hour = datetime.fromisoformat(
            row.get("timestamp", datetime.now().isoformat())
        ).hour

    return {
        "hour_sin":       math.sin(2 * math.pi * hour / 24),
        "hour_cos":       math.cos(2 * math.pi * hour / 24),
        "cloud_fraction": float(row.get("cloud_fraction", 0.2)),
        "ghi_wm2":        float(row.get("ghi_wm2", 0.0)),
        "temp_c":         float(row.get("temp_c", 28.0)),
    }


def update_and_predict(plant_id: str, row: dict) -> dict:
    with _LOCK:
        if plant_id not in _MODELS:
            _MODELS[plant_id]      = _make_model()
            _MAE_HISTORY[plant_id] = []

        m            = _MODELS[plant_id]
        features     = _features(row)
        actual_power = float(row.get("ac_power_mw", 0.0))
        capacity     = float(row.get("capacity_mw", 100.0))

        # Online learning — one sample at a time
        if HAS_RIVER and m["n_trained"] > 0:
            for key in ["p10", "p50", "p90"]:
                m[key].learn_one(features, actual_power)
            m["mae"].update(actual_power, m["p50"].predict_one(features))

        # Predict
        if not HAS_RIVER or m["n_trained"] < 3:
            naive          = capacity * max(0, 1 - float(row.get("cloud_fraction", 0.2))) * 0.7
            p50, p10, p90  = naive, naive * 0.8, min(capacity, naive * 1.2)
        else:
            p10 = max(0.0, m["p10"].predict_one(features))
            p50 = max(0.0, m["p50"].predict_one(features))
            p90 = max(p50, m["p90"].predict_one(features))
            p90 = min(capacity, p90)

        m["n_trained"] += 1

        # Track MAE improvement every 10 ticks for visible learning log
        mae_val = None
        mae_improving = None
        if HAS_RIVER and m["n_trained"] > 3:
            try:
                mae_val = round(m["mae"].get(), 3)
                _MAE_HISTORY[plant_id].append(mae_val)
                if len(_MAE_HISTORY[plant_id]) > 20:
                    _MAE_HISTORY[plant_id].pop(0)
                # Check if last 5 MAE values are trending down
                recent = _MAE_HISTORY[plant_id][-5:]
                if len(recent) >= 5:
                    mae_improving = recent[-1] < recent[0]
            except Exception:
                pass

        # Anomaly detection — persistent underperformance vs P50
        if plant_id not in _HISTORY:
            _HISTORY[plant_id] = []
        if m["n_trained"] > 3 and p50 > 1:
            dev = (actual_power - p50) / p50
            _HISTORY[plant_id].append(dev)
            if len(_HISTORY[plant_id]) > HISTORY_WINDOW:
                _HISTORY[plant_id].pop(0)

        history = _HISTORY.get(plant_id, [])
        anomaly = (
            len(history) >= HISTORY_WINDOW and
            all(d < -0.15 for d in history)
        )

        result = {
            "plant_id":          plant_id,
            "p10_mw":            round(p10, 2),
            "p50_mw":            round(p50, 2),
            "p90_mw":            round(p90, 2),
            "actual_mw":         round(actual_power, 2),
            "mae":               mae_val,
            "mae_improving":     mae_improving,
            "mae_history":       _MAE_HISTORY.get(plant_id, [])[-5:],
            "n_trained":         m["n_trained"],
            "anomaly_detected":  anomaly,
            "deviation_history": history[-HISTORY_WINDOW:],
        }
        # Best-effort periodic persistence of River state
        if HAS_RIVER and m["n_trained"] % 50 == 0:
            _save_state()
        return result
