#!/usr/bin/env python3
"""
Bobby Discord Sink - Custom Pycord Sink for real-time audio streaming

Receives per-user PCM audio from Discord voice channels and routes it
to Assembly AI for real-time transcription.

Audio format from Pycord: 48kHz stereo PCM16 (s16le), 3840 bytes per chunk (20ms).
We convert stereo→mono, buffer to 60ms (Assembly AI minimum is 50ms), and feed
chunks into per-user queues consumed by per-user Assembly AI streaming threads.

Each speaking Discord user gets their own Assembly AI session. Transcripts are
written as [Username] text to meeting_transcript.txt.
"""

import io
import logging
import os
import struct
import threading
from queue import Queue

from discord.sinks.core import Sink, Filters, AudioData, default_filters

from bobby.config import TRANSCRIPT_FILE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
# Silence noisy libraries
logging.getLogger("discord.gateway").setLevel(logging.WARNING)
logging.getLogger("discord.client").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)
logging.getLogger("aiohttp").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("assemblyai").setLevel(logging.WARNING)

# Sentinel value to signal the audio iterator to stop
_STOP_SENTINEL = None


def stereo_to_mono(data: bytes) -> bytes:
    """
    Convert 48kHz stereo PCM16 to mono by averaging L+R channels.

    Input: 3840 bytes (960 stereo frames × 2 channels × 2 bytes)
    Output: 1920 bytes (960 mono frames × 2 bytes)
    """
    num_samples = len(data) // 2
    samples = struct.unpack(f"<{num_samples}h", data)
    mono = []
    for i in range(0, len(samples), 2):
        avg = (samples[i] + samples[i + 1]) // 2
        mono.append(avg)
    return struct.pack(f"<{len(mono)}h", *mono)


class AudioQueueIterator:
    """
    Iterator that blocks on a queue, yielding audio chunks.

    Designed to feed Assembly AI's blocking client.stream() call.
    Stops when it receives the _STOP_SENTINEL value.
    """

    def __init__(self, queue: Queue):
        self._queue = queue

    def __iter__(self):
        return self

    def __next__(self):
        chunk = self._queue.get()
        if chunk is _STOP_SENTINEL:
            raise StopIteration
        return chunk


class _UserStream:
    """Per-user state: audio queue, mono buffer, Assembly AI thread, and connection gate."""

    def __init__(self, user_id, display_name):
        self.user_id = user_id
        self.display_name = display_name
        self.queue = Queue(maxsize=500)  # ~10 seconds of audio buffer
        self.mono_buffer = bytearray()
        self.thread = None
        self.client = None
        self.connected = threading.Event()


class AssemblyAISink(Sink):
    """
    Custom Pycord Sink that streams Discord voice audio to Assembly AI.

    Each speaking user gets their own Assembly AI streaming session.
    Transcripts are written as [Username] text to meeting_transcript.txt.
    """

    # 48kHz * 2 bytes * 60ms = 5760 bytes (3 Pycord chunks)
    MIN_SEND_BYTES = 5760

    def __init__(self, *, guild=None, filters=None):
        if filters is None:
            filters = default_filters
        self.filters = filters
        Filters.__init__(self, **self.filters)
        self.vc = None
        self.audio_data = {}
        self.encoding = "pcm"

        # Guild reference for resolving user IDs to display names
        self._guild = guild

        # Per-user streams: {user_id: _UserStream}
        self._user_streams = {}
        self._lock = threading.Lock()

        self._api_key = None
        self._running = False

    def start_transcription(self):
        """Validate API key and mark sink as ready to create per-user sessions."""
        self._api_key = os.getenv("ASSEMBLYAI_API_KEY")
        if not self._api_key or self._api_key == "your_api_key_here":
            logger.error("ASSEMBLYAI_API_KEY not set! Cannot start transcription.")
            return False

        self._running = True
        logger.info("Assembly AI transcription ready (per-user sessions on demand)")
        return True

    def _get_display_name(self, user_id):
        """Resolve a Discord user ID to a display name."""
        if self._guild:
            member = self._guild.get_member(user_id)
            if member:
                return member.display_name
        return f"User-{user_id}"

    def _get_or_create_stream(self, user_id):
        """Get existing user stream or create a new one with its own AAI session."""
        with self._lock:
            if user_id in self._user_streams:
                return self._user_streams[user_id]

            display_name = self._get_display_name(user_id)
            stream = _UserStream(user_id, display_name)

            stream.thread = threading.Thread(
                target=self._run_assemblyai_stream,
                args=(stream,),
                daemon=True,
                name=f"bobby-aai-{display_name}",
            )
            stream.thread.start()

            self._user_streams[user_id] = stream
            logger.info(f"Started Assembly AI session for {display_name} (user {user_id})")
            return stream

    def stop_transcription(self):
        """Stop all per-user Assembly AI streaming threads. Idempotent."""
        self._running = False

        # Atomically grab and clear — prevents double-stop races
        with self._lock:
            streams = list(self._user_streams.values())
            self._user_streams.clear()

        if not streams:
            return  # Already stopped or never started

        for stream in streams:
            try:
                stream.queue.put_nowait(_STOP_SENTINEL)
            except Exception:
                pass

        for stream in streams:
            if stream.thread and stream.thread.is_alive():
                stream.thread.join(timeout=5)
                if stream.thread.is_alive():
                    logger.warning(f"AAI thread for {stream.display_name} did not stop within 5s")

        logger.info("All Assembly AI sessions stopped")

    def _run_assemblyai_stream(self, stream: _UserStream):
        """
        Background thread: run Assembly AI streaming client for one user.

        This thread blocks on client.stream(iterator), where the iterator
        blocks on queue.get(). When the queue receives _STOP_SENTINEL,
        the iterator raises StopIteration and the stream ends.
        """
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

        logger.info(f"[{stream.display_name}] Connecting to Assembly AI (48kHz mono)...")

        try:
            stream.client = StreamingClient(
                StreamingClientOptions(
                    api_key=self._api_key,
                    api_host="streaming.assemblyai.com",
                )
            )

            def on_begin(client, event: BeginEvent):
                logger.info(f"[{stream.display_name}] Assembly AI session started: {event.id}")
                stream.connected.set()

            def on_turn(client, event: TurnEvent):
                if not event.end_of_turn:
                    return
                if not event.turn_is_formatted:
                    return
                if event.transcript and event.transcript.strip():
                    self._write_transcript(event.transcript, stream.display_name)

            def on_terminated(client, event: TerminationEvent):
                logger.info(
                    f"[{stream.display_name}] Assembly AI session ended: "
                    f"{event.audio_duration_seconds:.1f}s processed"
                )

            def on_error(client, error: StreamingError):
                logger.error(f"[{stream.display_name}] Assembly AI error: {error}")

            stream.client.on(StreamingEvents.Begin, on_begin)
            stream.client.on(StreamingEvents.Turn, on_turn)
            stream.client.on(StreamingEvents.Termination, on_terminated)
            stream.client.on(StreamingEvents.Error, on_error)

            stream.client.connect(
                StreamingParameters(
                    sample_rate=48000,
                    format_turns=True,
                )
            )

            logger.info(f"[{stream.display_name}] Connected, streaming audio...")

            iterator = AudioQueueIterator(stream.queue)
            stream.client.stream(iterator)

        except Exception as e:
            if self._running:
                logger.error(f"[{stream.display_name}] Assembly AI streaming error: {e}")
            else:
                logger.info(f"[{stream.display_name}] Assembly AI stream ended (shutdown)")
        finally:
            if stream.client:
                try:
                    stream.client.disconnect(terminate=True)
                except Exception:
                    pass
            logger.info(f"[{stream.display_name}] Assembly AI thread exiting")

    def _write_transcript(self, text: str, display_name: str):
        """Write a speaker-labeled transcript line to the shared transcript file."""
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] [{display_name}] {text}\n"

        try:
            with open(TRANSCRIPT_FILE, "a") as f:
                f.write(line)
            logger.info(f"TRANSCRIPT: {line.strip()}")
        except Exception as e:
            logger.error(f"Error writing transcript: {e}")

    @Filters.container
    def write(self, data, user):
        """
        Called by Pycord for each decoded audio chunk (~50x/sec per speaking user).

        Routes audio to the appropriate per-user Assembly AI session.
        """
        # Still store in audio_data so Pycord's cleanup/callback works
        if user not in self.audio_data:
            file = io.BytesIO()
            self.audio_data[user] = AudioData(file)
            logger.info(f"First audio from user {user}, stereo chunk size: {len(data)} bytes")
        self.audio_data[user].write(data)

        if not self._running:
            return

        # Get or create per-user stream (lazily starts AAI session on first audio)
        stream = self._get_or_create_stream(user)

        # Only buffer audio after this user's AAI connection is confirmed
        if not stream.connected.is_set():
            return

        try:
            mono_data = stereo_to_mono(data)
            stream.mono_buffer.extend(mono_data)

            # Drain buffer in fixed-size chunks (60ms each)
            chunks_sent = 0
            while len(stream.mono_buffer) >= self.MIN_SEND_BYTES:
                chunk = bytes(stream.mono_buffer[:self.MIN_SEND_BYTES])
                del stream.mono_buffer[:self.MIN_SEND_BYTES]
                stream.queue.put_nowait(chunk)
                chunks_sent += 1
            if chunks_sent > 1:
                logger.debug(f"[{stream.display_name}] Drained {chunks_sent} chunks (60ms each)")
        except Exception:
            pass  # Drop frame if queue is full (better than blocking Pycord)

    def format_audio(self, audio):
        """Called during cleanup. No-op since we stream in real-time."""
        audio.on_format(self.encoding)

    def cleanup(self):
        """Stop transcription and clean up."""
        self.stop_transcription()
        self.finished = True
        for file in self.audio_data.values():
            file.cleanup()
            self.format_audio(file)
