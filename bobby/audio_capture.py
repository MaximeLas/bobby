#!/usr/bin/env python3
"""
Bobby Audio Capture - Component 1
Captures audio from BlackHole virtual audio device (or the default mic) and
streams it to Assembly AI for real-time transcription.

Single-channel capture: one shared transcript, unlabeled by default. Writes to
meeting_transcript.txt in the format:
[HH:MM:SS] transcript text
[HH:MM:SS] [Max] transcript text     (with BOBBY_SPEAKER_LABELS=1)
"""

import os
import sys
import logging
import signal
from datetime import datetime

import pyaudio
from dotenv import load_dotenv
from bobby.config import (
    TRANSCRIPT_FILE,
    PAUSE_FLAG_FILE,
    BOBBY_SPEECH_FILE,
    STREAMING_SPEECH_MODEL,
    STREAMING_PROMPT,
    STREAMING_KEYTERMS,
    SIDECAR_MODE,
    SIDECAR_MAX_SPEAKERS,
    EVENTS_FILE,
    SPEAKER_NAMES,
    SPEAKER_NAMES_FILE,
    SPEAKER_LABELS_ENABLED,
)
from bobby.streaming import should_write_turn
from bobby.sidecar import (
    SidecarWriter,
    format_speaker_label,
    resolve_speaker_names,
    turn_speaker_label,
)
from assemblyai.streaming.v3 import (
    BeginEvent,
    StreamingClient,
    StreamingClientOptions,
    StreamingError,
    StreamingEvents,
    StreamingParameters,
    TurnEvent,
    TerminationEvent,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variable for cleanup
client = None

# Tracks turn_order values already written this session, so each finalized turn
# is written exactly once regardless of how the model emits it (see on_turn).
_written_turn_orders = set()

# Sidecar mode (BOBBY_SIDECAR=1): the v2 pipeline replaces write_transcript —
# every event goes to events.jsonl and the transcript becomes a derived view
# with live partials, speaker labels, and retroactive label revisions.
# Constructed in main() so it picks up the resolved workspace paths.
_sidecar = None


class BlackHoleAudioStream:
    """Custom audio stream for BlackHole device (or default microphone for testing)"""

    def __init__(self, sample_rate=16000, chunk_size=1024, use_default_mic=False):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.use_default_mic = use_default_mic
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.device_index = None

    def find_blackhole_device(self):
        """Find BlackHole audio device index"""
        logger.info("Searching for BlackHole audio device...")

        for i in range(self.p.get_device_count()):
            dev_info = self.p.get_device_info_by_index(i)
            device_name = dev_info.get('name', '').lower()

            # Look for BlackHole in device name
            if 'blackhole' in device_name:
                # Check if device has input channels
                if dev_info.get('maxInputChannels', 0) > 0:
                    logger.info(f"Found BlackHole device: {dev_info.get('name')} (index: {i})")
                    return i

        return None

    def start(self):
        """Start the audio stream"""
        if self.use_default_mic:
            # Use default microphone (for testing without BlackHole)
            self.device_index = None  # None means default input device
            logger.info("Using DEFAULT MICROPHONE for testing (not BlackHole)")
        else:
            # Use BlackHole (for production - capturing Zoom/meeting audio)
            self.device_index = self.find_blackhole_device()

            if self.device_index is None:
                raise RuntimeError(
                    "BlackHole device not found. Please ensure BlackHole is installed.\n"
                    "Install with: brew install blackhole-2ch\n"
                    "See docs/AUDIO_SETUP.md for complete setup instructions."
                )

        try:
            # Open audio stream from BlackHole
            self.stream = self.p.open(
                format=pyaudio.paInt16,
                channels=1,  # Mono
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size
            )
            logger.info(f"Audio stream started (sample rate: {self.sample_rate}Hz, chunk size: {self.chunk_size})")
        except Exception as e:
            raise RuntimeError(f"Failed to open audio stream: {e}")

    def __iter__(self):
        """Make the stream iterable for Assembly AI"""
        return self

    def __next__(self):
        """Read next chunk of audio data"""
        if self.stream is None or not self.stream.is_active():
            raise StopIteration

        try:
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)
            return data
        except Exception as e:
            logger.error(f"Error reading audio stream: {e}")
            raise StopIteration

    def close(self):
        """Close the audio stream"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
        logger.info("Audio stream closed")


def get_timestamp():
    """Get current timestamp in HH:MM:SS format"""
    return datetime.now().strftime("%H:%M:%S")


def write_transcript(text, label=None):
    """
    Write a transcript line to file with timestamp.

    Single-channel, so a line is "[HH:MM:SS] text" — unless speaker labels are
    on (BOBBY_SPEAKER_LABELS=1) and the turn carried one, giving
    "[HH:MM:SS] [Max] text". `label` is the raw diarization label ("A"/"B");
    the display name comes from the same SPEAKER_NAMES / speaker_names.txt
    mapping sidecar mode renders with, re-read per line so names can be
    assigned live mid-meeting.
    """
    # Check if transcription is paused (Bobby is speaking)
    pause_flag = PAUSE_FLAG_FILE
    if pause_flag.exists():
        logger.info(f"SKIPPED (Bobby speaking): {text[:50]}...")
        return

    # Filter out Bobby's own voice (Assembly AI buffers during pause and sends after)
    bobby_speech_file = BOBBY_SPEECH_FILE
    if bobby_speech_file.exists():
        try:
            with open(bobby_speech_file, 'r') as f:
                bobby_said = f.read().strip()
            # Check if transcribed text matches what Bobby just said
            import string
            bobby_normalized = bobby_said.lower().translate(str.maketrans('', '', string.punctuation))
            text_normalized = text.lower().translate(str.maketrans('', '', string.punctuation))

            if bobby_normalized and bobby_normalized in text_normalized:
                logger.info(f"FILTERED (Bobby's voice): {text[:50]}...")
                bobby_speech_file.unlink()
                return
        except Exception as e:
            logger.warning(f"Error checking Bobby's speech filter: {e}")

    # Format transcript line
    timestamp = get_timestamp()
    if label:
        names = resolve_speaker_names(SPEAKER_NAMES, SPEAKER_NAMES_FILE)
        line = f"[{timestamp}] {format_speaker_label(label, names)} {text}\n"
    else:
        line = f"[{timestamp}] {text}\n"

    # Open, write, close - triggers IDE file watchers immediately
    with open(TRANSCRIPT_FILE, 'a') as f:
        f.write(line)

    logger.info(f"TRANSCRIPT: {line.strip()}")


def on_begin(self, event: BeginEvent):
    """Called when streaming session starts"""
    global _written_turn_orders
    _written_turn_orders = set()  # fresh session => turn_order restarts
    if _sidecar:
        _sidecar.handle_event("Begin", event.model_dump())
    logger.info(f"Streaming session started: {event.id}")
    logger.info("Listening for audio... (Press Ctrl+C to stop)")


def _speaker_label(event):
    """
    Raw diarization label for a finalized turn, or None when labels are off.

    Display-only: should_write_turn still decides WHICH turns get written, so
    enabling labels cannot change trigger behavior.
    """
    if not SPEAKER_LABELS_ENABLED:
        return None
    return turn_speaker_label(event.words or [], event.speaker_label)


def on_turn(self, event: TurnEvent):
    """
    Called for each transcription turn.

    Wake-word mode: finalized-turn gating and dedupe live in
    streaming.should_write_turn (shared with Discord mode — keep the two
    modes identical). Partials are discarded there so a trigger can't fire
    mid-word; speaker labels are added to the written line only when
    BOBBY_SPEAKER_LABELS=1.

    Sidecar mode (BOBBY_SIDECAR=1): every turn event — partials included —
    feeds the v2 pipeline (bobby/sidecar.py), which logs it to events.jsonl
    and re-renders the transcript with labels, a live partial line, and
    overlap recovery. See docs/2026-08-05-sidecar-v2-design.md.
    """
    if _sidecar:
        _sidecar.handle_event("Turn", event.model_dump())
        return
    if should_write_turn(event, _written_turn_orders):
        write_transcript(event.transcript, label=_speaker_label(event))


def on_speaker_revision(self, event):
    """Sidecar mode only: server retroactively revised earlier turns' labels."""
    if _sidecar:
        _sidecar.handle_event("SpeakerRevision", event.model_dump())


def on_terminated(self, event: TerminationEvent):
    """Called when streaming session ends"""
    if _sidecar:
        _sidecar.handle_event("Termination", event.model_dump())
    duration = event.audio_duration_seconds
    logger.info(
        "Session terminated: "
        + (f"{duration:.1f} seconds of audio processed" if duration is not None else "no duration reported")
    )


def on_error(self, error: StreamingError):
    """Called when an error occurs"""
    logger.error(f"Streaming error: {error}")


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    logger.info("\nShutting down gracefully...")
    cleanup()
    sys.exit(0)


def cleanup():
    """Clean up resources"""
    global client

    if client:
        try:
            client.disconnect(terminate=True)
            logger.info("Disconnected from Assembly AI")
        except Exception as e:
            logger.error(f"Error disconnecting client: {e}")


def check_environment():
    """Check that all required environment variables and setup are present"""
    # Load environment variables
    load_dotenv()

    # Check for API key
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key or api_key == "your_api_key_here":
        logger.error("ASSEMBLYAI_API_KEY not set!")
        logger.error("Please create a .env file with your Assembly AI API key")
        logger.error("See .env.example for template")
        return None

    return api_key


def main():
    """Main function to run audio capture and transcription"""
    global client, _sidecar

    # Set up signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    logger.info("=" * 60)
    logger.info("Bobby Audio Capture - Component 1"
                + (" [SIDECAR v2]" if SIDECAR_MODE else ""))
    logger.info("=" * 60)

    # Check environment
    api_key = check_environment()
    if not api_key:
        sys.exit(1)

    # Write session header to transcript
    logger.info(f"Writing transcripts to: {TRANSCRIPT_FILE}")

    if SIDECAR_MODE:
        # v2 pipeline: transcript is a derived view the writer rewrites in
        # full, so no append-mode session header — events.jsonl carries the
        # session boundaries instead.
        _sidecar = SidecarWriter(
            TRANSCRIPT_FILE,
            EVENTS_FILE,
            speaker_names=SPEAKER_NAMES,
            speaker_names_file=SPEAKER_NAMES_FILE,
        )
        logger.info(f"Sidecar event log: {EVENTS_FILE}")
    else:
        timestamp = get_timestamp()
        with open(TRANSCRIPT_FILE, 'a') as f:
            f.write(f"\n[{timestamp}] === New Recording Session ===\n\n")

    # Create audio stream
    # Set use_default_mic=True to test with your MacBook mic
    # Set use_default_mic=False to use BlackHole (for capturing Zoom/meeting audio)
    USE_DEFAULT_MIC = True  # Change to False for production use with BlackHole

    try:
        audio_stream = BlackHoleAudioStream(
            sample_rate=16000,
            chunk_size=1024,
            use_default_mic=USE_DEFAULT_MIC
        )
        audio_stream.start()
    except Exception as e:
        logger.error(f"Failed to initialize audio: {e}")
        cleanup()
        sys.exit(1)

    # Create Assembly AI streaming client
    try:
        logger.info("Connecting to Assembly AI streaming service...")

        client = StreamingClient(
            StreamingClientOptions(
                api_key=api_key,
                api_host="streaming.assemblyai.com",
            )
        )

        # Register event handlers
        client.on(StreamingEvents.Begin, on_begin)
        client.on(StreamingEvents.Turn, on_turn)
        client.on(StreamingEvents.Termination, on_terminated)
        client.on(StreamingEvents.Error, on_error)
        if SIDECAR_MODE:
            client.on(StreamingEvents.SpeakerRevision, on_speaker_revision)

        # Connect with streaming parameters.
        # speech_model + prompt + keyterms come from config (shared with Discord
        # mode). format_turns is intentionally omitted: Universal-3.5 Pro formats
        # finalized turns inline, and on_turn dedupes by turn_order regardless.
        # Sidecar mode adds diarization + partials — measured on the 2026-08-04
        # call replay: labels ~99% word-accurate, finals every ~10s instead of
        # 60s walls, and partials carry overlapped interjections (see
        # docs/2026-08-05-sidecar-v2-design.md). Wake-word mode keeps the lean
        # parameters, adding diarization alone when BOBBY_SPEAKER_LABELS=1 —
        # never partials, which would let a trigger fire mid-word.
        params = dict(
            sample_rate=16000,
            speech_model=STREAMING_SPEECH_MODEL,
            prompt=STREAMING_PROMPT,
            keyterms_prompt=STREAMING_KEYTERMS,
        )
        if SIDECAR_MODE:
            params.update(
                speaker_labels=True,
                max_speakers=SIDECAR_MAX_SPEAKERS,
                include_partial_turns=True,
                continuous_partials=True,
            )
        elif SPEAKER_LABELS_ENABLED:
            params.update(
                speaker_labels=True,
                max_speakers=SIDECAR_MAX_SPEAKERS,
            )
        client.connect(StreamingParameters(**params))

        logger.info("Connected to Assembly AI")
        logger.info("Starting real-time transcription...")

        # Stream audio to Assembly AI
        client.stream(audio_stream)

    except KeyboardInterrupt:
        logger.info("\nStopping...")
    except Exception as e:
        logger.error(f"Error during streaming: {e}")
    finally:
        # Clean up
        audio_stream.close()
        cleanup()
        logger.info("Audio capture stopped")


if __name__ == "__main__":
    main()
