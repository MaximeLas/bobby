#!/usr/bin/env python3
"""
Bobby Voice Test with Transcript Watching (No Agent Execution)

This script:
- Starts audio capture (microphone -> Assembly AI -> transcript)
- Watches transcript for "Hey Bobby, please build this"
- Responds with Bobby's Eastern European voice
- Does NOT launch Claude Code agent (saves credits!)

Usage: uv run python3 tests/test_integration.py
Then say: "Hey Bobby, please build this"
"""

import subprocess
import threading
import time
import os
import sys
import signal
from datetime import datetime
from pathlib import Path

# Add project root to path so bobby package can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bobby.config import TRANSCRIPT_FILE, PAUSE_FLAG_FILE, WORKSPACE_DIR

# Global variables for cleanup
running = True
audio_capture_process = None

# Settings
DEBOUNCE_SECONDS = 30
POLL_INTERVAL = 1


class VoiceTest:
    """Watch transcript and respond with voice only."""

    def __init__(self):
        self.last_trigger_time = 0

        # Ensure workspace directory exists
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

        # Start from end of existing transcript
        if TRANSCRIPT_FILE.exists():
            with open(TRANSCRIPT_FILE, 'r') as f:
                f.seek(0, 2)
                self.last_position = f.tell()
            print(f"Starting from end of transcript (position: {self.last_position})")
        else:
            self.last_position = 0
            print("Transcript file doesn't exist yet, will watch from beginning")

        print()
        print("=" * 60)
        print("Bobby Voice Test - Transcript Mode")
        print("=" * 60)
        print()
        print("Will watch transcript for triggers")
        print("Will respond with Bobby's voice")
        print("Will NOT launch agent (saving credits)")
        print()
        print(f"Watching: {TRANSCRIPT_FILE}")
        print(f"Trigger: 'Hey Bobby, please build this'")
        print()
        print("=" * 60)
        print()

    def speak_bobby(self, text):
        """Make Bobby speak using ElevenLabs TTS."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print()
        print("=" * 60)
        print(f"[{timestamp}] Bobby says: {text}")
        print("=" * 60)
        print()

        # Create pause flag to stop transcription during speech
        try:
            with open(PAUSE_FLAG_FILE, 'w') as f:
                f.write(f"Paused at {timestamp}\n")
            print("Transcription paused")
        except Exception as e:
            print(f"Warning: Could not create pause flag: {e}")

        # Speak using ElevenLabs
        try:
            from bobby.tts import speak
            speak(text)
            print("Voice played successfully")
        except Exception as e:
            print(f"ElevenLabs TTS failed: {e}")
            # Fallback to macOS say
            try:
                print("Falling back to macOS 'say' command...")
                subprocess.run(
                    ['say', '-v', 'Alex', text],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=10
                )
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")

        # Remove pause flag to resume transcription
        try:
            if PAUSE_FLAG_FILE.exists():
                PAUSE_FLAG_FILE.unlink()
                print("Transcription resumed")
        except Exception as e:
            print(f"Warning: Could not remove pause flag: {e}")

        print()

    def should_process_trigger(self):
        """Check if enough time passed since last trigger (debouncing)."""
        current_time = time.time()
        time_since_last = current_time - self.last_trigger_time

        if time_since_last < DEBOUNCE_SECONDS:
            print(f"[DEBOUNCE] Ignoring trigger (only {time_since_last:.1f}s since last)")
            return False

        self.last_trigger_time = current_time
        return True

    def handle_trigger(self, new_text):
        """Handle the build trigger - speak but don't launch agent."""
        print()
        print("TRIGGER DETECTED: Hey Bobby, please build this")
        print()

        # Show context
        print("Recent transcript context:")
        print("-" * 60)
        lines = new_text.strip().split('\n')
        for line in lines[-5:]:  # Show last 5 lines
            print(f"   {line}")
        print("-" * 60)
        print()

        # Speak acknowledgment
        self.speak_bobby("On it, building now")

        # In test mode, we stop here
        print()
        print("=" * 60)
        print("VOICE TEST COMPLETE!")
        print("=" * 60)
        print()
        print("In production mode, Bobby would now:")
        print("   1. Launch Claude Code agent")
        print("   2. Build the requested feature")
        print("   3. Announce completion")
        print()
        print("But we're in test mode, so we stop here (no credits used)")
        print()
        print("=" * 60)
        print()

    def check_for_triggers(self):
        """Read new transcript content and check for triggers."""
        try:
            with open(TRANSCRIPT_FILE, 'r') as f:
                f.seek(self.last_position)
                new_text = f.read()
                self.last_position = f.tell()

                if not new_text.strip():
                    return

                # Show new transcript content
                if new_text.strip():
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] New transcript:")
                    for line in new_text.strip().split('\n'):
                        print(f"   {line}")
                    print()

                # Check for build trigger
                lower_text = new_text.lower()
                if 'hey bobby' in lower_text and 'please build this' in lower_text:
                    if self.should_process_trigger():
                        self.handle_trigger(new_text)

        except FileNotFoundError:
            pass  # File doesn't exist yet
        except Exception as e:
            print(f"Error reading transcript: {e}")

    def run(self):
        """Main loop - watch transcript for triggers."""
        print("Listening for NEW transcript content...")
        print()
        print("IMPORTANT: This script only watches for NEW text added AFTER it started!")
        print("   Old text in the transcript file is ignored.")
        print()
        print("To test: Say into your microphone NOW:")
        print("   'Hey Bobby, please build this'")
        print()
        print("To stop: Press Ctrl+C")
        print()

        try:
            while True:
                self.check_for_triggers()
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            print()
            print()
            print("=" * 60)
            print("Voice test stopped")
            print("=" * 60)
            print()


def start_audio_capture():
    """Start audio capture in subprocess."""
    global audio_capture_process

    print("Starting audio capture...")
    print("-" * 60)

    try:
        audio_capture_process = subprocess.Popen(
            ['uv', 'run', 'python3', '-m', 'bobby.audio_capture'],
            stdout=sys.stdout,
            stderr=sys.stderr
        )

        print("Audio capture started (microphone should turn on now)")
        print("-" * 60)
        print()

        # Wait for process to finish (or be killed)
        audio_capture_process.wait()

    except Exception as e:
        print(f"Audio capture failed: {e}")
        print()
        print("Exiting because audio capture is required...")
        sys.exit(1)


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    global running, audio_capture_process

    print()
    print()
    print("=" * 60)
    print("Stopping Bobby voice test...")
    print("=" * 60)

    running = False

    # Kill audio capture subprocess
    if audio_capture_process:
        try:
            audio_capture_process.terminate()
            audio_capture_process.wait(timeout=2)
            print("Audio capture stopped")
        except:
            audio_capture_process.kill()
            print("Audio capture killed")

    print()
    print("Goodbye!")
    print()

    sys.exit(0)


def main():
    """Main function - starts audio capture AND transcript watcher."""
    global running

    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    print()
    print("=" * 60)
    print("Bobby Voice Test - Full Mode")
    print("=" * 60)
    print()
    print("This will run:")
    print("  Audio capture (microphone -> Assembly AI -> transcript)")
    print("  Orchestrator (watches transcript -> Bobby speaks)")
    print()
    print("This will NOT run:")
    print("  Claude Code agents (no credits used)")
    print()
    print("=" * 60)
    print()

    # Check if workspace exists
    if not WORKSPACE_DIR.exists():
        print()
        print(f"Error: workspace directory not found: {WORKSPACE_DIR}")
        print()
        print("Make sure you're running this from the project root:")
        print("   cd ~/Projects/bobby")
        print("   uv run python3 tests/test_integration.py")
        print()
        sys.exit(1)

    # Start audio capture in a separate thread
    audio_thread = threading.Thread(target=start_audio_capture, daemon=True)
    audio_thread.start()

    # Give audio capture time to initialize
    print("Waiting for audio capture to initialize...")
    time.sleep(3)
    print()

    # Start transcript watcher in main thread
    try:
        test = VoiceTest()
        test.run()
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)


if __name__ == '__main__':
    main()
