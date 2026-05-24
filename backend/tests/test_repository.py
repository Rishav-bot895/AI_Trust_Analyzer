"""Tests for ownership-aware repository access guards."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Analysis, Base, Claim, Evidence
from app.db.repository import AnalysisRepository, RequestOwner
from app.schemas.analysis import AnalysisRequest


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
async def test_create_analysis_returns_orm_object():
    session = await _build_session()
    repo = AnalysisRepository(session)
    owner = RequestOwner(is_guest=False, user_id="user-orm")

    payload = AnalysisRequest(
        prompt="Prompt",
        response="Response",
        model_name="model-x",
        include_comparison=True,
    )

    analysis = await repo.create_analysis(owner, request=payload, status="PENDING")
    await session.commit()

    assert isinstance(analysis, Analysis)
    assert analysis.id
    assert analysis.user_id == "user-orm"
    assert analysis.prompt == "Prompt"
    assert analysis.response == "Response"
    assert analysis.model_name == "model-x"
    assert analysis.include_comparison is True

    await session.close()


@pytest.mark.asyncio
async def test_get_analysis_unknown_returns_none():
    session = await _build_session()
    repo = AnalysisRepository(session)
    owner = RequestOwner(is_guest=False, user_id="user-unknown")

    found = await repo.get_analysis_for_requester(
        "00000000-0000-0000-0000-000000000000",
        owner,
    )

    assert found is None

    await session.close()


@pytest.mark.asyncio
async def test_update_analysis_result_persists():
    session = await _build_session()
    repo = AnalysisRepository(session)
    owner = RequestOwner(is_guest=False, user_id="user-update")

    analysis = await repo.create_analysis(owner)
    claim_id = "11111111-1111-1111-1111-111111111111"
    state = {
        "analysis_id": analysis.id,
        "prompt": "Prompt",
        "response": "Response",
        "model_name": "model-y",
        "claims": [],
        "verified_claims": [
            {
                "id": claim_id,
                "text": "A verifiable claim",
                "confidence": 0.82,
                "status": "SUPPORTED",
                "claim_index": 0,
            }
        ],
        "evidence": [
            {
                "claim_id": claim_id,
                "snippet": "Supporting source snippet",
                "source_url": "https://example.com/source",
                "source_title": "Example Source",
                "relevance_score": 0.9,
                "source_type": "WEB_SEARCH",
                "polarity": "supporting",
            }
        ],
        "critique": "Looks accurate.",
        "trust_score": 91.5,
        "hallucination_risk": "LOW",
        "verdict": "Trustworthy",
        "timeline": [{"agent": "extractor"}],
        "error": None,
    }

    updated = await repo.update_analysis_result(analysis.id, owner, state)
    await session.commit()

    assert updated is not None
    reloaded = await repo.get_analysis_for_requester(analysis.id, owner)
    assert reloaded is not None
    assert reloaded.status == "COMPLETED"
    assert reloaded.trust_score == 91.5
    assert reloaded.verdict == "Trustworthy"
    assert "extractor" in (reloaded.timeline or "")
    assert len(reloaded.claims) == 1
    assert len(reloaded.claims[0].evidence) == 1

    await session.close()


@pytest.mark.asyncio
async def test_get_claims_filter_works():
    session = await _build_session()
    repo = AnalysisRepository(session)
    owner = RequestOwner(is_guest=False, user_id="user-claims")

    analysis = await repo.create_analysis(owner)
    await repo.create_claims(
        analysis.id,
        [
            {"text": "Supported claim", "status": "SUPPORTED", "claim_index": 0},
            {"text": "Unsupported claim", "status": "UNSUPPORTED", "claim_index": 1},
        ],
    )
    await session.commit()

    all_claims = await repo.get_claims(analysis.id, owner)
    unsupported = await repo.get_claims(analysis.id, owner, status="UNSUPPORTED")

    assert len(all_claims) == 2
    assert len(unsupported) == 1
    assert unsupported[0].status == "UNSUPPORTED"

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
