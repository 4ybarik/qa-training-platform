"""Доменные исключения. API-слой переводит их в HTTP-коды."""


class DomainError(Exception):
    """Базовая доменная ошибка."""


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class AuthError(DomainError):
    pass


class PermissionError_(DomainError):
    pass


class RateLimitError(DomainError):
    pass
