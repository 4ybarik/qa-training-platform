#!/usr/bin/env python3
"""Run TLC on all formal/tla/**/*.cfg specs (cross-platform)."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TLA_DIR = ROOT / "formal" / "tla"
DEFAULT_TIMEOUT_SECONDS = 30


def _tla2tools_jar() -> Path | None:
    configured = os.getenv("TLA2TOOLS_JAR")
    candidates = [Path(configured)] if configured else []
    candidates.append(ROOT / "formal" / ".tools" / "tla2tools.jar")
    return next((path.resolve() for path in candidates if path.is_file()), None)


def run_tlc(cfg: Path) -> bool:
    module = cfg.stem
    tla = cfg.parent / f"{module}.tla"
    if not tla.exists():
        print(f"SKIP (no .tla): {cfg}")
        return True
    print(f"TLC: {module}")
    with tempfile.TemporaryDirectory(prefix=f"qatp-tlc-{module}-") as metadir:
        tlc_args = [
            "-cleanup", "-noGenerateSpecTE", "-metadir", metadir,
            "-config", cfg.name, f"{module}.tla",
        ]
        if shutil.which("tlc"):
            cmd = ["tlc", *tlc_args]
        elif shutil.which("java") and (jar := _tla2tools_jar()):
            cmd = ["java", "-XX:+UseParallelGC", "-jar", str(jar), *tlc_args]
        else:
            print(
                "ERROR: TLC is unavailable. Install the `tlc` command or set "
                "TLA2TOOLS_JAR to an official tla2tools.jar release.",
                file=sys.stderr,
            )
            return False
        timeout = int(os.getenv("TLC_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
        try:
            result = subprocess.run(
                cmd,
                cwd=cfg.parent,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"  FAIL: {module} exceeded {timeout}s", file=sys.stderr)
            return False
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return False
    print(f"  OK: {module}")
    return True


def main() -> int:
    passed = failed = 0
    for cfg in sorted(TLA_DIR.rglob("*.cfg")):
        if run_tlc(cfg):
            passed += 1
        else:
            failed += 1
    print(f"TLC summary: passed={passed} failed={failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
