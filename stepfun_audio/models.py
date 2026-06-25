"""Default model and voice constants for the StepFun audio endpoints."""

from __future__ import annotations

# Step Plan StepAudio 2.5 family.
DEFAULT_TTS_MODEL = "stepaudio-2.5-tts"
DEFAULT_ASR_MODEL = "stepaudio-2.5-asr"
DEFAULT_CHAT_MODEL = "stepaudio-2.5-chat"

# A common preset voice id used in the StepFun TTS examples.
DEFAULT_TTS_VOICE = "cixingnansheng"

# Supported audio formats / codecs for TTS responses.
TTS_RESPONSE_FORMATS = ("mp3", "wav", "pcm", "opus")
TTS_SAMPLE_RATES = (8000, 16000, 22050, 24000, 44100, 48000)
