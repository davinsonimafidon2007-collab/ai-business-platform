"""OpenAI GPT-4 Vision provider for vehicle inspection photo analysis.

Implements the VisionProvider protocol to analyze vehicle damage
from photographs using OpenAI's vision-capable models (GPT-4o, GPT-4V).

Replaces MockVisionProvider in production by swapping the dependency
in app/api/v1/dependencies.py.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.models.vision import (
    VisionConfidence,
    VisionImage,
    VisionInspectionResult,
    VisionObservation,
    VisionSeverity,
)
from app.providers.vision_provider import VisionProvider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt template for vehicle damage analysis
# ---------------------------------------------------------------------------

DAMAGE_ANALYSIS_SYSTEM_PROMPT = """You are an expert vehicle damage assessor.
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
# DTO for the OpenAI API response
# ---------------------------------------------------------------------------


@dataclass
class _OpenAIMessage:
    role: str
    content: str


@dataclass
class _OpenAIChoice:
    index: int
    message: _OpenAIMessage
    finish_reason: str


@dataclass
class _OpenAIResponse:
    id: str
    choices: list[_OpenAIChoice]
    usage: dict[str, int] | None = None


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class OpenAIVisionProvider:
    """Analyzes vehicle photos using OpenAI's vision models.

    Args:
        api_key: OpenAI API key.
        model: Model name (default: 'gpt-4o').
        max_tokens: Maximum tokens for the response (default: 2000).
        temperature: Sampling temperature (default: 0.1).
        http_client: Optional pre-configured httpx.AsyncClient.
            If None, a default client is created.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        max_tokens: int = 2000,
        temperature: float = 0.1,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key is required")

        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._http_client = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
        )

    # ------------------------------------------------------------------
    # Public API (VisionProvider protocol)
    # ------------------------------------------------------------------

    async def analyze_images(
        self, images: list[VisionImage]
    ) -> VisionInspectionResult:
        """Analyze vehicle photos and return detected defects.

        Args:
            images: List of photos to analyze.

        Returns:
            VisionInspectionResult with observations and summary.

        Raises:
            VisionProviderError: If the API call fails or response is invalid.
        """
        if not images:
            return VisionInspectionResult(observations=[], summary="No se proporcionaron imágenes.")

        # Build content parts: system text + user text + images
        content_parts: list[dict[str, Any]] = [
            {"type": "text", "text": DAMAGE_ANALYSIS_SYSTEM_PROMPT},
            {
                "type": "text",
                "text": (
                    f"Analyze the following {len(images)} vehicle photograph(s) "
                    "and return a JSON with detected defects following the specified structure."
                ),
            },
        ]

        for image in images:
            content_parts.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": image.file_path,
                        "detail": "high",
                    },
                }
            )

        # Build the OpenAI chat completion request
        request_body: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": content_parts,
                }
            ],
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "response_format": {"type": "json_object"},
        }

        raw_response: dict[str, Any] = {}
        try:
            response = await self._http_client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=request_body,
            )
            if response.status_code >= 400:
                status_code = response.status_code
                error_body = response.text if hasattr(response, 'text') else ""
                if status_code == 401:
                    raise VisionProviderError(
                        "Authentication failed. Check your OpenAI API key.",
                        provider="openai",
                    )
                elif status_code == 429:
                    raise VisionProviderError(
                        "Rate limit exceeded. Please try again later.",
                        provider="openai",
                    )
                elif status_code == 400:
                    raise VisionProviderError(
                        f"Bad request: {error_body}",
                        provider="openai",
                    )
                else:
                    raise VisionProviderError(
                        f"HTTP {status_code}: {error_body}",
                        provider="openai",
                    )
            raw_response = response.json()
        except VisionProviderError:
            raise
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            error_body = exc.response.text
            if status_code == 401:
                raise VisionProviderError(
                    "Authentication failed. Check your OpenAI API key.",
                    provider="openai",
                ) from exc
            elif status_code == 429:
                raise VisionProviderError(
                    "Rate limit exceeded. Please try again later.",
                    provider="openai",
                ) from exc
            elif status_code == 400:
                raise VisionProviderError(
                    f"Bad request: {error_body}",
                    provider="openai",
                ) from exc
            else:
                raise VisionProviderError(
                    f"HTTP {status_code}: {error_body}",
                    provider="openai",
                ) from exc
        except httpx.TimeoutException as exc:
            raise VisionProviderError(
                "Request timed out. The API did not respond in time.",
                provider="openai",
            ) from exc
        except httpx.RequestError as exc:
            raise VisionProviderError(
                f"Network error: {exc}",
                provider="openai",
            ) from exc

        # Parse the response
        return self._parse_response(raw_response, images)

    async def is_available(self) -> bool:
        """Check if the provider is available by listing models.

        Returns:
            True if the API key is valid and the API is reachable.
        """
        try:
            response = await self._http_client.get(
                "https://api.openai.com/v1/models",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                },
            )
            return response.status_code == 200
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    def _parse_response(
        self,
        raw_response: dict[str, Any],
        original_images: list[VisionImage],
    ) -> VisionInspectionResult:
        """Parse the OpenAI API response into VisionInspectionResult.

        Args:
            raw_response: The raw JSON from the OpenAI API.
            original_images: The original images sent for analysis.

        Returns:
            Parsed VisionInspectionResult.

        Raises:
            VisionProviderError: If the response cannot be parsed.
        """
        try:
            choices = raw_response.get("choices", [])
            if not choices:
                raise VisionProviderError(
                    "Empty response from OpenAI (no choices).",
                    provider="openai",
                )

            message = choices[0].get("message", {})
            content = message.get("content", "")

            if not content:
                raise VisionProviderError(
                    "Empty content in OpenAI response.",
                    provider="openai",
                )

            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise VisionProviderError(
                f"Failed to parse JSON from OpenAI response: {exc}",
                provider="openai",
            ) from exc
        except (KeyError, IndexError, TypeError) as exc:
            raise VisionProviderError(
                f"Unexpected response structure: {exc}",
                provider="openai",
            ) from exc

        # Parse observations
        raw_observations = parsed.get("observations", [])
        observations: list[VisionObservation] = []
        seen_photo_ids: set[str] = set()

        for raw_obs in raw_observations:
            photo_id = raw_obs.get("photo_id", "")

            # Map status
            status = str(raw_obs.get("status", "WARNING")).upper()
            if status not in ("GOOD", "WARNING", "BAD"):
                status = "WARNING"

            # Track that this photo was seen, even if GOOD
            seen_photo_ids.add(photo_id)

            # For GOOD status, skip (we only report defects)
            if status == "GOOD":
                continue

            # Map severity
            severity_str = str(raw_obs.get("severity", "MEDIUM")).upper()
            try:
                severity = VisionSeverity(severity_str)
            except ValueError:
                severity = VisionSeverity.MEDIUM

            # Map confidence
            confidence_str = str(raw_obs.get("confidence", "MEDIUM")).upper()
            try:
                confidence = VisionConfidence(confidence_str)
            except ValueError:
                confidence = VisionConfidence.MEDIUM

            # Repair cost
            suggested_repair_cost = raw_obs.get("suggested_repair_cost")
            if suggested_repair_cost is not None:
                suggested_repair_cost = float(suggested_repair_cost)
                if suggested_repair_cost < 0:
                    suggested_repair_cost = None

            # Notes
            notes = str(raw_obs.get("notes", ""))[:500]  # Truncate to 500 chars

            observation = VisionObservation(
                photo_id=photo_id,
                status=status,
                severity=severity,
                confidence=confidence,
                notes=notes,
                suggested_repair_cost=suggested_repair_cost,
            )
            observations.append(observation)
            seen_photo_ids.add(photo_id)

        # Add placeholder observations for photos that were not mentioned
        # (with a low-confidence "UNKNOWN" interpretation)
        for image in original_images:
            if image.photo_id not in seen_photo_ids:
                observations.append(
                    VisionObservation(
                        photo_id=image.photo_id,
                        status="WARNING",
                        severity=VisionSeverity.LOW,
                        confidence=VisionConfidence.LOW,
                        notes="No se pudo analizar esta imagen automáticamente. Se recomienda revisión manual.",
                        suggested_repair_cost=None,
                    )
                )

        # Summary
        summary = str(parsed.get("summary", ""))[:1000]

        return VisionInspectionResult(
            observations=observations,
            summary=summary or "Análisis completado con los defectos detectados.",
        )


# ---------------------------------------------------------------------------
# Error
# ---------------------------------------------------------------------------


class VisionProviderError(Exception):
    """Error raised by OpenAIVisionProvider."""

    def __init__(self, message: str, provider: str = "openai") -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")

