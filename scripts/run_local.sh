#!/bin/bash
# Run RenewCast locally without Docker (for development).
set -e
echo "=== RenewCast Local Runner ==="

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "Created .env from .env.example  — edit it with your API keys"
fi

export $(cat .env | xargs)

mkdir -p data docs models

pip install -r requirements.pipeline.txt -q
pip install -r requirements.api.txt -q

echo "Starting API on port 8000..."
DATA_DIR=./data uvicorn api.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

sleep 2

echo "Starting pipeline..."
DATA_DIR=./data DOCS_DIR=./docs python pathway_pipeline/main.py

kill $API_PID 2>/dev/null || true
