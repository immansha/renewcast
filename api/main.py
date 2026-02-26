"""
api/main.py — FastAPI Read Layer
Serves the three JSONL output streams as REST endpoints + SSE live stream.
"""

import asyncio, json, os
from dotenv import load_dotenv

load_dotenv()
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

DATA_DIR = os.environ.get("DATA_DIR", "/app/data")

app = FastAPI(title="RenewCast Grid Intelligence API", version="4.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])


def _read_jsonl(filename: str, last_n: int = 20) -> list:
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows[-last_n:]


@app.get("/")
def root():
    return {"service": "RenewCast Grid Intelligence API", "version": "4.0.0",
            "endpoints": ["/dispatch", "/advisories", "/anomalies",
                          "/telemetry", "/status", "/stream/dispatch"]}

@app.get("/dispatch")
def get_dispatch(n: int = Query(20, ge=1, le=200)):
    return _read_jsonl("dispatch_commands.jsonl", n)

@app.get("/advisories")
def get_advisories(n: int = Query(10, ge=1, le=100)):
    return _read_jsonl("operator_advisory.jsonl", n)

@app.get("/anomalies")
def get_anomalies(n: int = Query(10, ge=1, le=100)):
    return _read_jsonl("anomaly_reports.jsonl", n)

@app.get("/telemetry")
def get_telemetry(n: int = Query(30, ge=1, le=300)):
    return _read_jsonl("telemetry_stream.jsonl", n)

@app.get("/status")
def get_status():
    def count(fname):
        p = os.path.join(DATA_DIR, fname)
        if not os.path.exists(p):
            return 0
        with open(p) as f:
            return sum(1 for line in f if line.strip())
    return {
        "status": "running",
        "records": {
            "dispatch_commands":  count("dispatch_commands.jsonl"),
            "operator_advisories": count("operator_advisory.jsonl"),
            "anomaly_reports":    count("anomaly_reports.jsonl"),
            "telemetry_rows":     count("telemetry_stream.jsonl"),
        }
    }

@app.get("/stream/dispatch")
async def stream_dispatch():
    """Server-Sent Events — pushes new dispatch commands in real time."""
    dispatch_file = os.path.join(DATA_DIR, "dispatch_commands.jsonl")

    async def generator():
        cursor = os.path.getsize(dispatch_file) if os.path.exists(dispatch_file) else 0
        while True:
            await asyncio.sleep(2)
            if not os.path.exists(dispatch_file):
                continue
            with open(dispatch_file) as f:
                f.seek(cursor)
                new_lines = f.readlines()
                cursor = f.tell()
            for line in new_lines:
                line = line.strip()
                if line:
                    yield f"data: {line}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache"})
