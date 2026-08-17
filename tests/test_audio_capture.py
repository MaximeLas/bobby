#!/usr/bin/env python3
"""
Automated tests for bobby.audio_capture's transcript line writing and the
optional speaker labels of wake-word mode (BOBBY_SPEAKER_LABELS=1).

Driven by real assemblyai.streaming.v3 TurnEvent objects — the point of these
tests is that the label really is read off the SDK's own model — but fully
offline: no audio device, no socket, no key.
"""

import importlib
import logging
import os
import re
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from assemblyai.streaming.v3 import TurnEvent
from assemblyai.streaming.v3.models import Word

from bobby.audio_capture import _speaker_label, write_transcript

# write_transcript logs every line it writes; keep the runner's output readable.
logging.getLogger("bobby.audio_capture").setLevel(logging.WARNING)


def _turn(text="hello world", label=None, word_speakers=()):
    """A finalized TurnEvent, optionally carrying per-word speakers."""
    words = [
        Word(start=i, end=i + 1, text=f"w{i}", confidence=1.0,
             word_is_final=True, speaker=speaker)
        for i, speaker in enumerate(word_speakers)
    ]
    return TurnEvent(
        type="Turn", turn_order=0, turn_is_formatted=True, end_of_turn=True,
        transcript=text, end_of_turn_confidence=1.0, words=words,
        speaker_label=label,
    )


@contextmanager
def _reloaded_config(**overrides):
    """Reload bobby.config under env overrides (None unsets), then restore."""
    from bobby import config

    saved = {name: os.environ.get(name) for name in overrides}
    try:
        for name, value in overrides.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        importlib.reload(config)
        yield config
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        importlib.reload(config)


def _written_line(text, label=None, speaker_names=None, names_file_content=None):
    """Run write_transcript with every workspace path redirected to a tmpdir."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        names_file = tmp / "speaker_names.txt"
        if names_file_content is not None:
            names_file.write_text(names_file_content)

        with patch.multiple(
            "bobby.audio_capture",
            TRANSCRIPT_FILE=tmp / "meeting_transcript.txt",
            PAUSE_FLAG_FILE=tmp / "pause_transcription.flag",
            BOBBY_SPEECH_FILE=tmp / "bobby_last_speech.txt",
            SPEAKER_NAMES=speaker_names or {},
            SPEAKER_NAMES_FILE=names_file,
        ):
            write_transcript(text, label=label)

        return (tmp / "meeting_transcript.txt").read_text()


# --- Flag default ---

def test_speaker_labels_off_by_default():
    """Wake-word mode stays lean unless explicitly asked for labels."""
    with _reloaded_config(BOBBY_SPEAKER_LABELS=None) as config:
        assert config.SPEAKER_LABELS_ENABLED is False


def test_speaker_labels_env_enables():
    """BOBBY_SPEAKER_LABELS accepts the same truthy values as BOBBY_PROACTIVE."""
    for value in ("1", "true", "yes"):
        with _reloaded_config(BOBBY_SPEAKER_LABELS=value) as config:
            assert config.SPEAKER_LABELS_ENABLED is True, f"{value!r} should enable labels"
    with _reloaded_config(BOBBY_SPEAKER_LABELS="0") as config:
        assert config.SPEAKER_LABELS_ENABLED is False


# --- Line formatting ---

def test_line_without_label_is_unchanged():
    """Flag off (label=None) must write exactly the line Bobby always wrote."""
    line = _written_line("hello world")
    assert re.fullmatch(r"\[\d\d:\d\d:\d\d\] hello world\n", line), repr(line)


def test_line_with_unmapped_label():
    """With no name mapping, the raw diarization label is shown."""
    line = _written_line("hello world", label="A")
    assert re.fullmatch(r"\[\d\d:\d\d:\d\d\] \[A\] hello world\n", line), repr(line)


def test_line_with_mapped_name_from_file():
    """speaker_names.txt maps the label at write time (settable mid-meeting)."""
    line = _written_line("hello world", label="A", names_file_content="A=Max\nB=David\n")
    assert re.fullmatch(r"\[\d\d:\d\d:\d\d\] \[Max\] hello world\n", line), repr(line)


def test_line_with_mapped_name_from_env_dict():
    """BOBBY_SPEAKER_NAMES (parsed into config.SPEAKER_NAMES) maps too."""
    line = _written_line("hello world", label="B", speaker_names={"A": "Max", "B": "David"})
    assert re.fullmatch(r"\[\d\d:\d\d:\d\d\] \[David\] hello world\n", line), repr(line)


# --- Label extraction from the SDK event ---

def test_no_label_extracted_when_flag_off():
    """Flag off must yield None even when the event carries a label."""
    with patch("bobby.audio_capture.SPEAKER_LABELS_ENABLED", False):
        assert _speaker_label(_turn(label="A")) is None


def test_label_extracted_from_event():
    """Flag on reads TurnEvent.speaker_label."""
    with patch("bobby.audio_capture.SPEAKER_LABELS_ENABLED", True):
        assert _speaker_label(_turn(label="A")) == "A"


def test_label_falls_back_to_word_speakers():
    """Without a turn-level label, the last labeled SDK Word decides."""
    with patch("bobby.audio_capture.SPEAKER_LABELS_ENABLED", True):
        assert _speaker_label(_turn(label=None, word_speakers=("A", "A", "B"))) == "B"


def test_label_none_when_event_carries_nothing():
    """No label anywhere: write an unlabeled line rather than a "[?]" one."""
    with patch("bobby.audio_capture.SPEAKER_LABELS_ENABLED", True):
        assert _speaker_label(_turn(label=None)) is None


ALL_TESTS = [
    ("Speaker labels: off by default", test_speaker_labels_off_by_default),
    ("Speaker labels: env var enables", test_speaker_labels_env_enables),
    ("Transcript line: unlabeled format unchanged", test_line_without_label_is_unchanged),
    ("Transcript line: raw label when unmapped", test_line_with_unmapped_label),
    ("Transcript line: name from speaker_names.txt", test_line_with_mapped_name_from_file),
    ("Transcript line: name from SPEAKER_NAMES", test_line_with_mapped_name_from_env_dict),
    ("Label extraction: none while flag is off", test_no_label_extracted_when_flag_off),
    ("Label extraction: from TurnEvent.speaker_label", test_label_extracted_from_event),
    ("Label extraction: falls back to word speakers", test_label_falls_back_to_word_speakers),
    ("Label extraction: none when event has no label", test_label_none_when_event_carries_nothing),
]
