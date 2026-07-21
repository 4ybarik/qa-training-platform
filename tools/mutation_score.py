"""Запускает ученические тесты против исправного стенда и выбранных мутаций."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def _run(tests: list[str], mutation: str | None) -> dict:
    env = os.environ.copy()
    if mutation:
        env["TEST_MUTATION"] = mutation
    else:
        env.pop("TEST_MUTATION", None)
    started = time.monotonic()
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *tests],
        env=env,
        check=False,
    )
    return {
        "returncode": completed.returncode,
        "duration_seconds": round(time.monotonic() - started, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="student_tests/mutations.json")
    parser.add_argument("--output", default="ci-artifacts/mutation-score.json")
    parser.add_argument("--skip-baseline", action="store_true")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    mutations = config.get("mutations", [])
    if not mutations:
        raise SystemExit("mutation config must contain at least one mutation")
    ids = [mutation.get("id") for mutation in mutations]
    if any(not item for item in ids) or len(set(ids)) != len(ids):
        raise SystemExit("mutation ids must be non-empty and unique")
    if any(not mutation.get("tests") for mutation in mutations):
        raise SystemExit("each mutation must define at least one test path")
    missing = sorted({
        path
        for mutation in mutations
        for path in mutation.get("tests", [])
        if not Path(path).is_file()
    })
    if missing:
        raise SystemExit(f"mutation config references missing tests: {', '.join(missing)}")
    minimum_score = float(config.get("minimum_score", 1.0))
    if not 0 <= minimum_score <= 1:
        raise SystemExit("minimum_score must be between 0 and 1")
    all_tests = sorted({path for mutation in mutations for path in mutation["tests"]})
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    baseline = {"returncode": 0, "duration_seconds": 0.0}
    if not args.skip_baseline:
        baseline = _run(all_tests, None)
        if baseline["returncode"] != 0:
            result = {"baseline": baseline, "score": 0.0, "error": "baseline_failed"}
            output.write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return baseline["returncode"]

    outcomes = []
    for mutation in mutations:
        run = _run(mutation["tests"], mutation["id"])
        outcomes.append({
            "id": mutation["id"],
            "killed": run["returncode"] != 0,
            **run,
        })
    killed = sum(item["killed"] for item in outcomes)
    score = killed / len(outcomes) if outcomes else 0.0
    result = {
        "baseline": baseline,
        "mutations_total": len(outcomes),
        "mutations_killed": killed,
        "mutations_survived": len(outcomes) - killed,
        "score": round(score, 4),
        "minimum_score": minimum_score,
        "outcomes": outcomes,
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if score >= result["minimum_score"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
