"""
Request / response logging middleware.

Logs every incoming request and its response status code + processing time.
Uses Python's standard `logging` module so output integrates with any
log aggregator (stdout/stderr, file, etc.).
"""

import logging
import time
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("api.access")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Starlette middleware that instruments every HTTP request with:
    - A unique request ID (X-Request-ID header)
    - Method, path, query params
    - Response status code
    - Wall-clock processing time in milliseconds
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Generate a unique ID for correlation across log lines
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        start_time = time.perf_counter()

        logger.info(
            "Incoming request | id=%s method=%s path=%s query=%s client=%s",
            request_id,
            request.method,
            request.url.path,
            str(request.query_params) or "-",
            request.client.host if request.client else "unknown",
        )

        response: Response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "Completed request | id=%s status=%d duration=%.2fms",
            request_id,
            response.status_code,
            elapsed_ms,
        )

        # Propagate the request ID to the client for debugging
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.2f}"

        return response
