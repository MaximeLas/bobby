#!/usr/bin/env python3
"""
Bobby Voice Test (Manual)

Plays Bobby's acknowledgment phrase through the speaker.
Requires: ELEVENLABS_API_KEY in .env (falls back to macOS 'say' command)

Usage: uv run python3 tests/manual/test_tts.py

WHAT TO VERIFY:
  - You hear Bobby speak "On it, building now" with an Eastern European accent
  - If ElevenLabs fails (no API key / free tier), you hear macOS 'say' fallback
  - No crashes or unhandled exceptions
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from bobby.tts import speak


def main():
    print("=" * 60)
    print("  Bobby Voice Test")
    print("=" * 60)
    print()
    print("  Playing: 'On it, building now'")
    print()

    result = speak("On it, building now")

    print()
    print("=" * 60)
    if result:
        print("  ElevenLabs TTS played successfully.")
    else:
        print("  ElevenLabs failed, fallback was used (or both failed).")
    print()
    print("  VERIFY: Did you hear Bobby speak?")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
