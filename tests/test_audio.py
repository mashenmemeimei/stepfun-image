"""Tests for TTS + ASR (audio.py). All network calls are mocked."""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from stepfun_audio.audio import StepFunAudioClient, StepFunAudioConfig
from stepfun_audio.models import (
    DEFAULT_TTS_MODEL,
    DEFAULT_TTS_VOICE,
    TTS_RESPONSE_FORMATS,
    TTS_SAMPLE_RATES,
)


@pytest.fixture
def client() -> StepFunAudioClient:
    return StepFunAudioClient(
        StepFunAudioConfig(api_key="test-key", base_url="https://x.example/v1")
    )


# ---- TTS ----

def test_tts_posts_correct_payload_and_returns_bytes(client):
    fake_mp3 = b"\xff\xfb\x90\x00" + b"\x00" * 64  # plausible MP3 frame header
    resp = MagicMock()
    resp.content = fake_mp3
    resp.raise_for_status.return_value = None

    with patch("stepfun_audio.audio.requests.post", return_value=resp) as post:
        out = client.text_to_speech(
            "你好世界",
            voice="cixingnansheng",
            instruction="语气温柔",
            response_format="mp3",
            sample_rate=24000,
        )

    assert out == fake_mp3
    args, kwargs = post.call_args
    assert args[0] == "https://x.example/v1/audio/speech"
    body = kwargs["json"]
    assert body["model"] == DEFAULT_TTS_MODEL
    assert body["voice"] == DEFAULT_TTS_VOICE
    assert body["input"] == "你好世界"
    assert body["instruction"] == "语气温柔"
    assert body["response_format"] == "mp3"
    assert body["sample_rate"] == 24000
    assert body["speed_ratio"] == 1.0
    assert body["volume_ratio"] == 1.0
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_tts_rejects_invalid_format(client):
    with pytest.raises(ValueError, match="response_format"):
        client.text_to_speech("x", response_format="ogg")


def test_tts_rejects_invalid_sample_rate(client):
    with pytest.raises(ValueError, match="sample_rate"):
        client.text_to_speech("x", sample_rate=11025)


def test_tts_drops_instruction_when_none(client):
    resp = MagicMock()
    resp.content = b""
    resp.raise_for_status.return_value = None
    with patch("stepfun_audio.audio.requests.post", return_value=resp) as post:
        client.text_to_speech("hi")
    body = post.call_args.kwargs["json"]
    assert "instruction" not in body


# ---- ASR / SSE ----

def _sse_response(chunks: list[str]) -> MagicMock:
    """Build a mock requests.Response that yields SSE lines via iter_lines."""
    lines: list[str] = []
    for chunk in chunks:
        lines.append(f"data: {json.dumps({'text': chunk})}")
        lines.append("")  # event boundary
    lines.append("data: [DONE]")
    lines.append("")

    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.iter_lines.return_value = iter(lines)
    return resp


def test_asr_concatenates_sse_chunks(client, tmp_path):
    audio = tmp_path / "rec.pcm"
    audio.write_bytes(b"\x00" * 32000)  # 1s of silent 16kHz mono pcm_s16le

    resp = _sse_response(["你好", "，世界", "！"])

    with patch("stepfun_audio.audio.requests.post", return_value=resp) as post:
        text = client.transcribe(audio)

    assert text == "你好，世界！"

    # Verify request payload shape
    args, kwargs = post.call_args
    assert args[0] == "https://x.example/v1/audio/asr/sse"
    assert kwargs["stream"] is True
    assert kwargs["headers"]["Accept"] == "text/event-stream"

    body = kwargs["json"]
    assert body["audio"]["data"] == base64.b64encode(audio.read_bytes()).decode()
    fmt = body["audio"]["input"]["format"]
    assert fmt == {"type": "pcm", "codec": "pcm_s16le", "rate": 16000, "bits": 16, "channel": 1}
    tr = body["audio"]["input"]["transcription"]
    assert tr["model"] == "stepaudio-2.5-asr"
    assert tr["language"] == "zh"
    assert tr["enable_itn"] is True


def test_asr_missing_file_raises(client):
    with pytest.raises(FileNotFoundError):
        client.transcribe("/no/such/file.pcm")


def test_asr_skips_non_data_lines(client, tmp_path):
    audio = tmp_path / "rec.pcm"
    audio.write_bytes(b"\x00" * 32)

    lines = [
        "event: ready",
        "",
        ": keep-alive comment",
        "",
        "data: " + json.dumps({"text": "片段"}),
        "",
        "data: [DONE]",
        "",
    ]
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.iter_lines.return_value = iter(lines)

    with patch("stepfun_audio.audio.requests.post", return_value=resp):
        text = client.transcribe(audio)
    assert text == "片段"


# ---- constants sanity ----

def test_models_constants():
    assert "mp3" in TTS_RESPONSE_FORMATS
    assert 16000 in TTS_SAMPLE_RATES
    assert DEFAULT_TTS_MODEL.startswith("stepaudio")
    assert DEFAULT_TTS_VOICE  # non-empty
