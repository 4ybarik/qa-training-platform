#!/usr/bin/env bash
# Compatibility wrapper; the Python runner is the single source of truth.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$ROOT/formal/run_tlc.py"
