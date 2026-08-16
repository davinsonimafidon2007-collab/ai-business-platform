"""Interfaz abstracta VisionProvider para análisis de imágenes.

Este módulo define el contrato que deben cumplir todos los proveedores
de visión artificial (GPT-4V, Gemini, Claude, etc.).

No se implementa ningún proveedor real todavía.
La arquitectura queda preparada para que en el futuro solo sea necesario
implementar esta interfaz y conectar el proveedor en dependencies.py.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# =============================================================================
# DTOs de entrada/salida para el análisis de visión
# =============================================================================


class VisionDefectType(str, Enum):
    """Tipo de defecto detectable por visión artificial."""

    SCRATCH = "SCRATCH"
    DENT = "DENT"
    RUST = "RUST"
    CRACK = "CRACK"
    WEAR = "WEAR"
    LEAK = "LEAK"
    CORROSION = "CORROSION"
    MISALIGNMENT = "MISALIGNMENT"
    UNKNOWN = "UNKNOWN"


@dataclass
class VisionDetectedDefect:
    """Defecto detectado automáticamente por el análisis de imagen."""

    defect_type: VisionDefectType
    """Tipo de defecto detectado."""
    confidence: float
    """Confianza de la detección (0.0 - 1.0)."""
    bounding_box: list[float] | None = None
    """Coordenadas [x1, y1, x2, y2] del defecto en la imagen."""
    description: str = ""
    """Descripción en lenguaje natural del defecto."""
    estimated_severity: int = 5
    """Severidad estimada (1-10)."""


@dataclass
class VisionAnalysisResult:
    """Resultado completo del análisis de una imagen por visión artificial."""

    photo_id: str
    """ID de la foto analizada."""
    detected_defects: list[VisionDetectedDefect] = field(default_factory=list)
    """Lista de defectos detectados en la imagen."""
    overall_condition_score: int = 10
    """Puntuación general del estado (1-10)."""
    summary: str = ""
    """Resumen textual del análisis."""
    requires_human_review: bool = False
    """True si el sistema sugiere revisión humana."""
    raw_response: dict[str, Any] = field(default_factory=dict)
    """Respuesta cruda del proveedor de IA (para debug/auditoría)."""


@dataclass
class VisionInspectionResult:
    """Resultado del análisis de múltiples imágenes de una inspección."""

    photo_results: list[VisionAnalysisResult] = field(default_factory=list)
    """Resultados individuales por foto."""
    global_summary: str = ""
    """Resumen global de todas las imágenes analizadas."""
    suggested_items_update: dict[str, Any] = field(default_factory=dict)
    """Sugerencias de actualización de ítems basadas en el análisis."""


# =============================================================================
# Interfaz abstracta del proveedor
# =============================================================================


class VisionProvider(ABC):
    """Interfaz para proveedores de análisis de imágenes.

    Cualquier proveedor de visión artificial (GPT-4V, Gemini, Claude, etc.)
    debe implementar esta interfaz.

    Métodos:
        analyze_photo: Analiza una sola fotografía.
        analyze_photos: Analiza múltiples fotografías.
        is_available: Verifica si el proveedor está disponible/configurado.
    """

    @abstractmethod
    async def analyze_photo(
        self,
        image_path: str,
        inspection_context: str | None = None,
    ) -> VisionAnalysisResult:
        """Analiza una sola fotografía y devuelve los defectos detectados.

        Args:
            image_path: Ruta o URL de la imagen a analizar.
            inspection_context: Contexto opcional de la inspección
                (ej: "Revisando pintura del capó").

        Returns:
            VisionAnalysisResult con los defectos detectados.

        Raises:
            VisionProviderError: Si el análisis falla.
        """
        ...

    @abstractmethod
    async def analyze_photos(
        self,
        photo_paths: list[str],
        inspection_context: str | None = None,
    ) -> VisionInspectionResult:
        """Analiza múltiples fotografías y devuelve resultados agregados.

        Args:
            photo_paths: Lista de rutas/URLs de imágenes.
            inspection_context: Contexto opcional de la inspección.

        Returns:
            VisionInspectionResult con resultados agregados.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Verifica si el proveedor está disponible y configurado.

        Returns:
            True si el proveedor puede ser usado.
        """
        ...


class VisionProviderError(Exception):
    """Error general del proveedor de visión."""

    def __init__(self, message: str, provider: str = "unknown") -> None:
        self.provider = provider
        super().__init__(f"[{provider}] {message}")

