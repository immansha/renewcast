import json
import os
import time
from datetime import datetime
from typing import List, Dict

import pandas as pd
import streamlit as st

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")

DISPATCH_PATH = os.path.join(DATA_DIR, "dispatch_commands.jsonl")
ADVISORY_PATH = os.path.join(DATA_DIR, "operator_advisory.jsonl")
HELD_PATH = os.path.join(DATA_DIR, "held_commands.jsonl")


def _read_jsonl(path: str, last_n: int = 100) -> List[Dict]:
    if not os.path.exists(path):
        return []
    rows: List[Dict] = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-last_n:]


def _latest_dispatch_by_plant(rows: List[Dict]) -> Dict[str, Dict]:
    latest: Dict[str, Dict] = {}
    for r in rows:
        pid = r.get("plant_id")
        ts = r.get("timestamp")
        if not pid or not ts:
            continue
        if pid not in latest or latest[pid].get("timestamp", "") < ts:
            latest[pid] = r
    return latest


def main():
    st.set_page_config(page_title="RenewCast", layout="wide")
    st.title("RenewCast — Live Grid Dispatch System")

    dispatch_rows = _read_jsonl(DISPATCH_PATH, last_n=200)
    advisory_rows = _read_jsonl(ADVISORY_PATH, last_n=50)
    held_rows = _read_jsonl(HELD_PATH, last_n=50)

    latest_by_plant = _latest_dispatch_by_plant(dispatch_rows)

    # Row 1 — plant metric cards
    col1, col2, col3 = st.columns(3)
    for col, plant in zip([col1, col2, col3], ["RJ01", "GJ01", "TN01"]):
        with col:
            d = latest_by_plant.get(plant)
            if not d:
                st.metric(label=f"{plant} Forecast (P50)", value="–", delta="Waiting for data")
            else:
                p10 = d.get("p10_mw", 0.0)
                p50 = d.get("p50_mw", 0.0)
                p90 = d.get("p90_mw", 0.0)
                st.metric(
                    label=f"{plant} Forecast (P50)",
                    value=f"{p50:.1f} MW",
                    delta=f"P10: {p10:.1f} | P90: {p90:.1f}",
                )

    # Row 2 — forecast history chart
    st.subheader("Generation Forecast — Latest Points")
    if dispatch_rows:
        records = []
        for r in dispatch_rows:
            try:
                ts = datetime.fromisoformat(r.get("timestamp"))
            except Exception:
                continue
            records.append(
                {
                    "time": ts,
                    "plant_id": r.get("plant_id"),
                    "p10_mw": r.get("p10_mw"),
                    "p50_mw": r.get("p50_mw"),
                    "p90_mw": r.get("p90_mw"),
                }
            )
        if records:
            df = pd.DataFrame.from_records(records)
            for plant in sorted(df["plant_id"].unique()):
                sub = df[df["plant_id"] == plant].sort_values("time")
                st.line_chart(
                    sub.set_index("time")[["p10_mw", "p50_mw", "p90_mw"]],
                    height=220,
                    use_container_width=True,
                )
    else:
        st.info("No dispatch data yet — start the pipeline and wait a few ticks.")

    # Row 3 — latest dispatch commands
    st.subheader("Autonomous Dispatch Commands (Live)")
    if dispatch_rows:
        for r in reversed(dispatch_rows[-20:]):
            status = r.get("status", "approved")
            color = "green" if status == "approved" else "red"
            st.markdown(
                f"**{r.get('plant_id','?')}** | {r.get('timestamp','?')} | "
                f":{color}[{status.upper()}] | "
                f"Backup: {r.get('allocated_mw',0):.1f} MW from {r.get('selected_asset','none')}"
            )
    else:
        st.write("No dispatch commands yet.")

    # Row 4 — latest held commands
    st.subheader("Compliance-Held Commands")
    if held_rows:
        for r in reversed(held_rows[-10:]):
            st.markdown(
                f"**{r.get('plant_id','?')}** | {r.get('timestamp','?')} | "
                f"Reason: {r.get('reason','?')} | "
                f"Adjusted MW: {r.get('adjusted_mw',0):.1f}"
            )
    else:
        st.caption("No commands held by compliance gate yet.")

    # Row 5 — latest advisory
    st.subheader("Operator Advisory (AI-Generated, RAG-Grounded)")
    if advisory_rows:
        last = advisory_rows[-1]
        st.info(last.get("advisory", "") or last.get("report", ""))
        ref = last.get("dispatch_ref", {})
        if ref:
            st.caption(
                f"Dispatch: {ref.get('asset','?')} "
                f"{ref.get('allocated_mw',0):.1f} MW | "
                f"CERC class {ref.get('cerc_merit_class','?')}"
            )
    else:
        st.caption("No advisories yet.")

    time.sleep(5)
    st.rerun()


if __name__ == "__main__":
    main()

