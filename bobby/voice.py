#!/usr/bin/env python3
"""
Bobby Voice — shared local-mode speech helper.

In local mode the orchestrator and the progress watcher both speak through
the machine's speakers while the microphone is live, so every utterance
must coordinate with audio capture or Bobby transcribes (and can even
re-trigger on) his own voice. speak_in_meeting() is the single path:

1. create PAUSE_FLAG_FILE so audio_capture stops streaming to Assembly AI
2. speak via ElevenLabs (bobby.tts), with macOS `say` as the fallback
3. remove the pause flag to resume transcription
4. record the spoken text in BOBBY_SPEECH_FILE so audio_capture can filter
   any buffered audio of Bobby's voice that Assembly AI flushes post-pause

Discord mode does NOT use this helper: the bot plays audio into the call
(discord_bot._speak_in_voice) and per-user audio routing means Bobby never
hears himself there.
"""

import subprocess
from datetime import datetime

from bobby.config import PAUSE_FLAG_FILE, BOBBY_SPEECH_FILE


def speak_in_meeting(text):
    """
    Speak into the room with transcription paused. Blocking for the length
    of the audio — callers that must keep polling should run this in a
    thread.

    Returns True if some audio was produced (ElevenLabs or fallback).
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n{'=' * 60}")
    print(f"[{timestamp}] 🗣️  Bobby says: {text}")
    print(f"{'=' * 60}\n")

    # Pause transcription so the mic doesn't capture Bobby's own voice
    try:
        with open(PAUSE_FLAG_FILE, 'w') as f:
            f.write(f"Paused for Bobby speech at {timestamp}\n")
    except Exception as e:
        print(f"Warning: Could not create pause flag: {e}")

    spoke = False
    try:
        # Lazy import: tts pulls in the ElevenLabs client; a missing/broken
        # install should degrade to `say`, not crash the caller
        from bobby.tts import speak
        speak(text)  # tts.speak has its own `say` fallback inside
        spoke = True
    except Exception as e:
        print(f"❌ ERROR: TTS unavailable: {e}")
        try:
            subprocess.run(
                ['say', '-v', 'Alex', text],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            spoke = True
        except Exception as fallback_error:
            print(f"Warning: Fallback TTS also failed: {fallback_error}")

    # Resume transcription
    try:
        if PAUSE_FLAG_FILE.exists():
            PAUSE_FLAG_FILE.unlink()
    except Exception as e:
        print(f"Warning: Could not remove pause flag: {e}")

    # Record what Bobby said so audio_capture can filter it out
    # (Assembly AI buffers audio during the pause and sends it after)
    try:
        with open(str(BOBBY_SPEECH_FILE), 'w') as f:
            f.write(text.lower())
    except Exception as e:
        print(f"Warning: Could not write Bobby's speech: {e}")

    return spoke
