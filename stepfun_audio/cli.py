"""CLI for StepFun audio: ``python -m stepfun_audio.cli tts|asr|chat``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .audio import StepFunAudioClient, StepFunAudioConfig
from .chat import StepFunChatClient, StepFunChatConfig
from .models import DEFAULT_ASR_MODEL, DEFAULT_CHAT_MODEL, DEFAULT_TTS_MODEL, DEFAULT_TTS_VOICE


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="stepfun-audio",
        description="CLI for StepFun TTS / ASR / Chat (Step Plan).",
    )
    p.add_argument("--db", help="Path to CCSwitch sqlite DB (auto-detected by default).")
    p.add_argument("--base-url", default="https://api.stepfun.com/step_plan/v1")

    sub = p.add_subparsers(dest="cmd", required=True)

    # ---- tts ----
    tts = sub.add_parser("tts", help="Text-to-speech (HTTP non-streaming)")
    tts.add_argument("text")
    tts.add_argument("-o", "--output")
    tts.add_argument("--model", default=DEFAULT_TTS_MODEL)
    tts.add_argument("--voice", default=DEFAULT_TTS_VOICE)
    tts.add_argument("--instruction", help='e.g. "语气温柔，语速偏慢"')
    tts.add_argument("--format", dest="response_format", default="mp3",
                     choices=("mp3", "wav", "pcm", "opus"))
    tts.add_argument("--sample-rate", type=int, default=24000)
    tts.add_argument("--speed", type=float, default=1.0)
    tts.add_argument("--volume", type=float, default=1.0)

    # ---- asr ----
    asr = sub.add_parser("asr", help="Speech-to-text (HTTP + SSE)")
    asr.add_argument("audio", help="Path to input audio (pcm_s16le recommended)")
    asr.add_argument("-o", "--output", help="Output text file (default: stdout)")
    asr.add_argument("--model", default=DEFAULT_ASR_MODEL)
    asr.add_argument("--language", default="zh")
    asr.add_argument("--no-itn", dest="enable_itn", action="store_false")
    asr.add_argument("--sample-rate", type=int, default=16000)
    asr.add_argument("--bits", type=int, default=16)
    asr.add_argument("--channels", type=int, default=1)

    # ---- chat ----
    chat = sub.add_parser("chat", help="Text chat completion")
    chat.add_argument("message", help="User message (single turn)")
    chat.add_argument("-o", "--output", help="Output text file (default: stdout)")
    chat.add_argument("--model", default=DEFAULT_CHAT_MODEL)
    chat.add_argument("--system", help="Optional system prompt")
    chat.add_argument("--temperature", type=float)
    chat.add_argument("--max-tokens", type=int)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd in ("tts", "asr"):
            cfg = StepFunAudioConfig(
                api_key=_resolve_key(args.db),
                base_url=args.base_url,
            )
        else:  # chat
            cfg = StepFunChatConfig(
                api_key=_resolve_key(args.db),
                base_url=args.base_url,
            )
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        if args.cmd == "tts":
            client = StepFunAudioClient(cfg)
            blob = client.text_to_speech(
                args.text,
                model=args.model,
                voice=args.voice,
                instruction=args.instruction,
                response_format=args.response_format,
                sample_rate=args.sample_rate,
                speed_ratio=args.speed,
                volume_ratio=args.volume,
            )
            out = _resolve_output(args.output, "tts", args.text, args.response_format)
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            Path(out).write_bytes(blob)
            print(out)
            return 0

        if args.cmd == "asr":
            client = StepFunAudioClient(cfg)
            text = client.transcribe(
                args.audio,
                model=args.model,
                language=args.language,
                enable_itn=args.enable_itn,
                sample_rate=args.sample_rate,
                bits=args.bits,
                channels=args.channels,
            )
            if args.output:
                Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                Path(args.output).write_text(text, encoding="utf-8")
                print(args.output)
            else:
                print(text)
            return 0

        if args.cmd == "chat":
            client = StepFunChatClient(cfg)
            messages: list[dict] = []
            if args.system:
                messages.append({"role": "system", "content": args.system})
            messages.append({"role": "user", "content": args.message})
            text = client.chat(
                messages,
                model=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
            if args.output:
                Path(args.output).parent.mkdir(parents=True, exist_ok=True)
                Path(args.output).write_text(text, encoding="utf-8")
                print(args.output)
            else:
                print(text)
            return 0

    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 2  # unreachable


def _resolve_key(db: str | None) -> str:
    from stepfun_image.ccswitch import resolve_api_key
    return resolve_api_key(db)


def _resolve_output(
    explicit: str | None, kind: str, prompt: str, ext: str
) -> str:
    if explicit:
        return explicit
    import time
    safe = "".join(c if c.isalnum() or c in "-_ " else "" for c in prompt)[:40].strip() or kind
    return str(Path("output") / f"{kind}-{int(time.time())}-{safe}.{ext}")


if __name__ == "__main__":
    sys.exit(main())
