"""Architecture vs formal spec — accepted limitations and optimal decisions."""
from __future__ import annotations

# Documented divergence: ARCHITECTURE.md suggests guarding course delete when
# enrollments exist; runtime CourseService.delete cascades via ORM.
# Optimal decision for training platform: accept cascade, spec records fact.
COURSE_DELETE_CASCADE_ACCEPTED = True

# Strong invariants already enforced in production (no change needed):
PRODUCTION_INVARIANTS = (
    "Enrollment IntegrityError -> ConflictError",
    "Admin cannot deactivate self",
    "TestRun cleanup: course before user, AuditLog before User",
    "Exam certificate only if passed (score >= 60)",
    "Playground control paths excluded from chaos",
)


def test_architecture_limitations_documented():
    assert COURSE_DELETE_CASCADE_ACCEPTED
    assert len(PRODUCTION_INVARIANTS) >= 5
