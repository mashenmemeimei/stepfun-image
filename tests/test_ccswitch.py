"""Tests for the CCSwitch SQLite key loader."""

from __future__ import annotations

import os

import pytest

from stepfun_image.ccswitch import (
    KEY_ENV_VAR,
    load_api_key_from_ccswitch,
    resolve_api_key,
)


def test_env_var_wins_over_db(fake_ccswitch_db, monkeypatch):
    monkeypatch.setenv(KEY_ENV_VAR, "env-wins-token")
    assert resolve_api_key(fake_ccswitch_db) == "env-wins-token"


def test_loads_claude_token(fake_ccswitch_db):
    assert load_api_key_from_ccswitch(fake_ccswitch_db) == "claude-test-token-AAA"


def test_returns_none_for_missing_db(tmp_path):
    assert load_api_key_from_ccswitch(tmp_path / "nope.db") is None


def test_returns_none_when_no_stepfun(empty_db):
    assert load_api_key_from_ccswitch(empty_db) is None


def test_resolve_raises_without_any_source(empty_db, monkeypatch):
    monkeypatch.delenv(KEY_ENV_VAR, raising=False)
    # Make sure no real CCSwitch is auto-detected by pointing at an empty path
    # that does not exist.
    with pytest.raises(RuntimeError) as exc:
        resolve_api_key(empty_db.parent / "definitely-missing.db")
    assert "STEP_API_KEY" in str(exc.value)
