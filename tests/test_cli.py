"""Tests for the argparse CLI surface (no network)."""

from __future__ import annotations

import io
import json
import sqlite3
import sys
from pathlib import Path

import pytest

from stepfun_image import cli
from stepfun_image.cli import build_parser, main


def _seed_db(db_path: Path, token: str) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE providers (
              id TEXT PRIMARY KEY,
              app_type TEXT NOT NULL,
              name TEXT NOT NULL,
              settings_config TEXT NOT NULL
            );
            """
        )
        conn.execute(
            "INSERT INTO providers(id, app_type, name, settings_config) VALUES (?,?,?,?)",
            (
                "u",
                "claude",
                "StepFun",
                json.dumps({"env": {"ANTHROPIC_AUTH_TOKEN": token}}),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_parser_t2i():
    args = build_parser().parse_args(["t2i", "hello", "--seed", "7"])
    assert args.cmd == "t2i"
    assert args.prompt == "hello"
    assert args.seed == 7
    assert args.text_mode is True


def test_parser_edit():
    args = build_parser().parse_args(
        ["edit", "in.webp", "red hat", "--no-text-mode", "--steps", "12"]
    )
    assert args.cmd == "edit"
    assert args.image == "in.webp"
    assert args.text_mode is False
    assert args.steps == 12


def test_whoami_prints_sources(capsys, tmp_path, monkeypatch):
    db = tmp_path / "cc.db"
    _seed_db(db, "secret-xyz")
    monkeypatch.delenv("STEP_API_KEY", raising=False)

    rc = main(["--db", str(db), "whoami"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "CCSwitch StepFun key: found" in out
    assert "sec..." in out or "xyz" in out  # masked preview


def test_missing_image_file(tmp_path):
    db = tmp_path / "cc.db"
    _seed_db(db, "tok")
    rc = main(
        [
            "--db",
            str(db),
            "edit",
            str(tmp_path / "missing.webp"),
            "add cat",
        ]
    )
    assert rc == 1  # client raises FileNotFoundError -> exit 1
