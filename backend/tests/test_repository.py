"""Tests for ownership-aware repository access guards."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Analysis, Base, Claim, Evidence
from app.db.repository import AnalysisRepository, RequestOwner


async def _build_session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return session_factory()


@pytest.mark.asyncio
async def test_repository_blocks_cross_user_reads():
    session = await _build_session()
    repo = AnalysisRepository(session)

    owner_a = RequestOwner(is_guest=False, user_id="user-a")
    owner_b = RequestOwner(is_guest=False, user_id="user-b")

    analysis_a = await repo.create_analysis(owner_a)
    await session.commit()

    visible_to_a = await repo.get_analysis(analysis_a.id, owner_a)
    hidden_from_b = await repo.get_analysis(analysis_a.id, owner_b)

    assert visible_to_a is not None
    assert hidden_from_b is None

    await session.close()


@pytest.mark.asyncio
async def test_repository_blocks_cross_session_reads_for_guests():
    session = await _build_session()
    repo = AnalysisRepository(session)

    guest_a = RequestOwner(is_guest=True, guest_session_id="guest-a")
    guest_b = RequestOwner(is_guest=True, guest_session_id="guest-b")

    analysis_a = await repo.create_analysis(guest_a)
    await session.commit()

    visible_to_guest_a = await repo.get_analysis(analysis_a.id, guest_a)
    hidden_from_guest_b = await repo.get_analysis(analysis_a.id, guest_b)

    assert visible_to_guest_a is not None
    assert hidden_from_guest_b is None

    await session.close()


@pytest.mark.asyncio
async def test_repository_update_status_scoped_to_owner():
    session = await _build_session()
    repo = AnalysisRepository(session)

    owner_a = RequestOwner(is_guest=False, user_id="user-a")
    owner_b = RequestOwner(is_guest=False, user_id="user-b")

    analysis_a = await repo.create_analysis(owner_a)
    await session.commit()

    updated = await repo.update_status(analysis_a.id, owner_b, status="COMPLETED")
    await session.commit()

    reloaded = await repo.get_analysis(analysis_a.id, owner_a)

    assert updated is False
    assert reloaded is not None
    assert reloaded.status == "PENDING"

    await session.close()


def test_request_owner_validation():
    with pytest.raises(ValueError):
        RequestOwner(is_guest=False)

    with pytest.raises(ValueError):
        RequestOwner(is_guest=True)

    with pytest.raises(ValueError):
        RequestOwner(is_guest=False, user_id="u-1", guest_session_id="g-1")

    with pytest.raises(ValueError):
        RequestOwner(is_guest=True, user_id="u-1", guest_session_id="g-1")


@pytest.mark.asyncio
async def test_delete_guest_session_removes_claims_evidence_and_history():
    session = await _build_session()
    repo = AnalysisRepository(session)

    guest_owner = RequestOwner(is_guest=True, guest_session_id="guest-to-delete")
    analysis = await repo.create_analysis(guest_owner, status="COMPLETED")

    claim = Claim(analysis_id=analysis.id, text="Claim", confidence=0.5, status="UNSUPPORTED")
    session.add(claim)
    await session.flush()

    evidence = Evidence(
        claim_id=claim.id,
        snippet="Snippet",
        source_url="https://example.com",
        source_title="Example",
        relevance_score=0.7,
        source_type="WEB_SEARCH",
        polarity=None,
    )
    session.add(evidence)
    await session.commit()

    deleted = await repo.delete_guest_session_analyses("guest-to-delete")
    await session.commit()

    remaining_analyses = (await session.execute(select(Analysis))).scalars().all()
    remaining_claims = (await session.execute(select(Claim))).scalars().all()
    remaining_evidence = (await session.execute(select(Evidence))).scalars().all()
    history = await repo.list_analyses(guest_owner)

    assert deleted == 1
    assert remaining_analyses == []
    assert remaining_claims == []
    assert remaining_evidence == []
    assert history == []

    await session.close()


@pytest.mark.asyncio
async def test_delete_expired_guest_analyses_respects_cutoff():
    session = await _build_session()
    repo = AnalysisRepository(session)

    guest_owner = RequestOwner(is_guest=True, guest_session_id="guest-ttl")
    recent = await repo.create_analysis(guest_owner)
    expired = await repo.create_analysis(guest_owner)

    now = datetime.now(timezone.utc)
    recent.created_at = now - timedelta(hours=1)
    expired.created_at = now - timedelta(hours=30)
    await session.commit()

    deleted = await repo.delete_expired_guest_analyses(now - timedelta(hours=24))
    await session.commit()

    remaining_ids = {
        item.id for item in (await session.execute(select(Analysis))).scalars().all()
    }

    assert deleted == 1
    assert recent.id in remaining_ids
    assert expired.id not in remaining_ids

    await session.close()


@pytest.mark.asyncio
async def test_list_authenticated_history_excludes_guest_and_other_users():
    session = await _build_session()
    repo = AnalysisRepository(session)

    await repo.create_analysis(RequestOwner(is_guest=False, user_id="user-a"), status="COMPLETED")
    await repo.create_analysis(RequestOwner(is_guest=False, user_id="user-a"), status="FAILED")
    await repo.create_analysis(RequestOwner(is_guest=False, user_id="user-b"), status="COMPLETED")
    await repo.create_analysis(RequestOwner(is_guest=True, guest_session_id="guest-a"), status="COMPLETED")
    await session.commit()

    history = await repo.list_authenticated_history("user-a", limit=10, offset=0)

    assert len(history) == 2
    assert all(item.user_id == "user-a" for item in history)
    assert all(item.is_guest is False for item in history)

    await session.close()
