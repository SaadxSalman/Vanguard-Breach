"""Optional API-key protection for the Vanguard console."""
from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .config import get_settings


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()
        if not settings.auth_enabled or request.url.path in {"/api/health", "/"}:
            return await call_next(request)
        supplied = request.headers.get("X-API-Key") or request.query_params.get("key")
        if supplied != settings.api_key:
            return JSONResponse(status_code=401, content={
                "detail": "Invalid or missing X-API-Key (see VANGUARD_API_KEY in .env)"})
        return await call_next(request)
