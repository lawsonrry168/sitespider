#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true
source scripts/gsc-env.sh
python scripts/gsc-authorize.py
