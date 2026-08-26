import pytest

from app.formal.machines.auth_account import AuthAccountMachine
from app.formal.machines.admin_user import AdminUserMachine, Role
from app.formal.machines.course_lifecycle import CourseLifecycleMachine, EnrollmentMachine
from app.formal.machines.exam_attempt import ExamAttemptMachine, PASS_THRESHOLD
from app.formal.machines.notification import NotificationMachine
from app.formal.machines.playground import PlaygroundMachine, CONTROL_PATHS
from app.formal.machines.practice_job import PracticeJobMachine, JobStatus
from app.formal.machines.rate_limiter import RateLimiterMachine
from app.formal.machines.test_run import TestRunMachine as TestRunOracle


class TestAuthAccountMachine:
    def test_register_then_login(self):
        m = AuthAccountMachine()
        assert m.current_state.id == "absent"
        m.register()
        assert m.current_state.id == "active"
        m.login_success()
        assert m.tokens_issued == 1
        assert m.login_hits_within_window

    def test_deactivate_forbids_new_tokens(self):
        m = AuthAccountMachine()
        m.register()
        m.deactivate()
        assert m.current_state.id == "inactive"
        assert m.inactive_cannot_issue_tokens

    def test_login_hits_exceed_max_raises(self):
        m = AuthAccountMachine(max_login_attempts=2)
        m.register()
        m.login_success()
        m.login_success()
        with pytest.raises(ValueError, match="LoginHitsWithinWindow"):
            m.on_login_success()


class TestCourseLifecycle:
    def test_publish_and_archive(self):
        m = CourseLifecycleMachine()
        m.publish()
        assert m.current_state.id == "published"
        m.archive()
        assert m.current_state.id == "archived"

    def test_enrollment_idempotent(self):
        e = EnrollmentMachine()
        e.try_enroll(1, 10)
        assert e.current_state.id == "enrolled"
        e.try_enroll(1, 10)
        assert e.progress_in_0_to_100


class TestExamAttempt:
    def test_passed_iff_score_ge_threshold(self):
        m = ExamAttemptMachine()
        m.set_enrollment()
        m.submit_exam(PASS_THRESHOLD)
        assert m.passed_iff_score_ge_60
        assert m.certificate_only_if_passed
        assert m.progress == 100

    def test_fail_no_certificate(self):
        m = ExamAttemptMachine()
        m.submit_exam(PASS_THRESHOLD - 1)
        assert not m.passed
        assert m.certificate_url is None


class TestNotification:
    def test_mark_read_owner_only(self):
        n = NotificationMachine(owner_id=1)
        n.mark_read_for(1)
        assert n.current_state.id == "read"

    def test_cross_user_forbidden(self):
        n = NotificationMachine(owner_id=1)
        with pytest.raises(PermissionError, match="NoCrossUserMutation"):
            n.mark_read_for(2)


class TestAdminUser:
    def test_only_admin_sets_role(self):
        m = AdminUserMachine(Role.ADMIN, actor_id=1, target_id=2)
        m.set_role(Role.MANAGER)
        assert m.target_role == Role.MANAGER

    def test_non_admin_forbidden(self):
        m = AdminUserMachine(Role.USER, actor_id=1, target_id=2)
        with pytest.raises(PermissionError, match="OnlyAdminMutatesUsers"):
            m.set_role(Role.ADMIN)

    def test_self_deactivate_forbidden(self):
        m = AdminUserMachine(Role.ADMIN, actor_id=1, target_id=1)
        with pytest.raises(PermissionError, match="ActorCannotDeactivateSelf"):
            m.set_active(False)


class TestTestRunOracle:
    def test_cleanup_course_before_user(self):
        t = TestRunOracle()
        t.track_create("user")
        t.track_create("course")
        t.run_cleanup()
        assert t.course_before_user


class TestPracticeJob:
    def test_pending_to_completed(self):
        j = PracticeJobMachine(polls_to_complete=2)
        assert j.poll() == JobStatus.PENDING
        assert j.poll() == JobStatus.COMPLETED
        assert j.terminal_is_stable

    def test_never_complete_mutation(self):
        j = PracticeJobMachine(polls_to_complete=1, never_complete=True)
        j.poll()
        j.poll()
        assert j.current_state.id == "pending"


class TestRateLimiter:
    def test_hits_within_window(self):
        r = RateLimiterMachine(max_attempts=2)
        assert r.try_hit("k")
        assert r.try_hit("k")
        assert not r.try_hit("k")
        assert r.hits_never_exceed_max_inside_window


class TestPlayground:
    def test_control_paths_never_chaosed(self):
        p = PlaygroundMachine()
        p.enable_probabilistic()
        for path in CONTROL_PATHS:
            assert not p.apply_chaos(path)
        assert p.apply_chaos("/api/courses")
        assert p.control_paths_never_chaosed
