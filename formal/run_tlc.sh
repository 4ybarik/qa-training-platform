#!/usr/bin/env bash
# Run TLC on all formal/tla/**/*.cfg specs.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TLA_DIR="$ROOT/formal/tla"
FAILED=0
PASSED=0

run_tlc() {
  local cfg="$1"
  local dir
  dir="$(dirname "$cfg")"
  local module
  module="$(basename "$cfg" .cfg)"
  local tla="$dir/$module.tla"
  if [[ ! -f "$tla" ]]; then
    echo "SKIP (no .tla): $cfg"
    return 0
  fi
  echo "TLC: $module"
  if command -v tlc &>/dev/null; then
    (cd "$dir" && tlc -config "$(basename "$cfg")" "$module.tla") && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
  elif command -v java &>/dev/null; then
    docker run --rm -v "$TLA_DIR:/tla" -w "/tla/${dir#$TLA_DIR/}" tlaplus/tlc \
      -config "$(basename "$cfg")" "$module.tla" && PASSED=$((PASSED + 1)) || FAILED=$((FAILED + 1))
  else
    echo "WARN: neither tlc nor java/docker available — skipping $module"
    return 0
  fi
}

while IFS= read -r -d '' cfg; do
  run_tlc "$cfg"
done < <(find "$TLA_DIR" -name '*.cfg' -print0)

echo "TLC summary: passed=$PASSED failed=$FAILED"
if [[ "$FAILED" -gt 0 ]]; then
  exit 1
fi
