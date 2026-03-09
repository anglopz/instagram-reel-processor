from __future__ import annotations


class DomainException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = 400,
        error_code: str = "DOMAIN_ERROR",
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message)


class TaskNotFound(DomainException):
    def __init__(self, task_id: str | None = None) -> None:
        message = f"Task not found: {task_id}" if task_id else "Task not found"
        super().__init__(message, status_code=404, error_code="TASK_NOT_FOUND")


class InvalidURL(DomainException):
    def __init__(self, url: str | None = None) -> None:
        message = f"Invalid reel URL: {url}" if url else "Invalid reel URL"
        super().__init__(message, status_code=422, error_code="INVALID_URL")


class PipelineError(DomainException):
    def __init__(self, step: str, detail: str) -> None:
        message = f"Pipeline failed at {step}: {detail}"
        super().__init__(message, status_code=500, error_code="PIPELINE_ERROR")


class Unauthorized(DomainException):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, status_code=401, error_code="UNAUTHORIZED")


class TaskAlreadyTerminal(DomainException):
    def __init__(self, status: str) -> None:
        message = f"Task is already in terminal state: {status}"
        super().__init__(message, status_code=409, error_code="TASK_ALREADY_TERMINAL")
