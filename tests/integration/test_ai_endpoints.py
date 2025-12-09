import os
from typing import List

import pytest

ALLOWED_OPENROUTER_MODELS = [
    ("Grok Code Fast 1", "x-ai/grok-code-fast-1"),
    ("Claude Sonnet 4.5", "anthropic/claude-sonnet-4.5"),
    ("Gemini 2.5 Flash", "google/gemini-2.5-flash"),
    ("MiniMax M2 (free)", "minimax/minimax-m2:free"),
    ("Gemini 2.5 Pro", "google/gemini-2.5-pro"),
    ("Grok 4 Fast", "x-ai/grok-4-fast"),
    ("Gemini 2.0 Flash", "google/gemini-2.0-flash-001"),
    ("Claude Sonnet 4", "anthropic/claude-sonnet-4"),
    ("Gemini 2.5 Flash Lite", "google/gemini-2.5-flash-lite"),
]


def _require_env_vars(*names: str) -> None:
    missing = [name for name in names if not os.getenv(name)]
    if missing:
        pytest.skip(f"Missing required environment variables for live test: {', '.join(missing)}")


def _ai_url(base_url: str, path: str) -> str:
    return f"{base_url}/api/v1/ai{path}"


def test_typing_suggestions_live(http_session, base_url, default_timeout) -> None:
    _require_env_vars("OPENAI_API_KEY")

    payload = {
        "prefix": "je vais partir en voyage à",
        "suffix": "",
        "language": "fr",
        "instructions": "Complète la phrase naturellement.",
        "temperature": 0.2,
    }
    response = http_session.post(
        _ai_url(base_url, "/typing-suggestions"),
        json=payload,
        timeout=default_timeout,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["model"].startswith("gpt-5-nano"), f"Unexpected model: {data['model']}"
    assert data["suggestion"], "Suggestion should not be empty"
    assert data["stubbed"] is False


def test_standard_response_live(http_session, base_url, default_timeout) -> None:
    _require_env_vars("OPENAI_API_KEY")

    payload = {
        "prompt": "Provide a short comparison between Python lists and tuples.",
        "instructions": "Answer in two concise bullet points.",
    }
    response = http_session.post(
        _ai_url(base_url, "/standard-response"),
        json=payload,
        timeout=default_timeout,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["model"] == "gpt-5-mini-2025-08-07"
    assert data["output"], "Output should not be empty"
    assert data["stubbed"] is False


def test_deep_reasoning_live(http_session, base_url, default_timeout) -> None:
    _require_env_vars("OPENAI_API_KEY")

    payload = {
        "question": "How can a manufacturing company reduce lead time without increasing inventory?",
        "context": "Consider suppliers, internal processes, and technology investments.",
        "expected_format": "Provide a numbered list of steps.",
    }
    response = http_session.post(
        _ai_url(base_url, "/deep-reasoning"),
        json=payload,
        timeout=default_timeout,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["model"] == "gpt-5-2025-08-07"
    assert data["effort"] == "high"
    assert data["answer"], "Answer should not be empty"
    assert data["stubbed"] is False


def test_streaming_response_live(http_session, base_url, default_timeout) -> None:
    _require_env_vars("OPENAI_API_KEY")

    payload = {
        "prompt": "List three quick tips for staying productive while working remotely.",
        "instructions": "Keep each tip under 15 words.",
    }

    chunks: List[str] = []
    with http_session.post(
        _ai_url(base_url, "/streaming-response"),
        json=payload,
        stream=True,
        timeout=default_timeout,
    ) as response:
        assert response.status_code == 200, response.text

        for line in response.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            content = line[len("data:") :].strip()
            if content == "[DONE]":
                break
            chunks.append(content)

    assert chunks, "Streaming response returned no content"
    assert not any(chunk.startswith("[ERROR]") for chunk in chunks), f"Streaming error received: {chunks}"


@pytest.mark.parametrize("preset", ["small", "large", "reasoning"])
def test_sample_response_live(http_session, base_url, default_timeout, preset: str) -> None:
    _require_env_vars("OPENAI_API_KEY")

    payload = {
        "preset": preset,
        "instructions": "Respond enthusiastically.",
        "input": "What's a compelling reason to adopt AI assistants in customer support?",
    }
    response = http_session.post(
        _ai_url(base_url, "/sample-response"),
        json=payload,
        timeout=default_timeout,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["preset"] == preset
    assert data["model"], "Model should be populated"
    assert data["output"], "Output text should not be empty"
    assert data["stubbed"] is False


def test_openrouter_response_live(http_session, base_url, default_timeout) -> None:
    _require_env_vars("OPENROUTER_API_KEY")

    payload = {
        "prompt": "Summarize the main differences between async and multithreaded programming.",
        "models": ["Grok Code Fast 1"],
        "instructions": "Respond with three bullet points.",
        "temperature": 0.3,
    }
    response = http_session.post(
        _ai_url(base_url, "/openrouter-response"),
        json=payload,
        timeout=default_timeout,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["requested_models"] == ["Grok Code Fast 1"]
    allowed_slugs = {slug for _, slug in ALLOWED_OPENROUTER_MODELS}
    assert data["selected_model"] in allowed_slugs, f"Unexpected model returned: {data['selected_model']}"
    assert data["output"], "OpenRouter output should not be empty"
    assert data["stubbed"] is False
