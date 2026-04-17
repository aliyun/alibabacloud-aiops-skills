#!/usr/bin/env python3
"""
Qwen TTS — 文本生成语音（千问实时语音合成）

SECURITY NOTES:
- base64.b64decode: used ONLY to decode audio PCM chunks received from
  Alibaba DashScope WebSocket API (response.audio.delta). No external
  input is evaluated or executed.
- DASHSCOPE_API_KEY / environment variables: read-only, never logged or
  transmitted to any third party. Used solely to authenticate with
  dashscope.aliyuncs.com (Alibaba Cloud official endpoint).
- No subprocess calls, no file system writes beyond the output WAV file.

支持根据场景自动选择模型和角色，默认使用 qwen3-tts-vd-realtime-2026-01-15。
输出格式：WAV（内部采集 PCM 后自动转换）。

用法:
  python qwen_tts.py --text "你好，欢迎来到未来。" --download
  python qwen_tts.py --text "今日股市大涨..." --scene news --download
  python qwen_tts.py --text "同学们，今天..." --scene education --voice Ethan --download
  python qwen_tts.py --text "亲爱的顾客..." --scene customer_service --download
  python qwen_tts.py --text "..." --model qwen3-tts-instruct-flash-realtime \
      --instructions "语速较快，带有明显的上扬语调，适合介绍时尚产品" --download

依赖:
  pip install dashscope scipy numpy
"""

import argparse
import base64
import io
import os
import struct
import sys
import threading
import time
from pathlib import Path

import dashscope

from input_validation import read_text_file_limited, resolve_under_cwd
from dashscope.audio.qwen_tts_realtime import (
    QwenTtsRealtime,
    QwenTtsRealtimeCallback,
    AudioFormat,
)

# ── User-Agent 配置 ──────────────────────────────────────────────────────────────
USER_AGENT = "AlibabaCloud-Agent-Skills/alibabacloud-avatar-video"

# ── WSS endpoints ──────────────────────────────────────────────────────────────
WSS_URL_CN = "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
WSS_URL_INTL = "wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime"

# ── Model selection guide ──────────────────────────────────────────────────────
# Default = qwen3-tts-vd-realtime-2026-01-15 (Voice Design, text-described tones)
DEFAULT_MODEL = "qwen3-tts-vd-realtime-2026-01-15"

MODEL_GUIDE = {
    "vd":       "qwen3-tts-vd-realtime-2026-01-15",       # 声音设计（文本描述定制音色）
    "vc":       "qwen3-tts-vc-realtime-2026-01-15",       # 声音复刻（音频样本复刻）
    "instruct": "qwen3-tts-instruct-flash-realtime",      # 指令控制（情感/角色/播音风格）
    "flash":    "qwen3-tts-flash-realtime",               # 快速多语种（客服/对话机器人）
    "legacy":   "qwen-tts-realtime",                      # 旧版稳定
}

# 场景 → 推荐模型 映射
SCENE_TO_MODEL = {
    "news":             "qwen3-tts-instruct-flash-realtime",   # 新闻播报
    "documentary":      "qwen3-tts-instruct-flash-realtime",   # 纪录片
    "advertising":      "qwen3-tts-instruct-flash-realtime",   # 广告宣传
    "audiobook":        "qwen3-tts-instruct-flash-realtime",   # 有声书
    "drama":            "qwen3-tts-instruct-flash-realtime",   # 广播剧/游戏配音
    "customer_service": "qwen3-tts-flash-realtime",            # 智能客服
    "chatbot":          "qwen3-tts-flash-realtime",            # 对话机器人
    "education":        "qwen3-tts-flash-realtime",            # 教育/讲解
    "ecommerce":        "qwen3-tts-flash-realtime",            # 电商/直播带货
    "short_video":      "qwen3-tts-flash-realtime",            # 短视频配音
    "brand":            DEFAULT_MODEL,                          # 品牌定制声音
    "default":          DEFAULT_MODEL,
}

# 场景 → 推荐 voice（系统音色）
SCENE_TO_VOICE = {
    "news":             "Serena",    # 成熟女声，播报感强
    "documentary":      "Ethan",     # 稳重男声
    "advertising":      "Cherry",    # 活泼女声
    "audiobook":        "Cherry",    # 温柔女声
    "drama":            "Dylan",     # 富有表现力
    "customer_service": "Anna",      # 亲切女声
    "chatbot":          "Anna",
    "education":        "Ethan",     # 清晰男声
    "ecommerce":        "Cherry",    # 热情女声
    "short_video":      "Cherry",
    "brand":            "Cherry",
    "default":          "Cherry",
}

# 所有可用系统音色（附描述）
VOICES = {
    "Cherry":  "活泼甜美女声，中文优先，适合广告/有声书/配音",
    "Serena":  "成熟知性女声，适合新闻/讲解/企业形象",
    "Ethan":   "稳重亲切男声，适合教育/纪录片/培训",
    "Dylan":   "富有表现力男声，适合广播剧/游戏配音",
    "Anna":    "温柔亲切女声，适合客服/助手/日常",
    "Chelsie": "年轻清新女声，适合短视频/电商",
    "Thomas":  "低沉磁性男声，适合品牌宣传/广告",
    "Luna":    "温暖柔和女声，适合冥想/故事叙述",
}


# ── PCM → WAV conversion ────────────────────────────────────────────────────────

def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 24000,
               channels: int = 1, sample_width: int = 2) -> bytes:
    """Convert raw PCM bytes to WAV format."""
    buf = io.BytesIO()
    data_len = len(pcm_bytes)
    byte_rate = sample_rate * channels * sample_width
    block_align = channels * sample_width

    buf.write(b"RIFF")
    buf.write(struct.pack("<I", 36 + data_len))
    buf.write(b"WAVE")
    buf.write(b"fmt ")
    buf.write(struct.pack("<I", 16))          # chunk size
    buf.write(struct.pack("<H", 1))           # PCM format
    buf.write(struct.pack("<H", channels))
    buf.write(struct.pack("<I", sample_rate))
    buf.write(struct.pack("<I", byte_rate))
    buf.write(struct.pack("<H", block_align))
    buf.write(struct.pack("<H", sample_width * 8))
    buf.write(b"data")
    buf.write(struct.pack("<I", data_len))
    buf.write(pcm_bytes)
    return buf.getvalue()


# ── TTS client ─────────────────────────────────────────────────────────────────

class _TtsCollector(QwenTtsRealtimeCallback):
    def __init__(self):
        self.pcm_chunks: list[bytes] = []
        self.done_event = threading.Event()
        self.error: Exception | None = None

    def on_open(self) -> None:
        pass

    def on_close(self, code, msg) -> None:
        self.done_event.set()

    def on_event(self, response: dict) -> None:
        try:
            evt = response.get("type", "")
            if evt == "response.audio.delta":
                chunk = base64.b64decode(response["delta"])
                self.pcm_chunks.append(chunk)
            elif evt == "session.finished":
                self.done_event.set()
            elif evt == "error":
                self.error = RuntimeError(str(response))
                self.done_event.set()
        except Exception as e:
            self.error = e
            self.done_event.set()

    def collect(self) -> bytes:
        return b"".join(self.pcm_chunks)


def synthesize(
    text: str,
    model: str = DEFAULT_MODEL,
    voice: str = "Cherry",
    instructions: str = "",
    optimize_instructions: bool = True,
    sample_rate: int = 24000,
    speed: float = 1.0,
    timeout: int = 120,
    url: str = WSS_URL_CN,
) -> bytes:
    """
    Synthesize text to speech using Qwen TTS Realtime.

    Returns:
        WAV bytes
    """
    dashscope.api_key = os.environ.get("DASHSCOPE_API_KEY", dashscope.api_key)
    if not dashscope.api_key:
        raise RuntimeError("DASHSCOPE_API_KEY not set")

    # Only PCM_24000HZ_MONO_16BIT is universally available; use it regardless of sample_rate param
    audio_fmt = AudioFormat.PCM_24000HZ_MONO_16BIT
    sample_rate = 24000  # force to match

    # 设置 User-Agent
    headers = {"User-Agent": USER_AGENT}

    collector = _TtsCollector()
    client = QwenTtsRealtime(
        model=model,
        callback=collector,
        url=url,
        headers=headers,  # 传递自定义 headers
    )
    client.connect()

    session_kwargs = dict(
        voice=voice,
        response_format=audio_fmt,
        mode="server_commit",
    )
    if speed != 1.0:
        session_kwargs["speed"] = speed
    if instructions:
        session_kwargs["instructions"] = instructions
        session_kwargs["optimize_instructions"] = optimize_instructions

    client.update_session(**session_kwargs)

    # Send text in chunks (improves latency for long text)
    max_chunk = 100
    for i in range(0, len(text), max_chunk):
        client.append_text(text[i:i + max_chunk])
        time.sleep(0.05)

    client.finish()
    collector.done_event.wait(timeout=timeout)

    if collector.error:
        raise collector.error

    pcm = collector.collect()
    if not pcm:
        raise RuntimeError("No audio received from TTS service")

    return pcm_to_wav(pcm, sample_rate=sample_rate)


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        description="Qwen TTS — 文本生成语音（根据场景自动选择模型和音色）"
    )
    p.add_argument("--text", help="要合成的文本（也可用 --text-file）")
    p.add_argument("--text-file", help="从文件读取文本")
    p.add_argument("--scene", default="default",
                   choices=list(SCENE_TO_MODEL.keys()),
                   help="""场景选择（自动推荐模型和音色）:
  news          新闻播报
  documentary   纪录片旁白
  advertising   广告宣传
  audiobook     有声书
  drama         广播剧/游戏配音
  customer_service 智能客服
  chatbot       对话机器人
  education     教育讲解
  ecommerce     电商/直播
  short_video   短视频配音
  brand         品牌定制
  default       默认（qwen3-tts-vd-realtime）""")

    p.add_argument("--model", default=None,
                   help=f"指定模型（覆盖 --scene 的推荐）。默认: {DEFAULT_MODEL}")
    p.add_argument("--voice", default=None,
                   help=f"指定音色（覆盖 --scene 的推荐）。可选: {', '.join(VOICES)}")
    p.add_argument("--instructions", default="",
                   help="自然语言指令控制语音表现（需配合 qwen3-tts-instruct-flash-realtime 模型）")
    p.add_argument("--speed", type=float, default=1.0,
                   help="语速倍率，0.5~2.0 (default: 1.0)")
    p.add_argument("--sample-rate", type=int, default=24000,
                   choices=[16000, 24000, 48000],
                   help="采样率 (default: 24000)")
    p.add_argument("--intl", action="store_true",
                   help="使用新加坡国际节点（需要国际区 API Key）")
    p.add_argument("--list-voices", action="store_true", help="列出所有音色及描述")
    p.add_argument("--list-models", action="store_true", help="列出模型选型指南")
    p.add_argument("--download", action="store_true", help="保存音频到本地文件")
    p.add_argument("--output", default="tts_output.wav", help="输出文件名 (default: tts_output.wav)")
    args = p.parse_args()

    if args.list_voices:
        print("\n── 可用音色 ──")
        for name, desc in VOICES.items():
            print(f"  {name:<10} {desc}")
        return

    if args.list_models:
        print("\n── 模型选型指南 ──")
        for scene, model in SCENE_TO_MODEL.items():
            voice = SCENE_TO_VOICE.get(scene, "Cherry")
            print(f"  {scene:<20} model={model}  voice={voice}")
        return

    # get text
    text = args.text
    if not text and args.text_file:
        text = read_text_file_limited(args.text_file, field="--text-file")
    if not text:
        p.error("需要 --text 或 --text-file")

    # resolve model and voice
    model = args.model or SCENE_TO_MODEL.get(args.scene, DEFAULT_MODEL)
    voice = args.voice or SCENE_TO_VOICE.get(args.scene, "Cherry")
    url = WSS_URL_INTL if args.intl else WSS_URL_CN

    print(f"[tts] model={model}  voice={voice}  scene={args.scene}")
    print(f"[tts] text({len(text)}ch): {text[:60]}{'...' if len(text)>60 else ''}")
    if args.instructions:
        print(f"[tts] instructions: {args.instructions}")

    t0 = time.time()
    wav_bytes = synthesize(
        text=text,
        model=model,
        voice=voice,
        instructions=args.instructions,
        sample_rate=args.sample_rate,
        speed=args.speed,
        url=url,
    )
    elapsed = time.time() - t0
    size_kb = len(wav_bytes) // 1024
    print(f"\n✅ Done  {size_kb}KB  {elapsed:.1f}s")

    if args.download:
        out = resolve_under_cwd(args.output, field="--output")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(wav_bytes)
        print(f"Saved → {out}  ({size_kb}KB)")
    else:
        # Write to stdout (for piping)
        sys.stdout.buffer.write(wav_bytes)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[interrupted]")
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
