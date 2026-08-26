"""Inventory coverage — every production symbol maps to a formal spec."""
from app.formal.inventory import scan_app, write_coverage_report


def test_inventory_has_symbols():
    inv = scan_app()
    assert inv.summary()["total"] > 100


def test_inventory_low_unmapped():
    inv = scan_app()
    summary = inv.summary()
    unmapped_ratio = summary["unmapped"] / summary["total"]
    assert unmapped_ratio < 0.05, f"Too many unmapped: {inv.uncovered()[:10]}"


def test_coverage_report_writes():
    from pathlib import Path

    repo = Path(__file__).resolve().parents[3]
    out = repo / "formal" / "coverage.json"
    report = write_coverage_report(out)
    assert "summary" in report
    assert out.exists()
