#!/usr/bin/env python3
"""Run TLC on all formal/tla/**/*.cfg specs (cross-platform)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TLA_DIR = ROOT / "formal" / "tla"


def run_tlc(cfg: Path) -> bool:
    module = cfg.stem
    tla = cfg.parent / f"{module}.tla"
    if not tla.exists():
        print(f"SKIP (no .tla): {cfg}")
        return True
    print(f"TLC: {module}")
    rel_dir = cfg.parent.relative_to(TLA_DIR)
    if shutil.which("tlc"):
        cmd = ["tlc", "-config", cfg.name, f"{module}.tla"]
        cwd = cfg.parent
    elif shutil.which("java"):
        mount = TLA_DIR.resolve()
        inner = f"/tla/{rel_dir.as_posix()}" if str(rel_dir) != "." else "/tla"
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{mount}:{inner}",
            "-w", inner,
            "tlaplus/tlc",
            "-config", cfg.name,
            f"{module}.tla",
        ]
        cwd = None
    else:
        print(f"WARN: no tlc/java/docker — skipping {module}")
        return True
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
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
