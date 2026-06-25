---
name: stepfun-audio
version: 0.1.0
description: "调用 StepFun 语音模型（Step Plan）：TTS 语音合成、ASR 语音识别、Chat 文本对话。Key 自动从 CCSwitch 复用。适用于用户需要把文字转成语音、把语音转成文字、调用 stepaudio-2.5 系列模型做对话等场景。"
metadata:
  requires:
    bins: ["python"]
    env_optional: ["STEP_API_KEY", "STEPFUN_HOME"]
    python_packages: ["requests"]
  source: "pip install -e <project>"  # or set $STEPFUN_HOME
---

# StepFun 语音模型 Skill

调用 `python -m stepfun_audio.cli ...`，使用 StepAudio 2.5 家族：

| 能力 | 模型 | 端点 |
| --- | --- | --- |
| TTS（HTTP 非流） | `stepaudio-2.5-tts` | `POST /step_plan/v1/audio/speech` |
| ASR（SSE 流式） | `stepaudio-2.5-asr` | `POST /step_plan/v1/audio/asr/sse` |
| Chat（文本） | `stepaudio-2.5-chat` | `POST /step_plan/v1/chat/completions` |

> **本次未实现**（需要 WebSocket 库 + 双向流控，等下一轮）：
> - `stepaudio-2.5-realtime`（WebSocket 双向实时语音）
> - WebSocket 流式 TTS `/realtime/audio`
> - 音色试听/复刻 `/audio/voices{,/preview}`

Key 复用：同 [[stepfun-image]]，自动从 `~/.cc-switch/cc-switch.db` 读，`$STEP_API_KEY` 可覆盖。

## 何时触发

- "用 stepfun 把这段文字转成语音 / 念给我听"
- "把这段录音转成文字 / 转录"
- "用 stepaudio 陪我聊聊 / 角色扮演对话"
- 用户给了一段 wav/pcm/mp3 文件，要求转写

## CLI 用法

```bash
# 1. TTS：文字转 mp3
python -m stepfun_audio.cli tts "今天天气不错，适合出去走走" \
  --voice cixingnansheng --instruction "语气温柔，语速偏慢" \
  -o out/hello.mp3

# 2. ASR：录音转文字
python -m stepfun_audio.cli asr recording.pcm -o transcript.txt
# 录音必须是 pcm_s16le / 16kHz / mono，否则请先 ffmpeg 转：
#   ffmpeg -i in.wav -f s16le -ar 16000 -ac 1 out.pcm

# 3. Chat：单轮对话
python -m stepfun_audio.cli chat "陪我聊聊" \
  --system "你是有耐心的陪伴搭子，回答自然、温暖、有人情味" \
  -o reply.txt
```

## TTS 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--voice` | `cixingnansheng` | 音色 id（完整列表见开放平台） |
| `--instruction` | — | 风格指令，如 "语气温柔，语速偏慢" |
| `--format` | `mp3` | `mp3` / `wav` / `pcm` / `opus` |
| `--sample-rate` | `24000` | 8k/16k/22050/24k/44100/48k |
| `--speed` | `1.0` | 语速倍率 |
| `--volume` | `1.0` | 音量倍率 |

## ASR 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--language` | `zh` | `zh` / `en` 等 |
| `--no-itn` | 关 | 关闭 ITN（数字归一化等），默认开启 |
| `--sample-rate` | `16000` | 采样率（需与音频实际一致） |
| `--bits` | `16` | 位深 |
| `--channels` | `1` | 声道数 |

## Python SDK

```python
from stepfun_audio import StepFunAudioClient, StepFunChatClient

# TTS
audio = StepFunAudioClient()
mp3 = audio.text_to_speech(
    "今天天气不错",
    voice="cixingnansheng",
    instruction="语气温柔",
    response_format="mp3",
)
open("out.mp3", "wb").write(mp3)

# ASR
text = audio.transcribe("rec.pcm", language="zh")
print(text)

# Chat
chat = StepFunChatClient()
reply = chat.chat([
    {"role": "system", "content": "你是有耐心的陪伴搭子"},
    {"role": "user", "content": "陪我聊聊"},
])
print(reply)
```

## 失败排查

| 现象 | 处理 |
| --- | --- |
| `No StepFun API key found` | 跑 `python -m stepfun_image.cli whoami` 验证 key 来源 |
| ASR 返回空 | 检查音频是不是真的 pcm_s16le / 16kHz / mono，否则用 ffmpeg 预转 |
| TTS 输出很小（< 1KB） | 可能 `--instruction` 太长或 voice id 不存在，简化提示重试 |
| Chat 报 `modalities` 错误 | 不要给 `stepaudio-2.5-chat` 加 `audio` 模态，它只支持 `text` |

## 跨项目复用

skill 与 [[stepfun-image]] 共享同一个 `stepfun_image.ccswitch` Key 加载器。
同一次 CCSwitch 订阅可同时给图像和语音用。
