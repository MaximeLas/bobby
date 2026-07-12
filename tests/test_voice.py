#!/usr/bin/env python3
"""
Automated tests for bobby.voice — the shared local-mode speech helper.

Does NOT produce audio: bobby.tts is replaced with a fake module so tests
never construct the ElevenLabs client or shell out to `say`.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bobby.config import PAUSE_FLAG_FILE, BOBBY_SPEECH_FILE
from bobby import voice


def _fake_tts(speak_side_effect=None):
    """Build a fake bobby.tts module whose speak() can be instrumented."""
    fake = MagicMock()
    fake.speak = MagicMock(side_effect=speak_side_effect, return_value=True)
    return fake


def test_speaks_via_tts_and_cleans_up():
    """Happy path: tts.speak is called, pause flag is gone afterwards,
    and the utterance is recorded for self-speech filtering."""
    PAUSE_FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
    fake = _fake_tts()

    try:
        with patch.dict(sys.modules, {"bobby.tts": fake}):
            result = voice.speak_in_meeting("Great success!")

        assert result is True
        fake.speak.assert_called_once_with("Great success!")
        assert not PAUSE_FLAG_FILE.exists(), "Pause flag must be removed after speech"
        assert BOBBY_SPEECH_FILE.exists(), "Spoken text must be recorded"
        assert BOBBY_SPEECH_FILE.read_text() == "great success!"
    finally:
        PAUSE_FLAG_FILE.unlink(missing_ok=True)
        BOBBY_SPEECH_FILE.unlink(missing_ok=True)


def test_pauses_transcription_while_speaking():
    """The pause flag must exist DURING tts.speak (that's the whole point)."""
    PAUSE_FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)
    flag_seen = {}

    def check_flag(text):
        flag_seen["during"] = PAUSE_FLAG_FILE.exists()
        return True

    fake = _fake_tts(speak_side_effect=check_flag)

    try:
        with patch.dict(sys.modules, {"bobby.tts": fake}):
            voice.speak_in_meeting("Is finished!")

        assert flag_seen.get("during") is True, \
            "Pause flag must be present while Bobby is speaking"
        assert not PAUSE_FLAG_FILE.exists()
    finally:
        PAUSE_FLAG_FILE.unlink(missing_ok=True)
        BOBBY_SPEECH_FILE.unlink(missing_ok=True)


def test_tts_import_failure_falls_back_to_say():
    """If bobby.tts can't even import, fall back to the `say` command —
    and still clean up the pause flag."""
    PAUSE_FLAG_FILE.parent.mkdir(parents=True, exist_ok=True)

    try:
        with patch.dict(sys.modules, {"bobby.tts": None}), \
             patch.object(voice.subprocess, "run") as fake_run:
            result = voice.speak_in_meeting("Not great success.")

        assert result is True
        fake_run.assert_called_once()
        assert "Not great success." in fake_run.call_args[0][0]
        assert not PAUSE_FLAG_FILE.exists()
    finally:
        PAUSE_FLAG_FILE.unlink(missing_ok=True)
        BOBBY_SPEECH_FILE.unlink(missing_ok=True)


ALL_TESTS = [
    ("Speaks via tts and cleans up state files", test_speaks_via_tts_and_cleans_up),
    ("Pause flag present during speech", test_pauses_transcription_while_speaking),
    ("tts import failure falls back to say", test_tts_import_failure_falls_back_to_say),
]
