"""Inventory coverage — every production symbol maps to a real formal spec."""
from collections import Counter
from pathlib import Path

from app.formal.inventory import (
    FORMAL_TLA,
    missing_spec_files,
    scan_app,
    write_coverage_report,
)


def test_inventory_has_symbols():
    inv = scan_app()
    assert inv.summary()["total"] > 100


def test_inventory_zero_unmapped():
    inv = scan_app()
    assert inv.summary()["unmapped"] == 0, inv.uncovered()[:20]


def test_inventory_zero_misc():
    """Adapter/API/web/services must not dump into the Misc catch-all."""
    inv = scan_app()
    misc = inv.misc()
    assert inv.summary()["misc"] == 0, [
        f"{s.module}:{s.name}->{s.spec}" for s in misc[:30]
    ]


def test_api_and_web_map_to_adapters():
    inv = scan_app()
    bad = [
        s
        for s in inv.symbols
        if (s.module.startswith("api.") or s.module.startswith("web."))
        and s.spec
        not in {
            "adapters/ApiAdapters.tla",
            "adapters/PracticeTargets.tla",
            "modules/Deps.tla",
            "modules/Errors.tla",
            "modules/Quality.tla",
            "modules/I18n.tla",
            "N/A",
        }
    ]
    assert bad == [], [
        f"{s.module}:{s.name} -> {s.spec}" for s in bad[:20]
    ]


def test_practice_and_integrations_map_to_practice_targets():
    inv = scan_app()
    targets = [
        s
        for s in inv.symbols
        if s.module.startswith("api.practice")
        or s.module.startswith("api.integrations")
    ]
    assert targets
    bad = [s for s in targets if s.spec != "adapters/PracticeTargets.tla"]
    assert bad == [], [f"{s.module}:{s.name} -> {s.spec}" for s in bad]


def test_service_methods_inherit_process_spec():
    inv = scan_app()
    enroll = next(
        s
        for s in inv.symbols
        if s.name == "enroll" and s.owner == "CourseService"
    )
    assert enroll.spec == "services/CourseLifecycle.tla"
    submit = next(
        s
        for s in inv.symbols
        if s.name == "submit" and s.owner == "ExamService"
    )
    assert submit.spec == "services/ExamAttempt.tla"


def test_all_referenced_specs_exist_on_disk():
    inv = scan_app()
    missing = missing_spec_files(inv)
    assert missing == [], f"Missing TLA files: {missing}"


def test_coverage_report_writes_and_is_healthy():
    repo = Path(__file__).resolve().parents[3]
    out = repo / "formal" / "coverage.json"
    report = write_coverage_report(out)
    summary = report["summary"]
    assert summary["unmapped"] == 0
    assert summary["misc"] == 0
    assert report["missing_specs"] == []
    assert out.exists()
    by_spec = report["by_spec"]
    assert by_spec["adapters/ApiAdapters.tla"] > 50
    assert by_spec["adapters/PracticeTargets.tla"] > 10
    # No silent Misc dump
    assert "modules/Misc.tla" not in by_spec


def test_spec_distribution_has_expected_buckets():
    inv = scan_app()
    specs = Counter(s.spec for s in inv.symbols)
    for required in (
        "adapters/ApiAdapters.tla",
        "adapters/PracticeTargets.tla",
        "domain/Entities.tla",
        "domain/Types.tla",
        "services/AuthAccount.tla",
        "services/CourseLifecycle.tla",
        "services/ExamAttempt.tla",
        "services/Learning.tla",
        "core/RateLimiter.tla",
        "middleware/Playground.tla",
    ):
        assert specs[required] > 0, f"Expected symbols for {required}"
    assert (FORMAL_TLA / "adapters" / "ApiAdapters.tla").exists()
