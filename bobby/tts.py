#!/usr/bin/env python3
"""
Text-to-Speech for Bobby using ElevenLabs

Bobby speaks with an Eastern European accent using ElevenLabs TTS API.
"""

import os
import subprocess
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

# Load environment variables
load_dotenv()

# Initialize ElevenLabs client
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Bobby's voice configuration
BOBBY_VOICE_ID = "lIaJUjvN2nyLPU9wRIa0"  # Eastern European voice
# Flash v2.5: ~75ms latency (vs ~250ms for Turbo), ~half the credit cost, same
# voice character — matters when Bobby talks during a live call. The custom
# voice carries the Borat character; the model mostly affects latency/cost.
BOBBY_MODEL = "eleven_flash_v2_5"
BOBBY_OUTPUT_FORMAT = "mp3_44100_128"  # Standard MP3 format


def generate_audio(text):
    """
    Generate speech audio bytes using ElevenLabs.

    Args:
        text: What Bobby should say

    Returns:
        bytes: MP3 audio data

    Raises:
        Exception: If ElevenLabs API call fails
    """
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=BOBBY_VOICE_ID,
        model_id=BOBBY_MODEL,
        output_format=BOBBY_OUTPUT_FORMAT,
    )

    # Collect all audio chunks into bytes
    audio_bytes = b""
    for chunk in audio:
        audio_bytes += chunk

    return audio_bytes


def play_local(audio_bytes):
    """
    Play audio bytes locally via macOS afplay.

    Args:
        audio_bytes: MP3 audio data to play
    """
    temp_file = "/tmp/bobby_speech.mp3"
    with open(temp_file, "wb") as f:
        f.write(audio_bytes)

    subprocess.run(["afplay", temp_file], check=True)


def speak(text):
    """
    Make Bobby speak using ElevenLabs text-to-speech (local playback).

    Convenience wrapper that generates audio and plays it locally.
    Used by the local-mode orchestrator.

    Args:
        text: What Bobby should say

    Returns:
        bool: True if speech was successful, False otherwise
    """
    print(f"🎙️  Bobby: {text}")

    try:
        audio_bytes = generate_audio(text)
        play_local(audio_bytes)
        return True

    except Exception as e:
        print(f"❌ TTS Error: {e}")
        print(f"💬 Fallback text: {text}")
        # Fallback to macOS say command
        try:
            subprocess.run(["say", text], check=True, timeout=10)
        except Exception as fallback_error:
            print(f"❌ Fallback also failed: {fallback_error}")
        return False
