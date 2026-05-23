"""harden auth/vector schema and persist analysis inputs

Revision ID: 004
Revises: 003
Create Date: 2026-05-23 22:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, Sequence[str], None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add analysis input fields and ownership-scoped vector metadata columns."""
    op.add_column("analyses", sa.Column("prompt", sa.Text(), nullable=True))
    op.add_column("analyses", sa.Column("response", sa.Text(), nullable=True))
    op.add_column("analyses", sa.Column("model_name", sa.String(length=128), nullable=True))
    op.add_column(
        "analyses",
        sa.Column("include_comparison", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.add_column("evidence_embeddings", sa.Column("evidence_id", sa.Text(), nullable=True))
    op.add_column("evidence_embeddings", sa.Column("user_id", sa.Text(), nullable=True))
    op.add_column("evidence_embeddings", sa.Column("guest_session_id", sa.Text(), nullable=True))
    op.add_column(
        "evidence_embeddings",
        sa.Column("is_guest", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.create_index("ix_evidence_embeddings_user_id", "evidence_embeddings", ["user_id"], unique=False)
    op.create_index(
        "ix_evidence_embeddings_guest_session_id",
        "evidence_embeddings",
        ["guest_session_id"],
        unique=False,
    )
    op.create_index("ix_evidence_embeddings_is_guest", "evidence_embeddings", ["is_guest"], unique=False)


def downgrade() -> None:
    """Revert hardening schema additions."""
    op.drop_index("ix_evidence_embeddings_is_guest", table_name="evidence_embeddings")
    op.drop_index("ix_evidence_embeddings_guest_session_id", table_name="evidence_embeddings")
    op.drop_index("ix_evidence_embeddings_user_id", table_name="evidence_embeddings")

    op.drop_column("evidence_embeddings", "is_guest")
    op.drop_column("evidence_embeddings", "guest_session_id")
    op.drop_column("evidence_embeddings", "user_id")
    op.drop_column("evidence_embeddings", "evidence_id")

    op.drop_column("analyses", "include_comparison")
    op.drop_column("analyses", "model_name")
    op.drop_column("analyses", "response")
    op.drop_column("analyses", "prompt")
