"""
compliance_gate.py
Compliance gate between dispatch decision and SCADA output.
Applies simple ramp-rate and must-run checks and separates
approved vs held commands into different JSONL streams.
"""

import json
import os
from typing import Dict

from pathway_pipeline.config import DATA_DIR, HELD_JSONL, PLANT_MAP
from pathway_pipeline.document_store import get_store

# Simple per-plant ramp-rate limit in MW per decision interval
RAMP_LIMIT_MW: Dict[str, float] = {
    "RJ01": 25.0,
    "GJ01": 20.0,
    "TN01": 15.0,
}

# Minimal must-run floor in MW when regulations say "must-run"
MIN_MUST_RUN_MW: Dict[str, float] = {
    "RJ01": 20.0,
    "GJ01": 15.0,
    "TN01": 12.0,
}

_PREV_DISPATCH: Dict[str, Dict] = {}


def _rag_context_for(plant_id: str) -> str:
    """Lightweight RAG query used for compliance context."""
    store = get_store()
    chunks = store.query(
        f"ramp rate limits and must-run obligations for plant {plant_id}",
        top_k=3,
    )
    parts = [
        f"[{c.get('source','?')}] {c.get('text','').strip()}"
        for c in chunks
        if c.get("text")
    ]
    return "\n\n".join(parts) or "No regulatory context found."


def gate_dispatch(dispatch: Dict) -> Dict:
    """
    Apply compliance checks and return enriched dispatch:
    - status: 'approved' | 'held'
    - reason: explanation string
    - adjusted_mw: possibly adjusted MW value
    """
    plant_id = dispatch.get("plant_id")
    if not plant_id:
        return dispatch

    rag_ctx = _rag_context_for(plant_id)
    prev = _PREV_DISPATCH.get(plant_id)

    allocated = float(dispatch.get("allocated_mw", 0.0) or 0.0)
    status = "approved"
    reason = "All constraints satisfied"

    # Ramp-rate check
    if prev is not None:
        prev_mw = float(prev.get("allocated_mw", 0.0) or 0.0)
        ramp = abs(allocated - prev_mw)
        limit = RAMP_LIMIT_MW.get(plant_id, 999.0)
        if ramp > limit:
            status = "held"
            reason = (
                f"Ramp rate exceeded: {ramp:.1f}MW vs limit {limit:.1f}MW "
                "per decision interval"
            )
            if allocated >= prev_mw:
                allocated = prev_mw + limit
            else:
                allocated = prev_mw - limit

    # Must-run constraint from RAG context
    floor = MIN_MUST_RUN_MW.get(plant_id)
    if (
        status == "approved"
        and floor is not None
        and allocated < floor
        and "must-run" in rag_ctx.lower()
    ):
        status = "held"
        reason = "CERC must-run constraint violated"
        allocated = floor

    gated = {
        **dispatch,
        "status": status,
        "reason": reason,
        "adjusted_mw": round(allocated, 2),
        "rag_context_snippet": rag_ctx[:400],
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    if status == "held":
        with open(HELD_JSONL, "a") as f:
            f.write(json.dumps(gated) + "\n")

    _PREV_DISPATCH[plant_id] = gated
    return gated

