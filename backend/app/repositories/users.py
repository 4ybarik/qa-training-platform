"""Репозитории доступа к данным пользователей."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.models import Profile, User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def list_all(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(User.id)))

    def add(self, user: User) -> User:
        self.db.add(user)
        self.db.flush()
        return user

    def save(self) -> None:
        self.db.commit()


class ProfileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_user(self, user_id: int) -> Profile | None:
        return self.db.scalar(select(Profile).where(Profile.user_id == user_id))

    def add(self, profile: Profile) -> Profile:
        self.db.add(profile)
        self.db.flush()
        return profile
