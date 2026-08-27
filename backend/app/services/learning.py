"""Сохранение попыток и расчёт доказуемого прогресса практики."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.enums import Role
from app.domain.models import PracticeCriterionResult, PracticeProgress, PracticeRun, User
from app.learning.grading import Grade
from app.practice.catalog import CHALLENGES


class LearningService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record_grade(
        self,
        user_id: int,
        challenge_slug: str,
        file_path: str,
        source_path: Path,
        grade: Grade,
    ) -> PracticeRun:
        source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        run = PracticeRun(
            user_id=user_id,
            challenge_slug=challenge_slug,
            file_path=file_path,
            source_hash=source_hash,
            exit_code=grade.baseline.exit_code,
            duration_ms=grade.baseline.duration_ms,
            tests_collected=grade.baseline.tests_collected,
            tests_passed=grade.baseline.tests_passed,
            tests_failed=grade.baseline.tests_failed,
            score=grade.score,
            passed=grade.passed,
            output=grade.baseline.output,
        )
        run.criteria = [
            PracticeCriterionResult(
                position=position,
                code=item.code,
                title=item.title,
                passed=item.passed,
                details=item.details,
            )
            for position, item in enumerate(grade.criteria)
        ]
        self.db.add(run)
        self.db.flush()

        progress = self.db.scalar(select(PracticeProgress).where(
            PracticeProgress.user_id == user_id,
            PracticeProgress.challenge_slug == challenge_slug,
        ))
        if progress is None:
            progress = PracticeProgress(user_id=user_id, challenge_slug=challenge_slug)
            self.db.add(progress)
        progress.attempts = (progress.attempts or 0) + 1
        progress.best_score = max(progress.best_score or 0, grade.score)
        progress.last_run_id = run.id
        progress.updated_at = datetime.now(timezone.utc)
        if grade.passed:
            progress.completed = True
            progress.completed_at = progress.completed_at or datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(run)
        return run

    def progress_map(self, user_id: int) -> dict[str, PracticeProgress]:
        items = self.db.scalars(
            select(PracticeProgress).where(PracticeProgress.user_id == user_id)
        ).all()
        return {item.challenge_slug: item for item in items}

    def summary(self, user_id: int) -> dict[str, int]:
        progress = self.progress_map(user_id)
        total = len(CHALLENGES)
        started = sum(item.attempts > 0 for item in progress.values())
        completed = sum(item.completed for item in progress.values())
        return {
            "total": total,
            "started": started,
            "completed": completed,
            "completion_percent": round(completed / total * 100) if total else 0,
        }

    def runs(self, user_id: int, limit: int = 50) -> list[PracticeRun]:
        return list(self.db.scalars(
            select(PracticeRun)
            .options(selectinload(PracticeRun.criteria))
            .where(PracticeRun.user_id == user_id)
            .order_by(PracticeRun.created_at.desc(), PracticeRun.id.desc())
            .limit(limit)
        ).all())

    def learner_overview(self) -> list[dict]:
        users = self.db.scalars(
            select(User).where(User.role == Role.USER).order_by(User.email)
        ).all()
        progress = self.db.scalars(select(PracticeProgress)).all()
        by_user: dict[int, list[PracticeProgress]] = {}
        for item in progress:
            by_user.setdefault(item.user_id, []).append(item)
        total = len(CHALLENGES)
        return [
            {
                "user_id": user.id,
                "email": user.email,
                "name": f"{user.first_name} {user.last_name}".strip(),
                "started": sum(item.attempts > 0 for item in by_user.get(user.id, [])),
                "completed": sum(item.completed for item in by_user.get(user.id, [])),
                "total": total,
                "completion_percent": round(
                    sum(item.completed for item in by_user.get(user.id, [])) / total * 100
                ) if total else 0,
            }
            for user in users
        ]


def serialize_progress(item: PracticeProgress | None) -> dict:
    if item is None:
        return {"attempts": 0, "best_score": 0, "completed": False, "last_run_id": None}
    return {
        "attempts": item.attempts,
        "best_score": item.best_score,
        "completed": item.completed,
        "last_run_id": item.last_run_id,
        "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        "completed_at": item.completed_at.isoformat() if item.completed_at else None,
    }


def serialize_run(run: PracticeRun) -> dict:
    return {
        "id": run.id,
        "challenge_slug": run.challenge_slug,
        "file_path": run.file_path,
        "exit_code": run.exit_code,
        "duration_ms": run.duration_ms,
        "tests_collected": run.tests_collected,
        "tests_passed": run.tests_passed,
        "tests_failed": run.tests_failed,
        "score": run.score,
        "passed": run.passed,
        "output": run.output,
        "created_at": run.created_at.isoformat(),
        "criteria": [
            {
                "code": item.code,
                "title": item.title,
                "passed": item.passed,
                "details": item.details,
            }
            for item in run.criteria
        ],
    }
