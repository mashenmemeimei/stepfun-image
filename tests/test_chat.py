"""Tests for the text chat completion client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from stepfun_audio.chat import StepFunChatClient, StepFunChatConfig


@pytest.fixture
def client() -> StepFunChatClient:
    return StepFunChatClient(
        StepFunChatConfig(api_key="test-key", base_url="https://x.example/v1")
    )


def test_chat_sends_messages_and_returns_assistant_text(client):
    payload = {"choices": [{"message": {"role": "assistant", "content": "没事的"}}]}
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None

    with patch("stepfun_audio.chat.requests.post", return_value=resp) as post:
        out = client.chat(
            [{"role": "user", "content": "今天有点闷"}],
            temperature=0.7,
            max_tokens=128,
        )

    assert out == "没事的"
    args, kwargs = post.call_args
    assert args[0] == "https://x.example/v1/chat/completions"
    body = kwargs["json"]
    assert body["model"] == "stepaudio-2.5-chat"
    # Modalities must be text-only for stepaudio-2.5-chat
    assert body["modalities"] == ["text"]
    assert body["messages"] == [{"role": "user", "content": "今天有点闷"}]
    assert body["temperature"] == 0.7
    assert body["max_tokens"] == 128
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_chat_omits_optional_params_when_none(client):
    payload = {"choices": [{"message": {"content": "ok"}}]}
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None

    with patch("stepfun_audio.chat.requests.post", return_value=resp) as post:
        client.chat([{"role": "user", "content": "hi"}])

    body = post.call_args.kwargs["json"]
    assert "temperature" not in body
    assert "max_tokens" not in body


def test_chat_merges_extra_body(client):
    payload = {"choices": [{"message": {"content": "ok"}}]}
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None

    with patch("stepfun_audio.chat.requests.post", return_value=resp) as post:
        client.chat(
            [{"role": "user", "content": "hi"}],
            extra_body={"user": "u-123", "metadata": {"tag": "x"}},
        )

    body = post.call_args.kwargs["json"]
    assert body["user"] == "u-123"
    assert body["metadata"] == {"tag": "x"}
