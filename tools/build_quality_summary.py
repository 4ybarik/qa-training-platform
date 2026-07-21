"""Собирает единый результат CI и добавляет его в постоянную историю."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from html import escape
import json
import os
from pathlib import Path
import time
import xml.etree.ElementTree as ET


def _junit(artifacts: Path) -> tuple[dict[str, int], list[str]]:
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    defects: list[str] = []
    for path in artifacts.rglob("*junit*.xml"):
        root = ET.parse(path).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
        for suite in suites:
            for key in totals:
                totals[key] += int(float(suite.attrib.get(key, 0)))
            for case in suite.findall(".//testcase"):
                if case.find("failure") is not None or case.find("error") is not None:
                    defects.append(f"{case.attrib.get('classname', '')}::{case.attrib.get('name', '')}")
    return totals, sorted(set(defects))


def _mutation(artifacts: Path) -> dict:
    path = artifacts / "mutation-score.json"
    if not path.exists():
        return {"score": None, "mutations_total": 0, "mutations_killed": 0, "outcomes": []}
    return json.loads(path.read_text(encoding="utf-8"))


def _performance(artifacts: Path) -> dict:
    candidates = list(artifacts.rglob("*_stats.csv"))
    if not candidates:
        return {"p95_ms": None, "requests": 0, "failures": 0}
    with candidates[0].open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    row = next((item for item in rows if item.get("Name") == "Aggregated"), rows[-1])
    return {
        "p95_ms": int(float(row.get("95%", 0) or 0)),
        "requests": int(float(row.get("Request Count", 0) or 0)),
        "failures": int(float(row.get("Failure Count", 0) or 0)),
    }


def _html(entries: list[dict]) -> str:
    rows = []
    for item in reversed(entries[-100:]):
        mutation = item["mutation"].get("score")
        rows.append(
            "<tr>"
            f"<td>{escape(str(item['build']))}</td>"
            f"<td>{escape(item['branch'])}</td>"
            f"<td><code>{escape(item['commit'][:12])}</code></td>"
            f"<td>{item['tests']['tests']}</td>"
            f"<td>{item['tests']['failures'] + item['tests']['errors']}</td>"
            f"<td>{'—' if mutation is None else f'{mutation * 100:.1f}%'}</td>"
            f"<td>{item['performance']['p95_ms'] or '—'}</td>"
            f"<td>{item['duration_seconds']}</td>"
            "</tr>"
        )
    return """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>QA Training quality history</title>
<style>body{font-family:system-ui;margin:2rem;background:#f6f8fb;color:#172033}
table{border-collapse:collapse;width:100%;background:#fff}th,td{padding:.65rem;border:1px solid #d9dfeb;text-align:left}
th{background:#eef2f8}code{font-size:.85rem}</style></head><body>
<h1>История качества автотестов</h1><table><thead><tr><th>Build</th><th>Branch</th><th>Commit</th>
<th>Tests</th><th>Defects</th><th>Mutation score</th><th>p95 ms</th><th>Seconds</th></tr></thead>
<tbody>""" + "".join(rows) + "</tbody></table></body></html>"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", default="ci-artifacts")
    parser.add_argument("--history", default=os.getenv("QUALITY_HISTORY_DIR", "quality-history"))
    parser.add_argument("--started-at", type=int, default=int(os.getenv("CI_STARTED_AT", time.time())))
    args = parser.parse_args()
    artifacts = Path(args.artifacts)
    history = Path(args.history)
    artifacts.mkdir(parents=True, exist_ok=True)
    history.mkdir(parents=True, exist_ok=True)
    tests, defects = _junit(artifacts)
    mutation = _mutation(artifacts)
    summary = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "build": os.getenv("BUILD_NUMBER", "local"),
        "branch": os.getenv("BRANCH_NAME", os.getenv("GIT_BRANCH", "local")),
        "commit": os.getenv("GIT_COMMIT", "local-working-tree"),
        "duration_seconds": max(int(time.time()) - args.started_at, 0),
        "tests": tests,
        "stability": {
            "runs": int(os.getenv("STABILITY_RUNS", "1")),
            "passed": tests["failures"] == 0 and tests["errors"] == 0,
        },
        "mutation": mutation,
        "performance": _performance(artifacts),
        "detected_defects": defects,
    }
    (artifacts / "quality-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    history_file = history / "history.jsonl"
    with history_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, ensure_ascii=False) + "\n")
    entries = [json.loads(line) for line in history_file.read_text(encoding="utf-8").splitlines() if line]
    (history / "index.html").write_text(_html(entries), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
