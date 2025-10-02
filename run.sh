#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
python -m room_extractor --config config.yaml "$@"
