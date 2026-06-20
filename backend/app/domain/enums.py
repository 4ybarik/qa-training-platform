"""Перечисления предметной области."""
import enum


class Role(str, enum.Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    USER = "USER"


class CourseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class QuestionType(str, enum.Enum):
    SINGLE = "SINGLE"      # одиночный выбор
    MULTI = "MULTI"        # множественный выбор
    TEXT = "TEXT"          # текстовый ответ
    DND = "DND"            # перетаскивание (drag and drop)


class NotificationStatus(str, enum.Enum):
    UNREAD = "UNREAD"
    READ = "READ"
