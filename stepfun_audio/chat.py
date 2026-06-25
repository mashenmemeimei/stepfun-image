"""Text-only chat completion client for ``stepaudio-2.5-chat``.

The endpoint mirrors the OpenAI-compatible ``/chat/completions`` shape, but
``stepaudio-2.5-chat`` only supports the ``text`` modality — do not request
``audio`` here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import requests

from stepfun_image.ccswitch import resolve_api_key

from .audio import DEFAULT_BASE_URL
from .models import DEFAULT_CHAT_MODEL


@dataclass
class StepFunChatConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 60


class StepFunChatClient:
    def __init__(self, config: StepFunChatConfig | None = None) -> None:
        if config is None:
            config = StepFunChatConfig(api_key=resolve_api_key())
        self.config = config

    def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str = DEFAULT_CHAT_MODEL,
        temperature: float | None = None,
        max_tokens: int | None = None,
        extra_body: dict[str, Any] | None = None,
    ) -> str:
        """Run a chat completion and return the assistant message text."""
        body: dict[str, Any] = {
            "model": model,
            "modalities": ["text"],
            "messages": messages,
        }
        if temperature is not None:
            body["temperature"] = temperature
        if max_tokens is not None:
            body["max_tokens"] = max_tokens
        if extra_body:
            body.update(extra_body)

        resp = requests.post(
            f"{self.config.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=self.config.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
