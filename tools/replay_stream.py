#!/usr/bin/env python3
"""
Replay a local audio file through AssemblyAI streaming v3 at a controlled pace,
logging EVERY event (Begin/Turn/SpeakerRevision/Warning/Error/Termination) as
JSONL — one record per event, full payload, wall-clock + audio-clock stamps.

Purpose: the 2026-08-04 Steven call gave us mic-vs-batch coverage numbers but
could not separate model from microphone, and never tested speaker_labels /
include_partial_turns / continuous_partials. Feeding the SAME .m4a the batch
engines transcribed makes mode the only variable, and the JSONL answers the
event-shape questions (partial cadence, revision behavior) directly.

Origin: built 2026-08-05 for the Steven-call replay experiment (meetings repo,
docs/experiments/2026-08-05-streaming-replay-partials-diarization.md). It is
also the deterministic test rig for sidecar v2 (docs/2026-08-05-sidecar-v2-design.md).

Usage:
  uv run python tools/replay_stream.py AUDIO --out events.jsonl \
      [--start SEC] [--duration SEC] [--speed 1.0] \
      [--speaker-labels] [--max-speakers 2] [--partials] [--continuous-partials] \
      [--mode balanced|min_latency|max_accuracy] [--prompt ...] [--keyterms a,b,c]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from assemblyai.streaming.v3 import (  # noqa: E402
    StreamingClient,
    StreamingClientOptions,
    StreamingEvents,
    StreamingParameters,
)

SAMPLE_RATE = 16000
BYTES_PER_SEC = SAMPLE_RATE * 2  # s16le mono
CHUNK_MS = 100
CHUNK_BYTES = BYTES_PER_SEC * CHUNK_MS // 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--out", required=True)
    ap.add_argument("--start", type=float, default=0.0, help="seek into audio (sec)")
    ap.add_argument("--duration", type=float, default=None)
    ap.add_argument("--speed", type=float, default=1.0, help="1.0 = real-time pacing")
    ap.add_argument("--speaker-labels", action="store_true")
    ap.add_argument("--max-speakers", type=int, default=None)
    ap.add_argument("--partials", action="store_true", help="include_partial_turns=True")
    ap.add_argument("--continuous-partials", action="store_true")
    ap.add_argument("--mode", default=None)
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--keyterms", default=None, help="comma-separated")
    args = ap.parse_args()

    if not os.getenv("ASSEMBLYAI_API_KEY"):
        sys.exit("ASSEMBLYAI_API_KEY not set (expected in ~/Projects/bobby/.env)")

    out = open(args.out, "a", buffering=1)
    t0 = time.monotonic()
    sent = {"bytes": 0}
    counts = {}

    def emit(kind, payload):
        counts[kind] = counts.get(kind, 0) + 1
        rec = {
            "wall": datetime.now().isoformat(timespec="milliseconds"),
            "elapsed": round(time.monotonic() - t0, 3),
            "audio_sent_sec": round(sent["bytes"] / BYTES_PER_SEC, 2),
            "type": kind,
            "data": payload,
        }
        out.write(json.dumps(rec, default=str) + "\n")

    def on_event(kind):
        def handler(_client, event):
            try:
                payload = event.model_dump()
            except AttributeError:
                payload = {"repr": repr(event)}
            emit(kind, payload)
            if kind in ("Error", "Warning", "Begin", "Termination", "SpeakerRevision"):
                print(f"[{kind}] {payload}", flush=True)
        return handler

    client = StreamingClient(StreamingClientOptions(api_key=os.environ["ASSEMBLYAI_API_KEY"]))
    for ev in ("Begin", "Turn", "SpeakerRevision", "Warning", "Error", "Termination"):
        client.on(StreamingEvents[ev], on_event(ev))

    params = dict(
        sample_rate=SAMPLE_RATE,
        speech_model="universal-3-5-pro",
    )
    if args.speaker_labels:
        params["speaker_labels"] = True
    if args.max_speakers:
        params["max_speakers"] = args.max_speakers
    if args.partials:
        params["include_partial_turns"] = True
    if args.continuous_partials:
        params["continuous_partials"] = True
    if args.mode:
        params["mode"] = args.mode
    if args.prompt:
        params["prompt"] = args.prompt
    if args.keyterms:
        params["keyterms_prompt"] = [t.strip() for t in args.keyterms.split(",") if t.strip()]

    emit("Meta", {"argv": sys.argv[1:], "params": {k: v for k, v in params.items()}})
    client.connect(StreamingParameters(**params))

    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error"]
    if args.start:
        cmd += ["-ss", str(args.start)]
    cmd += ["-i", args.audio]
    if args.duration:
        cmd += ["-t", str(args.duration)]
    cmd += ["-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "-"]
    ff = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    chunk_wall = (CHUNK_MS / 1000.0) / args.speed
    next_send = time.monotonic()
    try:
        while True:
            data = ff.stdout.read(CHUNK_BYTES)
            if not data:
                break
            now = time.monotonic()
            if now < next_send:
                time.sleep(next_send - now)
            client.stream(data)
            sent["bytes"] += len(data)
            next_send += chunk_wall
    except KeyboardInterrupt:
        print("interrupted", flush=True)
    finally:
        ff.terminate()
        # Give the server time to flush trailing turns + any final recluster.
        time.sleep(3)
        client.disconnect(terminate=True)
        emit("Meta", {"done": True, "audio_sec_sent": sent["bytes"] / BYTES_PER_SEC})
        out.close()

    print(f"sent {sent['bytes'] / BYTES_PER_SEC:.1f}s of audio; events: {counts}", flush=True)


if __name__ == "__main__":
    main()
