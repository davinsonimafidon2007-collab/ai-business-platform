"""Gemini Vision provider for vehicle inspection photo analysis.

Implements the VisionProvider protocol to analyze vehicle damage
from photographs using Google's Gemini vision-capable models.

Architecture note:
    This provider mirrors the OpenAIVisionProvider interface so the app
    can switch between providers by changing GEMINI_API_KEY / OPENAI_API_KEY
    in .env. Both providers share the VisionProvider protocol.
"""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import Any

import httpx

from app.models.vision import (
    VisionConfidence,
    VisionImage,
    VisionInspectionResult,
    VisionObservation,
    VisionSeverity,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt (same as OpenAI provider for consistency)
# ---------------------------------------------------------------------------

DAMAGE_ANALYSIS_PROMPT = """You are an expert vehicle damage assessor.
Analyze the provided vehicle photographs and return a **valid JSON** object (no markdown, no code fences).

For each photo, identify visible defects and return them in this exact structure:

{
  "observations": [
    {
      "photo_id": "<id of the photo>",
      "status": "GOOD" | "WARNING" | "BAD",
      "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
      "confidence": "LOW" | "MEDIUM" | "HIGH",
      "notes": "Clear description of the defect in Spanish (max 200 chars)",
      "suggested_repair_cost": <float | null>
    }
  ],
  "summary": "Global summary in Spanish (max 300 chars)"
}

Rules:
- status=GOOD → no visible defect; severity=LOW; suggested_repair_cost=null
- status=WARNING → minor cosmetic defect; severity=MEDIUM or LOW
- status=BAD → structural or safety-relevant defect; severity=HIGH or CRITICAL
- For GOOD photos, DO NOT include them in observations (skip them).
- Only include observations for photos WITH defects.
- suggested_repair_cost must be a realistic estimate in EUR based on European market prices.
- If you cannot determine a repair cost, set it to null.
- confidence reflects how sure you are about the detection.
"""

# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class GeminiVisionProvider:
    """Analyzes vehicle photos using Google Gemini vision models.

    Args:
        api_key: Google AI API key (GEMINI_API_KEY).
        model: Gemini model name (default: 'gemini-2.0-flash').
        max_tokens: Maximum tokens for the response (default: 2000).
        temperature: Sampling temperature (default: 0.1).
        http_client: Optional pre-configured httpx.AsyncClient.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        max_tokens: int = 2000,
        temperature: float = 0.1,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required")

        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._http_client = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    @property
    def _base_url(self) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{self._model}"

    # ------------------------------------------------------------------
    # Public API (VisionProvider protocol)
    # ------------------------------------------------------------------

    async def analyze_images(
        self, images: list[VisionImage]
    ) -> VisionInspectionResult:
        if not images:
            return VisionInspectionResult(
                observations=[], summary="No se proporcionaron imagenes."
            )

        parts: list[dict[str, Any]] = [
            {"text": DAMAGE_ANALYSIS_PROMPT},
            {
                "text": (
                    f"Analyze the following {len(images)} vehicle photograph(s) "
                    "and return a JSON with detected defects following the specified structure."
                ),
            },
        ]

        for image in images:
            image_data = self._load_image_data(image.file_path)
            mime_type = self._guess_mime(image.file_path)
            parts.append({
                "inlineData": {
                    "mimeType": mime_type,
                    "data": image_data,
                }
            })

        request_body: dict[str, Any] = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "maxOutputTokens": self._max_tokens,
                "temperature": self._temperature,
                "responseMimeType": "application/json",
            },
        }

        raw_response: dict[str, Any] = {}
        try:
            response = await self._http_client.post(
                f"{self._base_url}:generateContent?key={self._api_key}",
                headers={"Content-Type": "application/json"},
                json=request_body,
            )
            if response.status_code >= 400:
                status_code = response.status_code
                error_body = response.text
                if status_code == 400:
                    raise VisionProviderError(
                        f"Bad request: {error_body}",
                        provider="gemini",
                    )
                elif status_code == 403:
                    raise VisionProviderError(
                        "API key invalid or Gemini API not enabled. Check your GEMINI_API_KEY.",
                        provider="gemini",
                    )
                elif status_code == 429:
                    raise VisionProviderError(
                        "Rate limit exceeded. Please try again later.",
                        provider="gemini",
                    )
                else:
                    raise VisionProviderError(
                        f"HTTP {status_code}: {error_body}",
                        provider="gemini",
                    )
            raw_response = response.json()
        except VisionProviderError:
            raise
        except httpx.TimeoutException as exc:
            raise VisionProviderError(
                "Request timed out. The API did not respond in time.",
                provider="gemini",
            ) from exc
        except httpx.RequestError as exc:
            raise VisionProviderError(
                f"Network error: {exc}",
                provider="gemini",
            ) from exc

        return self._parse_response(raw_response, images)

    async def is_available(self) -> bool:
        try:
            response = await self._http_client.get(
                f"https://generativelanguage.googleapis.com/v1beta/models?key={self._api_key}",
            )
            return response.status_code == 200
        except (httpx.HTTPError, OSError, ValueError) as exc:
            logger.warning("gemini is_available check failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_image_data(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            raise VisionProviderError(
                f"Image file not found: {file_path}",
                provider="gemini",
            )
        return base64.b64encode(path.read_bytes()).decode("utf-8")

    def _guess_mime(self, file_path: str) -> str:
        lower = file_path.lower()
        if lower.endswith(".png"):
            return "image/png"
        if lower.endswith(".webp"):
            return "image/webp"
        if lower.endswith(".gif"):
            return "image/gif"
        return "image/jpeg"

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(
        self,
        raw_response: dict[str, Any],
        original_images: list[VisionImage],
    ) -> VisionInspectionResult:
        try:
            candidates = raw_response.get("candidates", [])
            if not candidates:
                raise VisionProviderError(
                    "No candidates in Gemini response",
                    provider="gemini",
                )

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])
            text = ""
            for part in parts:
                if "text" in part:
                    text = part["text"]
                    break

            if not text:
                raise VisionProviderError(
                    "Empty text in Gemini response",
                    provider="gemini",
                )

            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise VisionProviderError(
                f"Invalid JSON in response: {exc}",
                provider="gemini",
            ) from exc
        except VisionProviderError:
            raise

        observations: list[VisionObservation] = []
        for obs in data.get("observations", []):
            try:
                observations.append(VisionObservation(
                    photo_id=obs.get("photo_id", ""),
                    status=obs.get("status", "WARNING"),
                    severity=VisionSeverity(obs.get("severity", "MEDIUM")),
                    confidence=VisionConfidence(obs.get("confidence", "MEDIUM")),
                    notes=obs.get("notes", ""),
                    suggested_repair_cost=obs.get("suggested_repair_cost"),
                ))
            except (ValueError, KeyError) as exc:
                logger.warning("Skipping malformed observation: %s", exc)

        return VisionInspectionResult(
            observations=observations,
            summary=data.get("summary", "Analisis completado."),
        )


class VisionProviderError(Exception):
    """Error raised by GeminiVisionProvider."""

    def __init__(self, message: str, provider: str = "gemini") -> None:
        super().__init__(message)
        self.provider = provider
