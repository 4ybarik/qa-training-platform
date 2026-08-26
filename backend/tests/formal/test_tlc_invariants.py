"""Programmatic invariant verification — TLC surrogate when Java/Docker unavailable."""
from __future__ import annotations

import itertools

import pytest

from app.domain.errors import ConflictError
from app.formal.machines.admin_user import AdminUserMachine, Role
from app.formal.machines.auth_account import AuthAccountMachine
from app.formal.machines.course_lifecycle import EnrollmentMachine
from app.formal.machines.exam_attempt import ExamAttemptMachine, PASS_THRESHOLD
from app.formal.machines.notification import NotificationMachine
from app.formal.machines.playground import PlaygroundMachine, CONTROL_PATHS
from app.formal.machines.practice_job import PracticeJobMachine
from app.formal.machines.rate_limiter import RateLimiterMachine
from app.formal.machines.test_run import TestRunMachine


class TestAuthAccountInvariants:
    def test_email_unique_register_once(self):
        m = AuthAccountMachine()
        m.register()
        assert m.email_unique

    def test_login_hits_within_window(self):
        m = AuthAccountMachine(max_login_attempts=3)
        m.register()
        for _ in range(3):
            m.login_success()
        assert m.login_hits_within_window
        with pytest.raises(ValueError):
            m.on_login_success()

    def test_inactive_cannot_issue_tokens(self):
        m = AuthAccountMachine()
        m.register()
        m.deactivate()
        assert m.inactive_cannot_issue_tokens


class TestEnrollmentInvariants:
    def test_at_most_one_enrollment(self):
        e = EnrollmentMachine()
        e.try_enroll(1, 1)
        e.try_enroll(1, 1)
        assert e.at_most_one_enrollment_per_user_course

    def test_progress_bounds(self):
        e = EnrollmentMachine()
        e.try_enroll(1, 1)
        for p in range(0, 101, 10):
            e.update_progress(p)
        assert e.progress_in_0_to_100

    def test_archived_course_forbidden(self):
        e = EnrollmentMachine()
        with pytest.raises(ConflictError, match="архив"):
            e.try_enroll(1, 1, course_status="ARCHIVED")


class TestExamAttemptInvariants:
    @pytest.mark.parametrize("score", [0, 30, 59, 60, 100])
    def test_passed_iff_score_ge_60(self, score: int):
        m = ExamAttemptMachine()
        m.submit_exam(score)
        assert m.passed_iff_score_ge_60
        assert m.certificate_only_if_passed

    def test_progress_monotonic_with_enrollment(self):
        m = ExamAttemptMachine()
        m.set_enrollment()
        m.submit_exam(40)
        m.submit_exam(50)
        assert m.progress >= 40
        assert m.progress_monotonic


class TestNotificationInvariants:
    def test_no_cross_user_mutation(self):
        n = NotificationMachine(owner_id=1)
        with pytest.raises(PermissionError):
            n.mark_read_for(2)
        with pytest.raises(PermissionError):
            n.delete_for(2)


class TestAdminUserInvariants:
    def test_only_admin_mutates(self):
        m = AdminUserMachine(Role.USER, 1, 2)
        with pytest.raises(PermissionError, match="OnlyAdminMutatesUsers"):
            m.set_role(Role.ADMIN)

    def test_actor_cannot_deactivate_self(self):
        m = AdminUserMachine(Role.ADMIN, 1, 1)
        with pytest.raises(PermissionError, match="ActorCannotDeactivateSelf"):
            m.set_active(False)


class TestTestRunInvariants:
    def test_cleanup_order(self):
        for perm in itertools.permutations(["course", "user"]):
            t = TestRunMachine()
            for et in perm:
                t.track_create(et)
            t.run_cleanup()
            assert t.cleanup_deletes_tracked_only
            assert t.course_before_user


class TestPracticeJobInvariants:
    def test_terminal_is_stable(self):
        j = PracticeJobMachine(polls_to_complete=2)
        j.poll()
        j.poll()
        assert j.terminal_is_stable
        j.poll()
        assert j.terminal_is_stable


class TestRateLimiterInvariants:
    def test_hits_never_exceed_max(self):
        r = RateLimiterMachine(max_attempts=3)
        for _ in range(5):
            r.try_hit("k")
        assert r.hits_never_exceed_max_inside_window


class TestPlaygroundInvariants:
    def test_control_paths_never_chaosed(self):
        p = PlaygroundMachine()
        p.enable_probabilistic()
        for path in CONTROL_PATHS:
            p.apply_chaos(path)
        p.apply_chaos("/api/courses/1")
        assert p.control_paths_never_chaosed
