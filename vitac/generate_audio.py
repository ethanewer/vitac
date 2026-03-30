"""Generate TTS audio for task instructions using OpenAI.

Reads audio/instructions.json, generates a WAV file per task via the
OpenAI TTS API, and writes them to audio/{task_id}.wav.  Files that
already exist are skipped unless --force is passed.

Usage:
    python -m vitac.generate_audio [--force]
"""

from __future__ import annotations

import json
import os
import struct
import sys
from pathlib import Path

AUDIO_DIR = Path(__file__).parent.parent / "audio"
INSTRUCTIONS_PATH = AUDIO_DIR / "instructions.json"

TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = "nova"
TTS_SPEED = 1.0


def generate_wav(text: str, output_path: Path) -> None:
    """Call OpenAI TTS and write a WAV file."""
    import httpx

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    url = f"{base_url}/audio/speech"

    # Request raw PCM so we can wrap it in a proper WAV header.
    resp = httpx.post(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": TTS_MODEL,
            "input": text,
            "voice": TTS_VOICE,
            "response_format": "pcm",
            "speed": TTS_SPEED,
        },
        timeout=120,
    )
    resp.raise_for_status()
    pcm = resp.content

    # Wrap PCM (24 kHz, 16-bit, mono) in a WAV header.
    sample_rate = 24000
    channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * channels * (bits_per_sample // 8)
    block_align = channels * (bits_per_sample // 8)
    data_size = len(pcm)

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM format
        channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(header)
        f.write(pcm)


def main() -> None:
    force = "--force" in sys.argv

    if not INSTRUCTIONS_PATH.exists():
        print(f"Instructions file not found: {INSTRUCTIONS_PATH}")
        sys.exit(1)

    with open(INSTRUCTIONS_PATH) as f:
        instructions: dict = json.load(f)

    generated = 0
    skipped = 0
    for task_id, info in sorted(instructions.items()):
        wav_path = AUDIO_DIR / f"{task_id}.wav"
        if wav_path.exists() and not force:
            print(f"  skip  {task_id} (already exists)")
            skipped += 1
            continue

        text = info["text"]
        print(f"  gen   {task_id} ({len(text)} chars) ... ", end="", flush=True)
        try:
            generate_wav(text, wav_path)
            size_kb = wav_path.stat().st_size / 1024
            print(f"ok ({size_kb:.0f} KB)")
            generated += 1
        except Exception as e:
            print(f"FAILED: {e}")

    print(f"\nDone: {generated} generated, {skipped} skipped")


if __name__ == "__main__":
    main()
