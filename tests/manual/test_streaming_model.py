#!/usr/bin/env python3
"""
Manual diagnostic: stream real speech through AssemblyAI's streaming v3 API
and print exactly what TurnEvents come back.

WHY THIS EXISTS: Universal-3.5 Pro Realtime (speech_model="universal-3-5-pro")
changed how turns are emitted. Older streaming models sent each finalized turn
twice (unformatted, then formatted), so Bobby gated on `turn_is_formatted` to
avoid duplicates. If the new model never sets `turn_is_formatted=True`, that
gate would silently drop EVERY turn. This script settles the question with real
audio instead of guessing — no microphone needed (uses macOS `say`).

Requires: ASSEMBLYAI_API_KEY in .env, macOS (`say` + `afconvert`), network.

Run:  uv run python3 tests/manual/test_streaming_model.py
      uv run python3 tests/manual/test_streaming_model.py "your own phrase here"
"""

import os
import sys
import time
import wave
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from dotenv import load_dotenv
from bobby.config import (
    STREAMING_SPEECH_MODEL,
    STREAMING_PROMPT,
    STREAMING_KEYTERMS,
)
from assemblyai.streaming.v3 import (
    StreamingClient,
    StreamingClientOptions,
    StreamingEvents,
    StreamingParameters,
    BeginEvent,
    TurnEvent,
    TerminationEvent,
    StreamingError,
)

SAMPLE_RATE = 16000
PHRASE = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "Hey Bobby, please build this. Can you add a dark mode toggle to the app?"
)


def make_speech_wav(text: str) -> str:
    """Generate 16kHz mono PCM WAV speech via macOS say + afconvert."""
    aiff = "/tmp/bobby_streamtest.aiff"
    wav = "/tmp/bobby_streamtest.wav"
    subprocess.run(["say", "-o", aiff, text], check=True)
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", f"LEI16@{SAMPLE_RATE}", "-c", "1", aiff, wav],
        check=True,
    )
    return wav


def audio_chunks(wav_path: str):
    """Yield ~50ms PCM chunks in real time, then ~2s of trailing silence
    so the model detects end-of-turn before the stream closes."""
    with wave.open(wav_path, "rb") as wf:
        assert wf.getframerate() == SAMPLE_RATE, wf.getframerate()
        assert wf.getnchannels() == 1, wf.getnchannels()
        frames_per_chunk = SAMPLE_RATE // 20  # 50ms
        while True:
            frames = wf.readframes(frames_per_chunk)
            if not frames:
                break
            yield frames
            time.sleep(0.05)
    silence = b"\x00\x00" * (SAMPLE_RATE // 20)
    for _ in range(40):  # ~2s of silence
        yield silence
        time.sleep(0.05)


def main():
    load_dotenv()
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        print("❌ ASSEMBLYAI_API_KEY not set in .env — cannot run this diagnostic.")
        sys.exit(1)

    print(f"🗣️  Phrase: {PHRASE!r}")
    print("🎛️  Generating speech via macOS say...")
    wav = make_speech_wav(PHRASE)

    turns = []

    def on_begin(client, event: BeginEvent):
        print(f"✅ Session started: {event.id}")
        cfg = getattr(event, "configuration", None)
        if cfg is not None:
            print(f"   server-reported config: model={cfg.model!r} mode={cfg.mode!r} "
                  f"api_version={cfg.api_version!r}")

    def on_turn(client, event: TurnEvent):
        turns.append(event)
        print(
            f"   TURN order={event.turn_order} "
            f"end_of_turn={event.end_of_turn} "
            f"formatted={event.turn_is_formatted} "
            f"| {event.transcript!r}"
        )

    def on_terminated(client, event: TerminationEvent):
        print(f"🏁 Terminated: {event.audio_duration_seconds}s audio")

    def on_error(client, error: StreamingError):
        print(f"❌ Streaming error: {error}")

    client = StreamingClient(
        StreamingClientOptions(api_key=api_key, api_host="streaming.assemblyai.com")
    )
    client.on(StreamingEvents.Begin, on_begin)
    client.on(StreamingEvents.Turn, on_turn)
    client.on(StreamingEvents.Termination, on_terminated)
    client.on(StreamingEvents.Error, on_error)

    # Use the exact production config so this diagnostic verifies what Bobby
    # actually runs with (hardcoding here drifts silently from config.py).
    print(f"🔌 Connecting with speech_model={STREAMING_SPEECH_MODEL!r}...")
    client.connect(
        StreamingParameters(
            sample_rate=SAMPLE_RATE,
            speech_model=STREAMING_SPEECH_MODEL,
            prompt=STREAMING_PROMPT,
            keyterms_prompt=STREAMING_KEYTERMS,
        )
    )

    try:
        client.stream(audio_chunks(wav))
    finally:
        client.disconnect(terminate=True)

    # Summary: what a gate of `end_of_turn` only would write.
    finalized = [t for t in turns if t.end_of_turn]
    formatted_finalized = [t for t in finalized if t.turn_is_formatted]
    print("\n=== SUMMARY ===")
    print(f"total turn events:       {len(turns)}")
    print(f"finalized (end_of_turn): {len(finalized)}")
    print(f"  ...of which formatted: {len(formatted_finalized)}")
    print("\nVERDICT:")
    if finalized and not formatted_finalized:
        print("  ⚠️  Finalized turns are NEVER formatted on this model.")
        print("  ⚠️  The old `if not turn_is_formatted: return` gate would DROP EVERYTHING.")
        print("  ✅  Gate on end_of_turn only (with turn_order dedupe).")
    elif formatted_finalized and len(formatted_finalized) == len(finalized):
        print("  ✅  Every finalized turn is formatted; no unformatted duplicates seen.")
        print("  ✅  Gate on end_of_turn only is safe; dedupe is belt-and-suspenders.")
    else:
        print("  ℹ️  Mixed: some finalized turns formatted, some not "
              "(possible unformatted->formatted pairs). Dedupe by turn_order needed.")


if __name__ == "__main__":
    main()
