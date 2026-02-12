"""add chat context fields

Revision ID: 5e6c9f0e14d5
Revises: a5c220713937
Create Date: 2025-11-23 05:45:34.906521

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import open_webui.internal.db



# Alembic will have set these for you:
revision = "5e6c9f0e14d5"
down_revision = "a5c220713937"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Existing columns and indexes
    cols = [c["name"] for c in insp.get_columns("chat")]
    indexes = [ix["name"] for ix in insp.get_indexes("chat")]

    # 1) Columns (only add if they don't exist yet)

    if "context_type" not in cols:
        op.add_column("chat", sa.Column("context_type", sa.String(), nullable=True))

    # Backfill any NULLs to 'general' (safe to run even if column already existed)
    op.execute("UPDATE chat SET context_type = 'general' WHERE context_type IS NULL")

    if "course_id" not in cols:
        op.add_column("chat", sa.Column("course_id", sa.String(), nullable=True))

    if "lab_id" not in cols:
        op.add_column("chat", sa.Column("lab_id", sa.String(), nullable=True))

    # 2) Indexes (only create if they don't exist yet)

    if "user_id_context_type_idx" not in indexes:
        op.create_index(
            "user_id_context_type_idx",
            "chat",
            ["user_id", "context_type"],
            unique=False,
        )

    if "context_type_course_lab_idx" not in indexes:
        op.create_index(
            "context_type_course_lab_idx",
            "chat",
            ["context_type", "course_id", "lab_id"],
            unique=False,
        )


def downgrade() -> None:
    op.drop_index("context_type_course_lab_idx", table_name="chat")
    op.drop_index("user_id_context_type_idx", table_name="chat")

    op.drop_column("chat", "lab_id")
    op.drop_column("chat", "course_id")
    op.drop_column("chat", "context_type")
