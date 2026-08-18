"""add performance indexes for common queries

Revision ID: p2q3r4s5t6u7
Revises: o1p2q3r4s5t6
Create Date: 2026-08-18

BACKEND.PERF.1: índices para las consultas más frecuentes del pipeline:

- vehicles.brand/model y vehicles.year: búsqueda y filtrado de vehículos.
- vehicles.price: ranking por precio y rango de presupuesto.
- opportunities.recommendation: filtro por recomendación del listado.
  (opportunities no tiene columna user_id; el scoping por usuario se hace
  por join con vehicles.user_id, que ya está indexado.)

Estos índices son no-clúster y de baja cardinalidad en parte, por lo que
no afectan a la escritura de forma relevante a escala personal.
"""

from alembic import op


revision = "p2q3r4s5t6u7"
down_revision = "o1p2q3r4s5t6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_vehicles_brand_model", "vehicles", ["brand", "model"])
    op.create_index("ix_vehicles_year", "vehicles", ["year"])
    op.create_index("ix_vehicles_price", "vehicles", ["price"])
    op.create_index(
        "ix_opportunities_recommendation",
        "opportunities",
        ["recommendation"],
    )


def downgrade() -> None:
    op.drop_index("ix_opportunities_recommendation", table_name="opportunities")
    op.drop_index("ix_vehicles_price", table_name="vehicles")
    op.drop_index("ix_vehicles_year", table_name="vehicles")
    op.drop_index("ix_vehicles_brand_model", table_name="vehicles")