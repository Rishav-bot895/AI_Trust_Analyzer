from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_fixtures_load(
    async_client: AsyncClient,
    test_db_session: AsyncSession,
    auth_headers: dict[str, str],
    guest_headers: dict[str, str],
) -> None:
    response = await async_client.get("/")
    db_result = await test_db_session.execute(text("SELECT 1"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert db_result.scalar_one() == 1
    assert auth_headers["Authorization"].startswith("Bearer ")
    assert "X-Guest-Session-Id" in guest_headers
    assert "X-Guest-Session-Token" in guest_headers


def test_mock_llm_returns_canned_response(mock_llm) -> None:  # noqa: ANN001
    response = mock_llm.invoke([{"role": "user", "content": "Extract claims"}])

    assert "Apollo 11 landed on the Moon in 1969" in response.content
    assert mock_llm.calls
