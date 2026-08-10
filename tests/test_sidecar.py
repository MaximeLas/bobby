#!/usr/bin/env python3
"""
Automated tests for bobby.sidecar (the v2 transcript pipeline).

Driven by a RECORDED event log from the 2026-08-04 Steven-call replay
experiment (tests/fixtures/replay-smoke-38m.jsonl.gz — 150s of real call
audio through the real streaming endpoint with diarization + partials on),
plus small synthetic event sequences for the amend/overlap edge cases.
Fully offline and deterministic: no keys, no network.
"""

import gzip
import json
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bobby.sidecar import SidecarWriter

FIXTURE = Path(__file__).parent / "fixtures" / "replay-smoke-38m.jsonl.gz"


def _fixture_events():
    with gzip.open(FIXTURE, "rt") as f:
        return [json.loads(line) for line in f]


def _replay(events, tmpdir, **kwargs):
    w = SidecarWriter(
        Path(tmpdir) / "meeting_transcript.txt",
        Path(tmpdir) / "events.jsonl",
        **kwargs,
    )
    for rec in events:
        w.handle_event(rec["type"], rec.get("data") or {}, wall=rec.get("wall"))
    return w, (Path(tmpdir) / "meeting_transcript.txt")


def _turn(order, text, final, label=None, words=None):
    return {
        "type": "Turn", "turn_order": order, "turn_is_formatted": True,
        "end_of_turn": final, "transcript": text, "end_of_turn_confidence": 1.0,
        "words": words or [], "speaker_label": label,
    }


def test_fixture_replay_renders_labeled_transcript():
    """Replaying 150s of recorded real-call events yields a labeled transcript."""
    events = _fixture_events()
    with tempfile.TemporaryDirectory() as tmp:
        _, transcript = _replay(events, tmp)
        lines = transcript.read_text().splitlines()

        stamped = [l for l in lines if re.match(r"\[\d\d:\d\d:\d\d\] \[[AB]~?\] ", l)]
        assert len(stamped) >= 10, f"expected >=10 labeled lines, got {len(stamped)}"
        assert any(" [A] " in l for l in stamped), "no [A] lines rendered"
        assert any(" [B] " in l for l in stamped), "no [B] lines rendered"
        # Termination was replayed, so no live-partial line may remain.
        assert not any(l.startswith("⋯") for l in lines), "dangling partial line after Termination"


def test_fixture_replay_no_blackout():
    """With partials consumed, consecutive rendered lines are never >20s apart
    (the v1 pipeline showed 60s gaps on this same audio)."""
    events = _fixture_events()
    with tempfile.TemporaryDirectory() as tmp:
        _, transcript = _replay(events, tmp)
        stamps = []
        for l in transcript.read_text().splitlines():
            m = re.match(r"\[(\d\d):(\d\d):(\d\d)\]", l)
            if m:
                h, mn, s = int(m[1]), int(m[2]), int(m[3])
                stamps.append(h * 3600 + mn * 60 + s)
        gaps = [b - a for a, b in zip(stamps, stamps[1:])]
        assert gaps, "no stamped lines rendered"
        assert max(gaps) <= 20, f"blackout regression: max inter-line gap {max(gaps)}s"


def test_live_partial_is_last_line():
    """Mid-stream (no Termination yet), the in-flight partial renders as a
    trailing '⋯' line — the live view of what is being said right now."""
    events = _fixture_events()
    # Cut the replay right after the last partial Turn event.
    last_partial_idx = max(
        i for i, rec in enumerate(events)
        if rec["type"] == "Turn" and not rec["data"].get("end_of_turn")
    )
    with tempfile.TemporaryDirectory() as tmp:
        _, transcript = _replay(events[: last_partial_idx + 1], tmp)
        lines = transcript.read_text().splitlines()
        assert lines and lines[-1].startswith("⋯"), \
            f"expected trailing partial line, got: {lines[-1] if lines else '(empty)'}"


def test_amend_on_speaker_revision():
    """A SpeakerRevisionEvent must relabel an already-rendered line in place."""
    with tempfile.TemporaryDirectory() as tmp:
        seq = [
            {"type": "Begin", "wall": "2026-08-05T10:00:00", "data": {"id": "s1"}},
            {"type": "Turn", "wall": "2026-08-05T10:00:05",
             "data": _turn(0, "Hello there.", True, label="A")},
            {"type": "Turn", "wall": "2026-08-05T10:00:10",
             "data": _turn(1, "Hi, good to see you.", True, label="A")},
        ]
        w, transcript = _replay(seq, tmp)
        assert "[10:00:10] [A] Hi, good to see you." in transcript.read_text()

        w.handle_event("SpeakerRevision", {
            "revisions": [{"turn_order": 1, "speaker_label": "B", "words": []}]
        }, wall="2026-08-05T10:01:00")
        text = transcript.read_text()
        assert "[10:00:10] [B] Hi, good to see you." in text, f"label not amended:\n{text}"
        assert "[10:00:00] " not in text  # sanity: stamps come from turn walls
        assert "[10:00:05] [A] Hello there." in text  # untouched line survives


def test_overlap_recovery_and_resegmentation_suppression():
    """A word-run present in the last partial but absent from the final (and
    from the following finals) becomes an '[X~]' line; a run that merely moved
    into the next final (re-segmentation) must NOT."""
    words = lambda label, *ts: [  # noqa: E731
        {"start": 0, "end": 0, "confidence": 1.0, "text": t,
         "word_is_final": True, "speaker": label} for t in ts
    ]
    with tempfile.TemporaryDirectory() as tmp:
        seq = [
            {"type": "Begin", "wall": "2026-08-05T10:00:00", "data": {"id": "s1"}},
            # Partial carries B's interjection inside A's flow…
            {"type": "Turn", "wall": "2026-08-05T10:00:05", "data": _turn(
                0, "the clips are the product. No one watches the stream. It's a factory.",
                False,
                words=words("A", *"the clips are the product.".split())
                + words("B", *"No one watches the stream.".split())
                + words("A", *"It's a factory.".split()))},
            # …the final drops it.
            {"type": "Turn", "wall": "2026-08-05T10:00:08", "data": _turn(
                0, "the clips are the product. It's a factory.", True, label="A")},
            # Re-segmentation control: this partial's tail…
            {"type": "Turn", "wall": "2026-08-05T10:00:12", "data": _turn(
                1, "And another thing entirely. Which changes it all.", False)},
            {"type": "Turn", "wall": "2026-08-05T10:00:14", "data": _turn(
                1, "And another thing entirely.", True, label="A")},
            # …resurfaces as the NEXT final: not an overlap, no [~] line.
            {"type": "Turn", "wall": "2026-08-05T10:00:16", "data": _turn(
                2, "Which changes it all. Anyway.", True, label="A")},
            {"type": "Turn", "wall": "2026-08-05T10:00:20", "data": _turn(
                3, "Moving on to the next point now.", True, label="A")},
        ]
        _, transcript = _replay(seq, tmp)
        text = transcript.read_text()
        assert "[B~] No one watches the stream." in text, f"overlap not recovered:\n{text}"
        assert "Which changes it all." in text
        assert "[A~] Which changes it all." not in text and "[?~] Which changes" not in text, \
            f"re-segmented run wrongly flagged as overlap:\n{text}"


def test_bootstrap_survives_process_restart():
    """A fresh writer on the same events.jsonl (the restart-loop case) must
    reproduce the transcript, not wipe it."""
    events = _fixture_events()
    with tempfile.TemporaryDirectory() as tmp:
        _, transcript = _replay(events, tmp)
        before = transcript.read_text()
        assert before.strip(), "premise: transcript non-empty"

        # Simulates the restart loop relaunching bobby.audio_capture.
        SidecarWriter(transcript, Path(tmp) / "events.jsonl")
        after = transcript.read_text()
        assert after == before, "restart bootstrap changed the transcript"


def test_speaker_names_render_mapping():
    """speaker_names.txt maps raw labels to names at render time; raw labels
    stay in the event log (provenance)."""
    with tempfile.TemporaryDirectory() as tmp:
        names_file = Path(tmp) / "speaker_names.txt"
        names_file.write_text("A=Max\nB=Steven\n")
        seq = [
            {"type": "Begin", "wall": "2026-08-05T10:00:00", "data": {"id": "s1"}},
            {"type": "Turn", "wall": "2026-08-05T10:00:05",
             "data": _turn(0, "Hello there.", True, label="A")},
        ]
        _, transcript = _replay(seq, tmp, speaker_names_file=names_file)
        assert "[Max] Hello there." in transcript.read_text()
        logged = (Path(tmp) / "events.jsonl").read_text()
        assert '"speaker_label": "A"' in logged, "event log must keep raw labels"


ALL_TESTS = [
    ("Fixture replay renders labeled transcript", test_fixture_replay_renders_labeled_transcript),
    ("Fixture replay has no >20s blackout", test_fixture_replay_no_blackout),
    ("Live partial renders as trailing ⋯ line", test_live_partial_is_last_line),
    ("SpeakerRevision amends rendered lines", test_amend_on_speaker_revision),
    ("Overlap recovered; re-segmentation suppressed", test_overlap_recovery_and_resegmentation_suppression),
    ("Bootstrap survives process restart", test_bootstrap_survives_process_restart),
    ("speaker_names.txt maps labels at render", test_speaker_names_render_mapping),
]
