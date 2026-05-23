"""add pgvector extension and evidence embeddings table

Revision ID: 002
Revises: 001
Create Date: 2026-05-23 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, Sequence[str], None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with pgvector artifacts for evidence similarity search."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute(
            """
            CREATE TABLE IF NOT EXISTS evidence_embeddings (
                id TEXT PRIMARY KEY,
                snippet TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                embedding vector(384) NOT NULL
            )
            """
        )
        op.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_evidence_embeddings_embedding
            ON evidence_embeddings
            USING ivfflat (embedding vector_cosine_ops)
            """
        )
    else:
        # Keep SQLite and other non-PostgreSQL test databases operational.
        op.create_table(
            "evidence_embeddings",
            sa.Column("id", sa.Text(), nullable=False),
            sa.Column("snippet", sa.Text(), nullable=False),
            sa.Column("metadata", sa.Text(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("embedding", sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade() -> None:
    """Downgrade schema by removing pgvector artifacts safely."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_evidence_embeddings_embedding")
        op.execute("DROP TABLE IF EXISTS evidence_embeddings")
        op.execute("DROP EXTENSION IF EXISTS vector")
    else:
        op.drop_table("evidence_embeddings")
