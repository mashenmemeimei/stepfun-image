"""Tests for the request-building logic (network calls mocked)."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, patch

import pytest

from stepfun_image.client import StepFunConfig, StepFunImageClient, _guess_mime


@pytest.fixture
def client() -> StepFunImageClient:
    cfg = StepFunConfig(api_key="test-key", base_url="https://x.example/v1")
    return StepFunImageClient(cfg)


def test_text_to_image_payload_and_decoding(client):
    fake_png_a = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    fake_png_b = b"\x89PNG\r\n\x1a\n" + b"\x01" * 32
    payload = {
        "data": [
            {"b64_json": base64.b64encode(fake_png_a).decode()},
            {"b64_json": base64.b64encode(fake_png_b).decode()},
        ]
    }

    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None

    with patch("stepfun_image.client.requests.post", return_value=resp) as post:
        blobs = client.text_to_image(
            "hi",
            seed=3,
            steps=10,
            cfg_scale=1.5,
            text_mode=False,
            size="1024x1024",
            n=2,
        )

    assert blobs == [fake_png_a, fake_png_b]  # mock returned 2 items

    # Verify the outbound request
    post.assert_called_once()
    args, kwargs = post.call_args
    assert args[0] == "https://x.example/v1/images/generations"
    body = kwargs["json"]
    assert body["model"] == "step-image-edit-2"
    assert body["prompt"] == "hi"
    assert body["seed"] == 3
    assert body["steps"] == 10
    assert body["cfg_scale"] == 1.5
    assert body["text_mode"] is False
    assert body["size"] == "1024x1024"
    assert body["n"] == 2
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_edit_image_uses_multipart_and_casts_numbers(tmp_path, client):
    fake_png = b"\x89PNG\r\n\x1a\n" + b"\x11" * 16
    payload = {"data": [{"b64_json": base64.b64encode(fake_png).decode()}]}

    in_file = tmp_path / "input.webp"
    in_file.write_bytes(b"RIFFfakewebp")

    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None

    with patch("stepfun_image.client.requests.post", return_value=resp) as post:
        blobs = client.edit_image(
            in_file, "red hat", seed=1, steps=8, cfg_scale=1.0, text_mode=True
        )

    assert blobs == [fake_png]
    args, kwargs = post.call_args
    assert args[0] == "https://x.example/v1/images/edits"
    # multipart form: file + form fields
    assert "files" in kwargs and "data" in kwargs
    data = kwargs["data"]
    assert data["model"] == "step-image-edit-2"
    assert data["prompt"] == "red hat"
    # numbers and bools are serialized as strings for multipart
    assert data["seed"] == "1"
    assert data["steps"] == "8"
    assert data["cfg_scale"] == "1.0"
    assert data["text_mode"] == "true"


def test_edit_missing_file_raises(client):
    with pytest.raises(FileNotFoundError):
        client.edit_image("/nope.webp", "x")


def test_mime_guessing(tmp_path):
    p = tmp_path / "a.png"
    p.write_bytes(b"x")
    assert _guess_mime(p) == "image/png"
    p2 = tmp_path / "a.jpeg"
    p2.write_bytes(b"x")
    assert _guess_mime(p2) == "image/jpeg"
