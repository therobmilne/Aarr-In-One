from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from backend.logging_config import get_logger

logger = get_logger("exceptions")


class MediaForgeError(Exception):
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(MediaForgeError):
    def __init__(self, resource: str, identifier: str | int):
        super().__init__(
            message=f"{resource} '{identifier}' not found",
            code="NOT_FOUND",
            status_code=404,
        )


class AuthenticationError(MediaForgeError):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message=message, code="AUTH_FAILED", status_code=401)


class PermissionError(MediaForgeError):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message=message, code="FORBIDDEN", status_code=403)


class ConfigurationError(MediaForgeError):
    def __init__(self, message: str):
        super().__init__(message=message, code="CONFIG_ERROR", status_code=500)


class ExternalServiceError(MediaForgeError):
    def __init__(self, service: str, message: str):
        super().__init__(
            message=f"{service}: {message}",
            code="EXTERNAL_SERVICE_ERROR",
            status_code=502,
        )


async def mediaforge_exception_handler(request: Request, exc: MediaForgeError) -> JSONResponse:
    logger.error("handled_error", code=exc.code, message=exc.message, path=str(request.url))
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "code": exc.code},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_error", path=str(request.url), error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "code": "INTERNAL_ERROR"},
    )
