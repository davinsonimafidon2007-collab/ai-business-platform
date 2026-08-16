"""Standardized error response schema for the entire API.

All error responses MUST follow this format:

    {
      "success": false,
      "error": {
          "code": "...",
          "message": "...",
          "request_id": "...",
          "details": ...   // optional, null by default
      }
    }

This guarantees a consistent error contract consumed by all clients.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """The inner `error` object of a standardized error response."""

    code: str = Field(..., description="Machine-readable error code (e.g. 'not_found', 'validation_error')")
    message: str = Field(..., description="Human-readable error message")
    request_id: str | None = Field(None, description="Unique request identifier for tracing")
    details: Any = Field(None, description="Additional error details (optional)")


class ErrorResponse(BaseModel):
    """Standardized error response envelope.

    Every error response returned by the API MUST use this schema.
    """

    success: bool = Field(False, description="Always false for error responses")
    error: ErrorDetail = Field(..., description="Error details")

