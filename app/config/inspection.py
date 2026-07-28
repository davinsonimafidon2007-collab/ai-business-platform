"""Catálogo estático de categorías y puntos de inspección.

NO persiste en base de datos.
Se usa como fuente de verdad para construir el checklist.
Modificar aquí para añadir/eliminar puntos sin migraciones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# =============================================================================
# Enumeraciones
# =============================================================================


class InspectionItemStatus(str, Enum):
    """Estado de un punto de inspección individual."""

    GOOD = "GOOD"
    """Correcto, sin defectos."""
    WARNING = "WARNING"
    """Defecto leve, no crítico."""
    BAD = "BAD"
    """Defecto grave o crítico."""
    UNKNOWN = "UNKNOWN"
    """No revisado todavía."""


class InspectionSessionStatus(str, Enum):
    """Estado global de la sesión de inspección."""

    DRAFT = "DRAFT"
    """En progreso, se puede pausar/reanudar."""
    COMPLETED = "COMPLETED"
    """Finalizada, resumen generado."""


class SeverityLevel(str, Enum):
    """Nivel de gravedad de un defecto."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# =============================================================================
# Catálogo de categorías estáticas
# =============================================================================


@dataclass
class InspectionItemDef:
    """Definición de un punto de inspección en el catálogo."""

    id: str
    """Identificador único dentro de la categoría (ej: 'pintura')."""
    label: str
    """Nombre legible (ej: 'Estado de la pintura')."""
    description: str = ""
    """Descripción opcional de qué revisar."""
    is_safety_relevant: bool = False
    """True si afecta a seguridad (influye en negociación)."""
    has_cost_estimate: bool = True
    """True si se puede asignar un coste de reparación manual."""
    allows_photos: bool = True
    """True si se pueden subir fotos."""
    order: int = 0
    """Orden dentro de la categoría."""


@dataclass
class InspectionCategoryDef:
    """Definición de una categoría de inspección."""

    id: str
    """Identificador único (ej: 'exterior')."""
    label: str
    """Nombre legible (ej: 'Exterior')."""
    icon: str = "📋"
    """Icono para la UI."""
    description: str = ""
    """Descripción opcional."""
    items: list[InspectionItemDef] = field(default_factory=list)
    """Puntos de inspección dentro de esta categoría."""
    order: int = 0
    """Orden de aparición en el flujo."""


# =============================================================================
# Catálogo completo (única fuente de verdad)
# =============================================================================

INSPECTION_CATEGORIES: list[InspectionCategoryDef] = [
    InspectionCategoryDef(
        id="exterior",
        label="Exterior",
        icon="🚘",
        description="Revisión del exterior del vehículo",
        order=1,
        items=[
            InspectionItemDef(id="pintura", label="Estado de la pintura", description="Amarillamientos, decoloraciones, pérdida de brillo", order=1),
            InspectionItemDef(id="golpes", label="Golpes y abolladuras", description="Golpes visibles en carrocería", order=2),
            InspectionItemDef(id="rayones", label="Rayones y marcas", description="Rayones profundos o superficiales", order=3),
            InspectionItemDef(id="oxidacion", label="Óxido y corrosión", description="Puntos de óxido en chapa", is_safety_relevant=True, order=4),
            InspectionItemDef(id="faros", label="Faros y pilotos", description="Estado de ópticas, fisuras, condensación", is_safety_relevant=True, order=5),
            InspectionItemDef(id="parabrisas", label="Parabrisas y lunas", description="Lunas delanteras, traseras, laterales", is_safety_relevant=True, order=6),
            InspectionItemDef(id="llantas", label="Llantas", description="Estado de llantas (aleación, acero)", order=7),
            InspectionItemDef(id="emblemas", label="Emblemas y molduras", description="Emblemas, molduras, frankfurt", order=8),
            InspectionItemDef(id="cierre_puertas", label="Cierre de puertas", description="Apertura y cierre correcto", order=9),
            InspectionItemDef(id="juntas", label="Juntas y gomas", description="Estado de juntas de puertas, ventanas", order=10),
        ],
    ),
    InspectionCategoryDef(
        id="interior",
        label="Interior",
        icon="🚙",
        description="Revisión del interior del vehículo",
        order=2,
        items=[
            InspectionItemDef(id="asientos", label="Asientos", description="Tapicería, ajustes, desgaste", order=1),
            InspectionItemDef(id="salpicadero", label="Salpicadero", description="Grietas, deformaciones, testigos", order=2),
            InspectionItemDef(id="volante", label="Volante", description="Desgaste, botones funcionales", order=3),
            InspectionItemDef(id="tapiceria", label="Tapicería general", description="Puertas, techo, moqueta", order=4),
            InspectionItemDef(id="climatizador", label="Climatizador / A/A", description="Funcionamiento frío/calor", order=5),
            InspectionItemDef(id="elevalunas", label="Elevalunas", description="Subida/bajada correcta", order=6),
            InspectionItemDef(id="cierre_centralizado", label="Cierre centralizado", description="Apertura/cierre remoto", order=7),
            InspectionItemDef(id="espejos", label="Espejos interiores", description="Regulación, antideslumbrante", order=8),
            InspectionItemDef(id="guantera", label="Guantera", description="Apertura, cierre, estado", order=9),
            InspectionItemDef(id="olfato", label="Olor interior", description="Humedad, tabaco, moho", order=10),
        ],
    ),
    InspectionCategoryDef(
        id="motor",
        label="Motor",
        icon="🔧",
        description="Revisión del compartimento motor",
        order=3,
        items=[
            InspectionItemDef(id="nivel_aceite", label="Nivel y estado del aceite", description="Nivel correcto, color, olor a quemado", order=1),
            InspectionItemDef(id="fugas", label="Fugas de líquidos", description="Aceite, refrigerante, dirección, frenos", is_safety_relevant=True, order=2),
            InspectionItemDef(id="correa", label="Correa / Cadena de distribución", description="Estado, tensión, ruidos", is_safety_relevant=True, order=3),
            InspectionItemDef(id="bateria", label="Batería", description="Bornes, estado, tensión", order=4),
            InspectionItemDef(id="refrigerante", label="Líquido refrigerante", description="Nivel, color, presencia de aceite", order=5),
            InspectionItemDef(id="admision", label="Admisión de aire", description="Filtro, manguitos, fugas", order=6),
            InspectionItemDef(id="escape", label="Sistema de escape", description="Humo, ruidos, fugas", is_safety_relevant=True, order=7),
            InspectionItemDef(id="soportes", label="Soportes motor", description="Roturas, desgaste excesivo", order=8),
            InspectionItemDef(id="ruidos", label="Ruidos anómalos", description="Golpeteo, silbidos, rozamiento", is_safety_relevant=True, order=9),
            InspectionItemDef(id="tapa_valvulas", label="Tapa de válvulas", description="Fugas, estado junta", order=10),
        ],
    ),
    InspectionCategoryDef(
        id="electronica",
        label="Electrónica",
        icon="💡",
        description="Revisión de sistemas electrónicos",
        order=4,
        items=[
            InspectionItemDef(id="centralita", label="Centralita / OBD", description="Lectura de códigos de error", is_safety_relevant=True, order=1),
            InspectionItemDef(id="testigos", label="Testigos en tablero", description="Luces de avería encendidas", is_safety_relevant=True, order=2),
            InspectionItemDef(id="luces", label="Sistema de iluminación", description="Luces exteriores completas", is_safety_relevant=True, order=3),
            InspectionItemDef(id="sensores", label="Sensores de aparcamiento", description="Funcionamiento, rotos", order=4),
            InspectionItemDef(id="pantalla", label="Pantalla / Infoentretenimiento", description="Táctil, navegación, conectividad", order=5),
            InspectionItemDef(id="sonido", label="Sistema de sonido", description="Altavoces, mandos, calidad", order=6),
            InspectionItemDef(id="bluetooth", label="Bluetooth / Manos libres", description="Conexión, micrófono", order=7),
            InspectionItemDef(id="camara", label="Cámaras (trasera/360)", description="Calidad imagen, enfoque", order=8),
            InspectionItemDef(id="ordenador", label="Ordenador de a bordo", description="Consumos, autonomía, funciones", order=9),
        ],
    ),
    InspectionCategoryDef(
        id="neumaticos",
        label="Neumáticos",
        icon="⚪",
        description="Revisión de neumáticos y ruedas",
        order=5,
        items=[
            InspectionItemDef(id="profundidad", label="Profundidad del dibujo", description="Desgaste, medida en mm", is_safety_relevant=True, order=1),
            InspectionItemDef(id="presion", label="Presión correcta", description="Presión recomendada en frío", is_safety_relevant=True, order=2),
            InspectionItemDef(id="desgaste", label="Desgaste irregular", description="Señales de mala alineación / suspensión", is_safety_relevant=True, order=3),
            InspectionItemDef(id="fecha", label="Fecha de fabricación", description="Código DOT, antigüedad", is_safety_relevant=True, order=4),
            InspectionItemDef(id="golpes", label="Golpes / Abultamientos", description="Deformaciones en flanco o banda", is_safety_relevant=True, order=5),
            InspectionItemDef(id="valvulas", label="Válvulas y tapones", description="Estado correcto, fugas", order=6),
            InspectionItemDef(id="rueda_repuesto", label="Rueda de repuesto", description="Estado, presión, presencia", order=7),
        ],
    ),
    InspectionCategoryDef(
        id="frenos",
        label="Frenos",
        icon="🛑",
        description="Revisión del sistema de frenado",
        order=6,
        items=[
            InspectionItemDef(id="pastillas", label="Pastillas de freno", description="Grosor restante, desgaste irregular", is_safety_relevant=True, order=1),
            InspectionItemDef(id="discos", label="Discos de freno", description="Rayado, alabeo, grosor", is_safety_relevant=True, order=2),
            InspectionItemDef(id="liquido", label="Líquido de frenos", description="Nivel, color, fecha cambio", is_safety_relevant=True, order=3),
            InspectionItemDef(id="latiguillos", label="Latiguillos", description="Fugas, grietas, abombamiento", is_safety_relevant=True, order=4),
            InspectionItemDef(id="freno_mano", label="Freno de mano", description="Recorrido, retención en pendiente", is_safety_relevant=True, order=5),
            InspectionItemDef(id="abs", label="ABS / ESP", description="Testigo, funcionamiento", is_safety_relevant=True, order=6),
            InspectionItemDef(id="servofreno", label="Servofreno", description="Asistencia, pedal duro", is_safety_relevant=True, order=7),
        ],
    ),
    InspectionCategoryDef(
        id="suspension",
        label="Suspensión",
        icon="🏎️",
        description="Revisión del sistema de suspensión y dirección",
        order=7,
        items=[
            InspectionItemDef(id="amortiguadores", label="Amortiguadores", description="Fugas, pérdida de eficacia", is_safety_relevant=True, order=1),
            InspectionItemDef(id="muelles", label="Muelles / Ballestas", description="Roturas, asentamiento", is_safety_relevant=True, order=2),
            InspectionItemDef(id="silentblocks", label="Silentblocks / Bujes", description="Desgaste, roturas", order=3),
            InspectionItemDef(id="rotulas", label="Rótulas de suspensión", description="Holgura, protección", is_safety_relevant=True, order=4),
            InspectionItemDef(id="direccion", label="Dirección", description="Holgura, ruidos, asistencia", is_safety_relevant=True, order=5),
            InspectionItemDef(id="alineacion", label="Alineación", description="Desgaste neumáticos, volante descentrado", order=6),
            InspectionItemDef(id="barra_estabilizadora", label="Barra estabilizadora", description="Bujes, bieletas", order=7),
        ],
    ),
    InspectionCategoryDef(
        id="documentacion",
        label="Documentación",
        icon="📄",
        description="Revisión de la documentación del vehículo",
        order=8,
        items=[
            InspectionItemDef(id="permiso_circulacion", label="Permiso de circulación", description="Original, datos correctos", order=1, has_cost_estimate=False, allows_photos=False),
            InspectionItemDef(id="ficha_tecnica", label="Ficha técnica", description="Original, coincidencia datos", order=2, has_cost_estimate=False, allows_photos=False),
            InspectionItemDef(id="itv", label="ITV vigente", description="Fecha caducidad, resultados", is_safety_relevant=True, order=3, has_cost_estimate=False, allows_photos=False),
            InspectionItemDef(id="historial", label="Historial de mantenimiento", description="Facturas, sellos, libro", order=4, has_cost_estimate=False),
            InspectionItemDef(id="propietarios", label="Número de propietarios", description="Coincidencia con documentación", order=5, has_cost_estimate=False),
            InspectionItemDef(id="carga", label="Cargas / Embargos", description="Informe DGT / Carfax", order=6, has_cost_estimate=False),
            InspectionItemDef(id="seguro", label="Seguro", description="Tipo, cobertura, vigencia", order=7, has_cost_estimate=False),
        ],
    ),
    InspectionCategoryDef(
        id="prueba_dinamica",
        label="Prueba dinámica",
        icon="🏁",
        description="Prueba de conducción del vehículo",
        order=9,
        items=[
            InspectionItemDef(id="arranque", label="Arranque en frío", description="Facilidad, ruidos, humo", is_safety_relevant=True, order=1),
            InspectionItemDef(id="aceleracion", label="Aceleración", description="Respuesta, tirones, potencia", is_safety_relevant=True, order=2),
            InspectionItemDef(id="frenado", label="Frenado en movimiento", description="Potencia, vibraciones, rectitud", is_safety_relevant=True, order=3),
            InspectionItemDef(id="caja_cambios", label="Caja de cambios", description="Suavidad, ruidos, patinaje", is_safety_relevant=True, order=4),
            InspectionItemDef(id="embrague", label="Embrague", description="Punto de fricción, patinaje", is_safety_relevant=True, order=5),
            InspectionItemDef(id="direccion_dinamica", label="Dirección en marcha", description="Precisión, vibraciones", is_safety_relevant=True, order=6),
            InspectionItemDef(id="suspension_dinamica", label="Suspensión en marcha", description="Confort, ruidos, estabilidad", is_safety_relevant=True, order=7),
            InspectionItemDef(id="ruidos_marcha", label="Ruidos en marcha", description="Rodamientos, transmisión, viento", order=8),
            InspectionItemDef(id="consumo", label="Consumo indicado", description="Consumo instantáneo vs esperado", order=9),
            InspectionItemDef(id="emisiones", label="Emisiones / Humo", description="Humo visible, olor", is_safety_relevant=True, order=10),
        ],
    ),
]


# =============================================================================
# Utilidades
# =============================================================================


def get_category_def(category_id: str) -> InspectionCategoryDef | None:
    """Obtiene la definición de una categoría por su ID."""
    for cat in INSPECTION_CATEGORIES:
        if cat.id == category_id:
            return cat
    return None


def get_item_def(category_id: str, item_id: str) -> InspectionItemDef | None:
    """Obtiene la definición de un ítem dentro de una categoría."""
    cat = get_category_def(category_id)
    if cat is None:
        return None
    for item in cat.items:
        if item.id == item_id:
            return item
    return None


def get_total_items_count() -> int:
    """Devuelve el número total de puntos de inspección en el catálogo."""
    return sum(len(cat.items) for cat in INSPECTION_CATEGORIES)


# =============================================================================
# Umbrales de severidad
# =============================================================================

SEVERITY_MAP: dict[InspectionItemStatus, SeverityLevel] = {
    InspectionItemStatus.GOOD: SeverityLevel.LOW,
    InspectionItemStatus.WARNING: SeverityLevel.MEDIUM,
    InspectionItemStatus.BAD: SeverityLevel.HIGH,
    InspectionItemStatus.UNKNOWN: SeverityLevel.LOW,
}

SEVERITY_WEIGHT: dict[SeverityLevel, int] = {
    SeverityLevel.LOW: 0,
    SeverityLevel.MEDIUM: 3,
    SeverityLevel.HIGH: 7,
    SeverityLevel.CRITICAL: 10,
}

# Umbral de severidad para considerar defecto crítico
CRITICAL_SEVERITY_THRESHOLD: int = 7

# Coste base por defecto HIGH sin coste manual
DEFAULT_REPAIR_COST_HIGH: float = 500.0
DEFAULT_REPAIR_COST_MEDIUM: float = 150.0
