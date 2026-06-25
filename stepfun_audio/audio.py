"""TTS and ASR clients for StepFun StepAudio 2.5.

Endpoints:
- TTS (HTTP, non-streaming):  POST {base}/audio/speech
- ASR (HTTP + SSE stream):    POST {base}/audio/asr/sse
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import requests

# Reuse the CCSwitch-aware key loader from the image package.
from stepfun_image.ccswitch import resolve_api_key

from .models import (
    DEFAULT_ASR_MODEL,
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_VOICE,
    TTS_RESPONSE_FORMATS,
    TTS_SAMPLE_RATES,
)

DEFAULT_BASE_URL = "https://api.stepfun.com/step_plan/v1"


@dataclass
class StepFunAudioConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    timeout: int = 120

    @classmethod
    def auto(cls, db_path: str | os.PathLike | None = None) -> "StepFunAudioConfig":
        return cls(api_key=resolve_api_key(db_path))


class StepFunAudioClient:
    def __init__(self, config: StepFunAudioConfig | None = None) -> None:
        self.config = config or StepFunAudioConfig.auto()

    # ---- helpers ----
    def _headers(self, *, stream: bool = False) -> dict[str, str]:
        h = {"Authorization": f"Bearer {self.config.api_key}"}
        if stream:
            h["Accept"] = "text/event-stream"
        return h

    # ---- TTS (HTTP non-streaming) ----
    def text_to_speech(
        self,
        text: str,
        *,
        model: str = DEFAULT_TTS_MODEL,
        voice: str = DEFAULT_TTS_VOICE,
        instruction: str | None = None,
        response_format: str = "mp3",
        sample_rate: int = 24000,
        speed_ratio: float = 1.0,
        volume_ratio: float = 1.0,
    ) -> bytes:
        """Synthesise speech from ``text`` and return raw audio bytes.

        ``response_format`` must be one of ``TTS_RESPONSE_FORMATS``.
        ``sample_rate`` must be one of ``TTS_SAMPLE_RATES``.
        """
        if response_format not in TTS_RESPONSE_FORMATS:
            raise ValueError(
                f"response_format must be one of {TTS_RESPONSE_FORMATS}, "
                f"got {response_format!r}"
            )
        if sample_rate not in TTS_SAMPLE_RATES:
            raise ValueError(
                f"sample_rate must be one of {TTS_SAMPLE_RATES}, got {sample_rate!r}"
            )

        body: dict = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": response_format,
        }
        if instruction:
            body["instruction"] = instruction
        body["sample_rate"] = sample_rate
        body["speed_ratio"] = speed_ratio
        body["volume_ratio"] = volume_ratio

        resp = requests.post(
            f"{self.config.base_url}/audio/speech",
            headers={**self._headers(), "Content-Type": "application/json"},
            json=body,
            timeout=self.config.timeout,
        )
        resp.raise_for_status()
        return resp.content

    # ---- ASR (HTTP + SSE) ----
    def transcribe(
        self,
        audio_path: str | os.PathLike,
        *,
        model: str = DEFAULT_ASR_MODEL,
        language: str = "zh",
        enable_itn: bool = True,
        sample_rate: int = 16000,
        bits: int = 16,
        channels: int = 1,
    ) -> str:
        """Transcribe an audio file and return the full text.

        Internally calls the SSE endpoint and accumulates the streamed
        transcription chunks.
        """
        path = Path(audio_path)
        if not path.exists():
            raise FileNotFoundError(path)

        audio_bytes = path.read_bytes()
        body = {
            "audio": {
                "data": base64.b64encode(audio_bytes).decode(),
                "input": {
                    "transcription": {
                        "model": model,
                        "language": language,
                        "enable_itn": enable_itn,
                    },
                    "format": {
                        "type": "pcm",
                        "codec": "pcm_s16le",
                        "rate": sample_rate,
                        "bits": bits,
                        "channel": channels,
                    },
                },
            }
        }

        resp = requests.post(
            f"{self.config.base_url}/audio/asr/sse",
            headers={**self._headers(stream=True), "Content-Type": "application/json"},
            json=body,
            stream=True,
            timeout=self.config.timeout,
        )
        resp.raise_for_status()
        return "".join(self._iter_sse_text(resp))

    @staticmethod
    def _iter_sse_text(resp: requests.Response) -> Iterator[str]:
        """Yield text fragments from an SSE response.

        Each ``data:`` line is expected to be JSON with a ``text`` field
        (the documented StepFun shape). Lines starting with ``data:`` are
        parsed; blank lines (event boundaries) are skipped.
        """
        for raw in resp.iter_lines(decode_unicode=True):
            if not raw or not raw.startswith("data:"):
                continue
            payload = raw[len("data:") :].strip()
            if payload == "[DONE]":
                return
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            text = event.get("text") or event.get("data", {}).get("text")
            if text:
                yield text
