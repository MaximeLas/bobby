#!/usr/bin/env python3
"""
Simple Bobby Voice Test (No Tmux, No Agent)

Usage: uv run python3 tests/test_tts.py
Bobby will respond with his Eastern European voice, then stop.

No agent execution = No credits used!
"""

import sys
from pathlib import Path

# Add project root to path so bobby package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bobby.tts import speak


def main():
    print("=" * 60)
    print("🎤 Bobby Voice Test - Simple Mode")
    print("=" * 60)
    print()
    print("Testing Bobby's Eastern European voice...")
    print()
    print("Bobby will say his acknowledgment phrase:")
    print()

    # Test the voice
    speak("On it, building now")

    print()
    print("=" * 60)
    print("✅ Voice test complete!")
    print("=" * 60)
    print()
    print("If you heard Bobby speak, the voice is working!")
    print("Next step: Run the full system with ./start_bobby.sh")
    print()


if __name__ == "__main__":
    main()
