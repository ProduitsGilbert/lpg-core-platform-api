import os

import pytest

CONVERSATION_ID = os.environ.get("TEST_CONVERSATION_ID", "cnv_1f9l8rq0")


def _require_front_env() -> None:
    if not os.getenv("FRONT_API_KEY"):
        pytest.skip("FRONT_API_KEY is not configured; skipping communications integration tests.")


def _communications_url(base_url: str, path: str) -> str:
    return f"{base_url}/api/v1/communications{path}"


def test_get_conversation(http_session, base_url, default_timeout) -> None:
    _require_front_env()

    response = http_session.get(
        _communications_url(base_url, f"/conversations/{CONVERSATION_ID}"),
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id"] == CONVERSATION_ID
    assert data["messages"], "Conversation should include messages"


def test_list_conversation_messages(http_session, base_url, default_timeout) -> None:
    _require_front_env()

    response = http_session.get(
        _communications_url(base_url, f"/conversations/{CONVERSATION_ID}/messages"),
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    messages = response.json()["data"]
    assert messages, "Expected at least one conversation message"


def test_get_last_conversation_message(http_session, base_url, default_timeout) -> None:
    _require_front_env()

    response = http_session.get(
        _communications_url(base_url, f"/conversations/{CONVERSATION_ID}/messages/last"),
        timeout=default_timeout,
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id"], "Last message should include an ID"
