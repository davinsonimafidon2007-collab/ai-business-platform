"""InspectionService — Orquestador del módulo Inspection Session.

Actúa únicamente como orquestador entre:
- Repositorios (acceso a datos)
- Motores existentes (NegotiationEngine, EvaluationEngine)
- Catálogo estático de inspección (app/config/inspection.py)

NO contiene lógica de valoración ni negociación.
Esa lógica pertenece a NegotiationEngine y EvaluationEngine.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.config.inspection import (
    CRITICAL_SEVERITY_THRESHOLD,
    INSPECTION_CATEGORIES,
    SEVERITY_MAP,
    InspectionItemStatus,
    InspectionSessionStatus,
    SeverityLevel,
    get_item_def,
    get_total_items_count,
)
from app.core.config import settings
from app.models.inspection import (
    InspectionObservation,
    InspectionPhoto,
    InspectionSession,
)
from app.models.negotiation import (
    DefectItem,
    InspectionResult,
    NegotiationInput,
    NegotiationResult,
    RepairEstimate,
)
from app.models.vehicle_evaluation import VehicleEvaluation
from app.repositories.inspection_repository import (
    InspectionObservationRepository,
    InspectionPhotoRepository,
    InspectionSessionRepository,
)
from app.repositories.vehicle_evaluation_repository import VehicleEvaluationRepository
from app.services.evaluation_engine import EvaluationEngine
from app.services.negotiation_engine import NegotiationEngine
from app.services.vision_service import VisionService


class InspectionService:
    """Servicio de orquestación de inspecciones.

    Coordina la creación, actualización y finalización de sesiones
    de inspección, delegando la lógica de negocio a los motores
    existentes (NegotiationEngine, EvaluationEngine).
    """

    def __init__(
        self,
        session_repo: InspectionSessionRepository,
        observation_repo: InspectionObservationRepository,
        photo_repo: InspectionPhotoRepository,
        negotiation_engine: NegotiationEngine | None = None,
        evaluation_engine: EvaluationEngine | None = None,
        vision_service: VisionService | None = None,
        evaluation_repo: VehicleEvaluationRepository | None = None,
    ) -> None:
        self._session_repo = session_repo
        self._observation_repo = observation_repo
        self._photo_repo = photo_repo
        self._negotiation_engine = negotiation_engine or NegotiationEngine()
        self._evaluation_engine = evaluation_engine or EvaluationEngine(
            import_cost_profile=getattr(settings, "default_import_cost_profile", None)
        )
        self._vision_service = vision_service
        self._evaluation_repo = evaluation_repo

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def create_session(self, vehicle_id: str, user_id: str) -> InspectionSession:
        """Crea una nueva sesión de inspección para un vehículo.

        Args:
            vehicle_id: ID del vehículo a inspeccionar.
            user_id: ID del usuario propietario de la sesión.

        Returns:
            InspectionSession creada en estado DRAFT.
        """
        session = InspectionSession(
            vehicle_id=vehicle_id,
            user_id=user_id,
            status=InspectionSessionStatus.DRAFT.value,
            current_category_order=1,
        )
        return await self._session_repo.create(session)

    async def get_session(self, session_id: str | UUID) -> InspectionSession | None:
        """Obtiene una sesión de inspección por su ID.

        Args:
            session_id: ID de la sesión.

        Returns:
            InspectionSession o None si no existe.
        """
        return await self._session_repo.get_by_id(session_id)

    async def get_session_with_details(
        self, session_id: str | UUID
    ) -> dict[str, Any] | None:
        """Obtiene una sesión con todas sus observaciones y fotos.

        Args:
            session_id: ID de la sesión.

        Returns:
            Dict con session, observations y photos, o None.
        """
        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            return None

        observations = await self._observation_repo.get_by_session(session_id)
        photos = await self._photo_repo.get_by_session(session_id)

        return {
            "session": session.to_dict(),
            "observations": [obs.to_dict() for obs in observations],
            "photos": [photo.to_dict() for photo in photos],
            "catalog": self._get_catalog_with_status(observations),
        }

    # ------------------------------------------------------------------
    # Integración con el pipeline de búsqueda (TASK 4/6 — AUD-012)
    # ------------------------------------------------------------------
    #
    # SearchResultAnalyzer._load_inspection_result llamaba a estos tres
    # métodos, que NO existían: el wiring nunca pudo funcionar y su
    # `except Exception` convertía el AttributeError en un silencioso
    # "no hay inspección". Implementados aquí sobre los repositorios
    # reales para que la negociación automática use defectos reales en
    # vez de la heurística vacía.

    async def get_latest_session_for_vehicle(
        self, vehicle_id: str | UUID | None
    ) -> InspectionSession | None:
        """Última sesión de inspección de un vehículo (o None si no hay).

        Prioriza sesiones finalizadas (COMPLETED) sobre borradores: si el
        usuario terminó una inspección, esa es la que refleja el estado real
        del vehículo. Dentro de cada grupo se toma la más reciente.
        """
        if not vehicle_id:
            return None
        sessions = await self._session_repo.get_by_vehicle_id(vehicle_id)
        if not sessions:
            return None
        completed = [
            s
            for s in sessions
            if s.status == InspectionSessionStatus.COMPLETED.value
        ]
        # get_by_vehicle_id ya ordena por created_at DESC.
        return completed[0] if completed else sessions[0]

    async def get_session_observations(
        self, session_id: str | UUID
    ) -> list[InspectionObservation]:
        """Observaciones registradas en una sesión de inspección."""
        return await self._observation_repo.get_by_session(session_id)

    def build_inspection_result(
        self, observations: list[InspectionObservation]
    ) -> InspectionResult:
        """Convierte observaciones en el InspectionResult del dominio de negociación.

        Usa la misma escala de ``overall_condition`` que ``_build_summary``
        (10 = perfecto; -1 por cada WARNING, -2 por cada BAD, mínimo 1) para
        no tener dos definiciones distintas del estado del vehículo.
        """
        defects = self._build_defect_items(observations)
        warning_items = [
            obs
            for obs in observations
            if obs.status == InspectionItemStatus.WARNING.value
        ]
        bad_items = [
            obs for obs in observations if obs.status == InspectionItemStatus.BAD.value
        ]
        if not defects:
            overall_condition = 10
        else:
            penalty = len(warning_items) * 1 + len(bad_items) * 2
            overall_condition = max(1, 10 - penalty)

        notes = [obs.notes for obs in observations if getattr(obs, "notes", None)]
        return InspectionResult(
            defects=defects,
            overall_condition=overall_condition,
            has_accident_history=False,
            inspection_notes=notes,
        )

    # ------------------------------------------------------------------
    # Item management
    # ------------------------------------------------------------------

    async def update_item(
        self,
        session_id: str | UUID,
        category_id: str,
        item_id: str,
        status: str,
        notes: str | None = None,
        estimated_repair_cost: float | None = None,
    ) -> InspectionObservation:
        """Crea o actualiza la observación de un punto de inspección.

        Args:
            session_id: ID de la sesión.
            category_id: ID de la categoría (ej: 'exterior').
            item_id: ID del ítem (ej: 'pintura').
            status: Estado del ítem (GOOD, WARNING, BAD, UNKNOWN).
            notes: Notas opcionales.
            estimated_repair_cost: Coste estimado de reparación opcional.

        Returns:
            InspectionObservation creada o actualizada.

        Raises:
            ValueError: Si el ítem no existe en el catálogo.
        """
        # Validar que el ítem existe en el catálogo
        item_def = get_item_def(category_id, item_id)
        if item_def is None:
            raise ValueError(
                f"Item '{item_id}' not found in category '{category_id}'"
            )

        # Buscar si ya existe una observación para este ítem
        existing = await self._observation_repo.get_by_item(
            session_id, category_id, item_id
        )

        if existing:
            # Actualizar existente
            existing.status = status
            existing.updated_at = datetime.now(UTC)
            if notes is not None:
                existing.notes = notes
            if estimated_repair_cost is not None and item_def.has_cost_estimate:
                existing.estimated_repair_cost = estimated_repair_cost
            # Actualizar severidad basada en el estado
            new_severity = SEVERITY_MAP.get(
                InspectionItemStatus(status), SeverityLevel.LOW
            )
            existing.severity = new_severity.value
            return await self._observation_repo.update(existing)

        # Crear nueva observación
        severity = SEVERITY_MAP.get(
            InspectionItemStatus(status), SeverityLevel.LOW
        )
        observation = InspectionObservation(
            session_id=str(session_id),
            category_id=category_id,
            item_id=item_id,
            status=status,
            notes=notes,
            estimated_repair_cost=estimated_repair_cost if item_def.has_cost_estimate else None,
            severity=severity.value,
        )
        return await self._observation_repo.create(observation)

    # ------------------------------------------------------------------
    # Photo management
    # ------------------------------------------------------------------

    async def upload_photo(
        self,
        session_id: str | UUID,
        observation_id: str | UUID,
        file_path: str,
        file_name: str | None = None,
        mime_type: str | None = None,
        file_size_bytes: int | None = None,
    ) -> InspectionPhoto:
        """Registra una fotografía asociada a una observación.

        Args:
            session_id: ID de la sesión.
            observation_id: ID de la observación.
            file_path: Ruta o URL del archivo.
            file_name: Nombre original del archivo.
            mime_type: Tipo MIME.
            file_size_bytes: Tamaño en bytes.

        Returns:
            InspectionPhoto creada.
        """
        # SEC.LFI.1: file_path solo acepta rutas dentro del directorio de
        # uploads o URLs https públicas (ver app/core/path_safety.py).
        from app.core.config import settings
        from app.core.path_safety import validate_photo_file_path

        safe_file_path = validate_photo_file_path(file_path, settings.upload_dir)
        photo = InspectionPhoto(
            session_id=str(session_id),
            observation_id=str(observation_id),
            file_path=safe_file_path,
            file_name=file_name,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
        )
        return await self._photo_repo.create(photo)

    async def get_photos_for_observation(
        self, observation_id: str | UUID
    ) -> list[InspectionPhoto]:
        """Obtiene todas las fotos de una observación."""
        return await self._photo_repo.get_by_observation(observation_id)

    async def analyze_photos(
        self, session_id: str | UUID, photo_ids: list[str] | None = None
    ) -> dict[str, object]:
        """Returns vision suggestions without changing the inspection session."""
        if self._vision_service is None:
            raise ValueError("Vision provider is not configured")
        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            raise ValueError(f"Session '{session_id}' not found")
        photos = await self._photo_repo.get_by_session(session_id)
        if photo_ids is not None:
            requested = set(photo_ids)
            photos = [photo for photo in photos if photo.id in requested]
        observations = {
            photo.id: observation
            for photo in photos
            if (observation := await self._observation_repo.get_by_id(photo.observation_id))
            is not None
        }
        return await self._vision_service.analyze_photos(photos, observations)

    # ------------------------------------------------------------------
    # Finalization & Summary
    # ------------------------------------------------------------------

    async def finalize_session(
        self, session_id: str | UUID
    ) -> InspectionSession:
        """Finaliza una sesión de inspección y genera el resumen.

        Calcula estadísticas, genera el resumen y actualiza el estado
        de la sesión a COMPLETED.

        Args:
            session_id: ID de la sesión a finalizar.

        Returns:
            InspectionSession actualizada con estado COMPLETED.

        Raises:
            ValueError: Si la sesión no existe o ya está completada.
        """
        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            raise ValueError(f"Session '{session_id}' not found")

        if session.status == InspectionSessionStatus.COMPLETED.value:
            raise ValueError(f"Session '{session_id}' is already completed")

        observations = await self._observation_repo.get_by_session(session_id)

        # Calcular estadísticas
        summary = self._build_summary(session, observations)

        # --- Ejecutar NegotiationEngine con los datos de la inspección ---
        negotiation_result = self._build_negotiation(summary, observations)
        summary["negotiation"] = self._serialize_negotiation(negotiation_result)

        # --- Actualizar VehicleEvaluation si tenemos repositorio ---
        if self._evaluation_repo is not None:
            try:
                existing_eval = await self._evaluation_repo.get_by_vehicle_id(session.vehicle_id)
                if existing_eval is not None:
                    existing_eval.negotiation = negotiation_result
                    existing_eval.updated_at = datetime.now(UTC)
                    await self._evaluation_repo.update(existing_eval)
                else:
                    # Crear VehicleEvaluation con el resultado de negociación
                    evaluation = VehicleEvaluation(
                        vehicle_id=session.vehicle_id,
                        negotiation=negotiation_result,
                    )
                    await self._evaluation_repo.create(evaluation)
            except Exception:
                # Si falla la actualización de VehicleEvaluation, no bloquear la finalización
                pass

        # Actualizar la sesión con los resultados
        session.status = InspectionSessionStatus.COMPLETED.value
        session.completed_at = datetime.now(UTC)
        session.updated_at = datetime.now(UTC)
        session.total_repair_cost = summary["costs"]["total_repair_cost"]
        session.total_defects = summary["defects"]["total"]
        session.total_critical_defects = summary["defects"]["critical"]
        session.risk_level = summary["risk_level"]
        session.recommendation = summary.get("recommendation")
        session.overall_condition = summary.get("overall_condition")
        session.summary = summary

        return await self._session_repo.update(session)

    async def generate_summary(
        self, session_id: str | UUID
    ) -> dict[str, Any] | None:
        """Genera el resumen de una sesión de inspección.

        Si la sesión está completada, devuelve el summary almacenado.
        Si está en progreso, calcula un resumen parcial.

        Args:
            session_id: ID de la sesión.

        Returns:
            Dict con el resumen o None si la sesión no existe.
        """
        session = await self._session_repo.get_by_id(session_id)
        if session is None:
            return None

        if session.status == InspectionSessionStatus.COMPLETED.value and session.summary:
            return session.summary

        observations = await self._observation_repo.get_by_session(session_id)
        summary = self._build_summary(session, observations)
        summary["negotiation"] = self._serialize_negotiation(
            self._build_negotiation(summary, observations)
        )
        return summary

    # ------------------------------------------------------------------
    # Internal helpers

    def _build_negotiation(
        self, summary: dict[str, Any], observations: list[InspectionObservation]
    ) -> NegotiationResult:
        """Ejecuta NegotiationEngine con los datos actuales de la inspección.

        Reutilizado por ``finalize_session`` y por ``generate_summary`` para
        que la negociación se actualice en vivo mientras la inspección sigue
        en progreso (PERSONAL.NOAUTH).
        """
        from app.models.market import MarketEstimation

        defect_items = self._build_defect_items(observations)
        total_repair_cost = summary["costs"]["total_repair_cost"]
        repair_estimate = RepairEstimate(
            total_repair_cost=total_repair_cost,
            parts_cost=summary["costs"]["parts_cost"],
            labor_cost=summary["costs"]["labor_cost"],
            paint_and_body_cost=summary["costs"]["paint_and_body_cost"],
            diagnostic_cost=50.0 if total_repair_cost > 0 else 0.0,
        )
        inspection_result = InspectionResult(
            defects=defect_items,
            overall_condition=summary["overall_condition"] or 10,
            has_accident_history=False,
        )
        # NegotiationInput requiere market_estimation, profit_analysis_data y
        # vehicle_score_data; la inspección no tiene acceso directo a ellos, así
        # que se usan datos mínimos (el NegotiationEngine tolera valores por defecto).
        negotiation_input = NegotiationInput(
            inspection_result=inspection_result,
            repair_estimate=repair_estimate,
            market_estimation=MarketEstimation(
                market_price=0.0,
                supply_level=50.0,
                demand_level=50.0,
                market_trend="stable",
                confidence=50.0,
            ),
            asking_price=0.0,
            profit_analysis_data={},
            vehicle_score_data={},
        )
        return self._negotiation_engine.analyze(negotiation_input)

    @staticmethod
    def _serialize_negotiation(
        negotiation_result: NegotiationResult,
    ) -> dict[str, Any]:
        """Convierte NegotiationResult a dict con el enum recomendación en string."""
        negotiation: dict[str, Any] = asdict(negotiation_result)
        if "recommendation" in negotiation and hasattr(
            negotiation["recommendation"], "value"
        ):
            negotiation["recommendation"] = negotiation["recommendation"].value
        return negotiation
    # ------------------------------------------------------------------

    def _build_summary(
        self,
        session: InspectionSession,
        observations: list[InspectionObservation],
    ) -> dict[str, Any]:
        """Construye el resumen de la inspección.

        Calcula estadísticas de defectos, costes de reparación,
        y genera datos para el motor de negociación.

        Args:
            session: Sesión de inspección.
            observations: Observaciones de la sesión.

        Returns:
            Dict con el resumen completo.
        """
        # --- Estadísticas básicas ---
        total_items = get_total_items_count()
        reviewed_items = len(observations)
        progress_pct = (reviewed_items / total_items * 100) if total_items > 0 else 0

        # --- Análisis de defectos ---
        defects = [obs for obs in observations if obs.status != InspectionItemStatus.GOOD.value]
        good_items = [obs for obs in observations if obs.status == InspectionItemStatus.GOOD.value]
        warning_items = [obs for obs in observations if obs.status == InspectionItemStatus.WARNING.value]
        bad_items = [obs for obs in observations if obs.status == InspectionItemStatus.BAD.value]

        total_repair_cost = sum(
            obs.estimated_repair_cost or 0.0 for obs in observations
        )
        total_defects = len(defects)
        total_critical = sum(
            1 for obs in defects
            if self._get_severity_weight(obs.severity) >= CRITICAL_SEVERITY_THRESHOLD
        )

        # --- Overall condition (1-10) ---
        if total_defects == 0:
            overall_condition = 10
        else:
            # Penalizar por defectos: -1 por cada WARNING, -2 por cada BAD
            penalty = len(warning_items) * 1 + len(bad_items) * 2
            overall_condition = max(1, 10 - penalty)

        # --- Risk level ---
        if total_critical > 0:
            risk_level = "HIGH"
        elif total_defects > 5:
            risk_level = "MEDIUM"
        elif total_defects > 0:
            risk_level = "LOW"
        else:
            risk_level = "NONE"

        # --- Recommendation ---
        if risk_level == "HIGH":
            recommendation = (
                "Se recomienda una revisión profesional antes de proceder "
                "con la compra. Los defectos críticos detectados requieren "
                "atención inmediata."
            )
        elif risk_level == "MEDIUM":
            recommendation = (
                "El vehículo presenta defectos moderados. Se recomienda "
                "negociar el precio considerando los costes de reparación."
            )
        elif risk_level == "LOW":
            recommendation = (
                "El vehículo está en buen estado general. Los defectos "
                "menores no deberían afectar significativamente al valor."
            )
        else:
            recommendation = (
                "El vehículo no presenta defectos. Está en excelentes condiciones."
            )

        # --- Construir DefectItems para NegotiationEngine ---
        defect_items = self._build_defect_items(observations)

        # --- Construir RepairEstimate ---
        repair_estimate = RepairEstimate(
            total_repair_cost=total_repair_cost,
            parts_cost=total_repair_cost * 0.4,  # Estimación: 40% piezas
            labor_cost=total_repair_cost * 0.4,  # Estimación: 40% mano de obra
            paint_and_body_cost=total_repair_cost * 0.15,  # 15% pintura/carrocería
            diagnostic_cost=50.0 if total_repair_cost > 0 else 0.0,
        )

        # --- Construir InspectionResult ---
        inspection_result = InspectionResult(
            defects=defect_items,
            overall_condition=overall_condition,
            has_accident_history=False,  # Se podría detectar en el futuro
            inspection_notes=[],
        )

        return {
            "session_id": session.id,
            "vehicle_id": session.vehicle_id,
            "status": session.status,
            "progress": {
                "reviewed_items": reviewed_items,
                "total_items": total_items,
                "percentage": round(progress_pct, 1),
            },
            "defects": {
                "total": total_defects,
                "good": len(good_items),
                "warning": len(warning_items),
                "bad": len(bad_items),
                "critical": total_critical,
            },
            "costs": {
                "total_repair_cost": round(total_repair_cost, 2),
                "parts_cost": round(repair_estimate.parts_cost, 2),
                "labor_cost": round(repair_estimate.labor_cost, 2),
                "paint_and_body_cost": round(repair_estimate.paint_and_body_cost, 2),
            },
            "overall_condition": overall_condition,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "defect_items": [
                {
                    "category": d.category,
                    "description": d.description,
                    "severity": d.severity,
                    "estimated_repair_cost": d.estimated_repair_cost,
                    "is_safety_relevant": d.is_safety_relevant,
                }
                for d in defect_items
            ],
            "repair_estimate": {
                "total_repair_cost": repair_estimate.total_repair_cost,
                "parts_cost": repair_estimate.parts_cost,
                "labor_cost": repair_estimate.labor_cost,
            },
            "inspection_result": {
                "overall_condition": inspection_result.overall_condition,
                "has_accident_history": inspection_result.has_accident_history,
            },
        }

    def _build_defect_items(
        self, observations: list[InspectionObservation]
    ) -> list[DefectItem]:
        """Convierte observaciones en DefectItems para NegotiationEngine.

        Args:
            observations: Lista de observaciones de la sesión.

        Returns:
            Lista de DefectItem listos para NegotiationEngine.
        """
        defect_items: list[DefectItem] = []

        for obs in observations:
            if obs.status == InspectionItemStatus.GOOD.value:
                continue

            item_def = get_item_def(obs.category_id, obs.item_id)
            severity_weight = self._get_severity_weight(obs.severity)

            defect_items.append(
                DefectItem(
                    category=obs.category_id,
                    description=item_def.label if item_def else obs.item_id,
                    severity=severity_weight,
                    estimated_repair_cost=obs.estimated_repair_cost or 0.0,
                    is_safety_relevant=item_def.is_safety_relevant if item_def else False,
                    can_be_used_as_leverage=True,
                )
            )

        return defect_items

    @staticmethod
    def _get_severity_weight(severity: str) -> int:
        """Obtiene el peso numérico de un nivel de severidad."""
        mapping = {
            SeverityLevel.LOW.value: 0,
            SeverityLevel.MEDIUM.value: 3,
            SeverityLevel.HIGH.value: 7,
            SeverityLevel.CRITICAL.value: 10,
        }
        return mapping.get(severity, 0)

    def _get_catalog_with_status(
        self, observations: list[InspectionObservation]
    ) -> list[dict[str, Any]]:
        """Construye el catálogo con el estado actual de cada ítem.

        Args:
            observations: Observaciones existentes.

        Returns:
            Lista de categorías con sus ítems y estado.
        """
        # Indexar observaciones por (category_id, item_id)
        obs_map: dict[tuple[str, str], InspectionObservation] = {}
        for obs in observations:
            obs_map[(obs.category_id, obs.item_id)] = obs

        result = []
        for cat in INSPECTION_CATEGORIES:
            items = []
            for item in cat.items:
                obs = obs_map.get((cat.id, item.id))
                items.append({
                    "id": item.id,
                    "label": item.label,
                    "description": item.description,
                    "order": item.order,
                    "is_safety_relevant": item.is_safety_relevant,
                    "has_cost_estimate": item.has_cost_estimate,
                    "allows_photos": item.allows_photos,
                    "status": obs.status if obs else InspectionItemStatus.UNKNOWN.value,
                    "notes": obs.notes if obs else None,
                    "estimated_repair_cost": obs.estimated_repair_cost if obs else None,
                    "severity": obs.severity if obs else SeverityLevel.LOW.value,
                    "observation_id": obs.id if obs else None,
                })

            result.append({
                "id": cat.id,
                "label": cat.label,
                "icon": cat.icon,
                "description": cat.description,
                "order": cat.order,
                "items": items,
            })

        return result
