"""add ownership columns to analyses

Revision ID: 003
Revises: 002
Create Date: 2026-05-23 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, Sequence[str], None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ownership markers used for requester-scoped access controls."""
    op.add_column("analyses", sa.Column("user_id", sa.String(length=255), nullable=True))
    op.add_column("analyses", sa.Column("guest_session_id", sa.String(length=128), nullable=True))
    op.add_column(
        "analyses",
        sa.Column("is_guest", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_index("ix_analyses_user_id", "analyses", ["user_id"], unique=False)
    op.create_index("ix_analyses_guest_session_id", "analyses", ["guest_session_id"], unique=False)
    op.create_index("ix_analyses_is_guest", "analyses", ["is_guest"], unique=False)


def downgrade() -> None:
    """Remove ownership markers and related indexes."""
    op.drop_index("ix_analyses_is_guest", table_name="analyses")
    op.drop_index("ix_analyses_guest_session_id", table_name="analyses")
    op.drop_index("ix_analyses_user_id", table_name="analyses")

    op.drop_column("analyses", "is_guest")
    op.drop_column("analyses", "guest_session_id")
    op.drop_column("analyses", "user_id")
