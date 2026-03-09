from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from src.domain.exceptions import DomainException

logger = logging.getLogger(__name__)


async def domain_exception_handler(
    request: Request, exc: DomainException
) -> JSONResponse:
    logger.warning(
        "Domain error: %s (code=%s, status=%d)",
        exc.message,
        exc.error_code,
        exc.status_code,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message, "error_code": exc.error_code},
    )
