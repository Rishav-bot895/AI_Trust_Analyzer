"""SQLAlchemy ORM models for persisted analysis data."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class Analysis(Base):
    """Top-level analysis record."""

    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    hallucination_risk: Mapped[str | None] = mapped_column(String(32), nullable=True)
    critique: Mapped[str | None] = mapped_column(Text, nullable=True)
    verdict: Mapped[str | None] = mapped_column(Text, nullable=True)
    timeline: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    claims: Mapped[list[Claim]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class Claim(Base):
    """Claim extracted from an analyzed response."""

    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    analysis_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNVERIFIABLE")
    claim_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_span: Mapped[str | None] = mapped_column(Text, nullable=True)

    analysis: Mapped[Analysis] = relationship(back_populates="claims")
    evidence: Mapped[list[Evidence]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )


class Evidence(Base):
    """Evidence item used to verify or contradict a claim."""

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    claim_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False
    )
    snippet: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    polarity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    claim: Mapped[Claim] = relationship(back_populates="evidence")