#!/usr/bin/env bash
set -euo pipefail
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python scripts/fetch_model.py --output models/TinyLlama-1.1B-Chat-q4_k_m.gguf
