#!/usr/bin/env python3
"""
Automated tests for bobby.orchestrator

Tests the pure logic: answer extraction, trigger normalization, context reading,
debounce. Does NOT call any APIs, launch agents, or produce audio.
"""

import io
import os
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bobby.config import TRANSCRIPT_FILE


def _make_orchestrator(**kwargs):
    """Create an Orchestrator instance for testing (suppresses startup output)."""
    from bobby.orchestrator import Orchestrator
    with redirect_stdout(io.StringIO()):
        return Orchestrator(**kwargs)


def _normalize(text):
    """Replicate the trigger normalization logic from watch_transcript."""
    return ' '.join(text.lower().replace(',', '').replace('.', '').split())


# --- extract_answer tests ---

def test_extract_answer_simple():
    """Extract answer before 'thank you bobby'."""
    orch = _make_orchestrator()
    text = "[00:01] Speaker A: Use blue for buttons\n[00:02] Speaker A: Thank you, Bobby"
    answer = orch.extract_answer(text)
    assert "blue" in answer, f"Expected 'blue' in answer, got: {answer}"


def test_extract_answer_no_comma():
    """'thank you bobby' without comma should also work."""
    orch = _make_orchestrator()
    text = "[00:01] Speaker A: Monthly pricing\n[00:02] Speaker A: Thank you Bobby"
    answer = orch.extract_answer(text)
    assert "Monthly pricing" in answer, f"Expected 'Monthly pricing', got: {answer}"


def test_extract_answer_thanks_variant():
    """'thanks bobby' should also trigger extraction."""
    orch = _make_orchestrator()
    text = "[00:01] Speaker A: Use the dark theme\n[00:02] Speaker A: Thanks Bobby"
    answer = orch.extract_answer(text)
    assert "dark theme" in answer, f"Expected 'dark theme', got: {answer}"


def test_extract_answer_no_trigger():
    """With no trigger phrase, return the full text."""
    orch = _make_orchestrator()
    text = "[00:01] Speaker A: Just some discussion\n[00:02] Speaker B: Agreed"
    answer = orch.extract_answer(text)
    assert "discussion" in answer and "Agreed" in answer, \
        f"Expected full text, got: {answer}"


def test_extract_answer_multiple_lines():
    """With many lines before trigger, return last 3 non-empty lines."""
    orch = _make_orchestrator()
    text = (
        "[00:01] Line 1\n"
        "[00:02] Line 2\n"
        "[00:03] Line 3\n"
        "[00:04] Line 4\n"
        "[00:05] Line 5\n"
        "Thank you, Bobby"
    )
    answer = orch.extract_answer(text)
    assert "Line 3" in answer, f"Expected Line 3, got: {answer}"
    assert "Line 5" in answer, f"Expected Line 5, got: {answer}"
    assert "Line 1" not in answer, f"Line 1 should be excluded, got: {answer}"


def test_extract_answer_single_line():
    """Single answer line before trigger."""
    orch = _make_orchestrator()
    text = "[00:01] Just one answer\n[00:02] Thank you Bobby"
    answer = orch.extract_answer(text)
    assert "Just one answer" in answer, f"Expected 'Just one answer', got: {answer}"


def test_extract_answer_empty_before_trigger():
    """Empty lines only before trigger should return empty string."""
    orch = _make_orchestrator()
    text = "\n\n\nThank you Bobby"
    answer = orch.extract_answer(text)
    assert answer == "", f"Expected empty string, got: {answer!r}"


def test_extract_answer_multiple_triggers():
    """With multiple 'thank you bobby', should use the last one (rfind)."""
    orch = _make_orchestrator()
    text = (
        "[00:01] First answer\n"
        "[00:02] Thank you Bobby\n"
        "[00:03] Actually, use red instead\n"
        "[00:04] Thank you, Bobby"
    )
    answer = orch.extract_answer(text)
    assert "red" in answer, f"Expected 'red' in answer (last trigger), got: {answer}"


# --- Trigger normalization tests ---

def test_normalize_basic_trigger():
    """Basic trigger phrase should normalize."""
    assert 'hey bobby please build this' in _normalize("Hey Bobby, please build this")


def test_normalize_with_punctuation():
    """Trigger with extra punctuation should still match."""
    assert 'hey bobby please build this' in _normalize("Hey, Bobby, please build this.")


def test_normalize_extra_whitespace():
    """Extra whitespace should be collapsed."""
    assert 'hey bobby please build this' in _normalize("Hey   Bobby   please  build  this")


def test_normalize_mixed_case():
    """Mixed case should be lowered."""
    assert 'hey bobby please build this' in _normalize("HEY BOBBY PLEASE BUILD THIS")


def test_normalize_resume_trigger():
    """Resume triggers should normalize."""
    assert 'thank you bobby' in _normalize("Thank you, Bobby")
    assert 'thanks bobby' in _normalize("Thanks Bobby!")


def test_normalize_trigger_in_longer_text():
    """Trigger embedded in longer text should still match (substring)."""
    text = "So yeah, hey bobby please build this and also add tests"
    assert 'hey bobby please build this' in _normalize(text)


# --- Debounce tests ---

def test_debounce_rejects_within_window():
    """A trigger within DEBOUNCE_SECONDS of the last one should be rejected."""
    from bobby.orchestrator import DEBOUNCE_SECONDS
    orch = _make_orchestrator()
    # Simulate a recent trigger
    orch.last_trigger_time = time.time()
    time_since = time.time() - orch.last_trigger_time
    assert time_since < DEBOUNCE_SECONDS, "Should be within debounce window"


def test_debounce_accepts_after_window():
    """A trigger after DEBOUNCE_SECONDS should be accepted."""
    from bobby.orchestrator import DEBOUNCE_SECONDS
    orch = _make_orchestrator()
    # Simulate a trigger that happened long ago
    orch.last_trigger_time = time.time() - DEBOUNCE_SECONDS - 1
    time_since = time.time() - orch.last_trigger_time
    assert time_since >= DEBOUNCE_SECONDS, "Should be past debounce window"


def test_debounce_initial_state():
    """Fresh orchestrator should accept the first trigger (last_trigger_time=0)."""
    from bobby.orchestrator import DEBOUNCE_SECONDS
    orch = _make_orchestrator()
    assert orch.last_trigger_time == 0, "Should start at 0"
    time_since = time.time() - orch.last_trigger_time
    assert time_since >= DEBOUNCE_SECONDS, "First trigger should always pass debounce"


# --- get_recent_context tests ---

def test_get_recent_context():
    """Should return last N lines from transcript."""
    TRANSCRIPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(TRANSCRIPT_FILE, 'w') as f:
            for i in range(10):
                f.write(f"[00:00:{i:02d}] Line {i}\n")

        orch = _make_orchestrator()
        context = orch.get_recent_context(lines=3)

        assert "Line 7" in context, f"Expected Line 7, got: {context}"
        assert "Line 8" in context, f"Expected Line 8, got: {context}"
        assert "Line 9" in context, f"Expected Line 9, got: {context}"
        assert "Line 0" not in context, f"Line 0 should be excluded, got: {context}"
    finally:
        if TRANSCRIPT_FILE.exists():
            TRANSCRIPT_FILE.unlink()


def test_get_recent_context_missing_file():
    """Should return empty string if transcript doesn't exist."""
    if TRANSCRIPT_FILE.exists():
        TRANSCRIPT_FILE.unlink()

    orch = _make_orchestrator()
    context = orch.get_recent_context()
    assert context == "", f"Expected empty string, got: {context!r}"


def test_get_recent_context_fewer_lines():
    """Should return all lines if file has fewer than requested."""
    TRANSCRIPT_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(TRANSCRIPT_FILE, 'w') as f:
            f.write("[00:00:00] Only line\n")

        orch = _make_orchestrator()
        context = orch.get_recent_context(lines=10)
        assert "Only line" in context, f"Expected 'Only line', got: {context}"
    finally:
        if TRANSCRIPT_FILE.exists():
            TRANSCRIPT_FILE.unlink()


# --- Converse route tests ---

def test_converse_initial_state():
    """Fresh orchestrator should accept the first converse trigger."""
    from bobby.orchestrator import CONVERSE_DEBOUNCE_SECONDS
    orch = _make_orchestrator()
    assert orch.last_converse_time == 0
    assert time.time() - orch.last_converse_time >= CONVERSE_DEBOUNCE_SECONDS


def test_handle_conversation_speaks_answer():
    """A brain answer gets spoken."""
    from unittest.mock import patch, MagicMock
    orch = _make_orchestrator()
    orch.speak_bob = MagicMock()
    with patch("bobby.brain.ask_brain", return_value="Is going very nice!"):
        orch.handle_conversation()
    orch.speak_bob.assert_called_once_with("Is going very nice!")


def test_handle_conversation_speaks_fallback_on_failure():
    """A brain failure (None) speaks the error line, not silence."""
    from unittest.mock import patch, MagicMock
    from bobby.prompts import VOICE_BRAIN_ERROR
    orch = _make_orchestrator()
    orch.speak_bob = MagicMock()
    with patch("bobby.brain.ask_brain", return_value=None):
        orch.handle_conversation()
    orch.speak_bob.assert_called_once_with(VOICE_BRAIN_ERROR)


def test_speak_bob_delegates_to_shared_helper():
    """speak_bob must route through bobby.voice (single speech path)."""
    from unittest.mock import patch
    orch = _make_orchestrator()
    with patch("bobby.orchestrator.speak_in_meeting") as fake_speak:
        orch.speak_bob("Very nice!")
    fake_speak.assert_called_once_with("Very nice!")


# --- Import and instantiation tests ---

def test_import_orchestrator():
    """Orchestrator module should import without errors."""
    from bobby import orchestrator
    assert hasattr(orchestrator, 'Orchestrator')


def test_instantiate_orchestrator():
    """Orchestrator class should instantiate without errors."""
    orch = _make_orchestrator()
    assert hasattr(orch, 'extract_answer')
    assert hasattr(orch, 'get_recent_context')
    assert hasattr(orch, 'speak_bob')
    assert hasattr(orch, 'launch_agent')
    assert hasattr(orch, 'watch_transcript')


ALL_TESTS = [
    ("Import orchestrator module", test_import_orchestrator),
    ("Instantiate Orchestrator class", test_instantiate_orchestrator),
    ("extract_answer: simple case", test_extract_answer_simple),
    ("extract_answer: no comma variant", test_extract_answer_no_comma),
    ("extract_answer: 'thanks bobby' variant", test_extract_answer_thanks_variant),
    ("extract_answer: no trigger returns full text", test_extract_answer_no_trigger),
    ("extract_answer: multiple lines returns last 3", test_extract_answer_multiple_lines),
    ("extract_answer: single answer line", test_extract_answer_single_line),
    ("extract_answer: empty before trigger", test_extract_answer_empty_before_trigger),
    ("extract_answer: multiple triggers uses last", test_extract_answer_multiple_triggers),
    ("Trigger normalization: basic", test_normalize_basic_trigger),
    ("Trigger normalization: punctuation", test_normalize_with_punctuation),
    ("Trigger normalization: whitespace", test_normalize_extra_whitespace),
    ("Trigger normalization: mixed case", test_normalize_mixed_case),
    ("Trigger normalization: resume triggers", test_normalize_resume_trigger),
    ("Trigger normalization: embedded in longer text", test_normalize_trigger_in_longer_text),
    ("Debounce: rejects within window", test_debounce_rejects_within_window),
    ("Debounce: accepts after window", test_debounce_accepts_after_window),
    ("Debounce: initial state accepts first trigger", test_debounce_initial_state),
    ("Converse: initial state accepts first trigger", test_converse_initial_state),
    ("Converse: brain answer is spoken", test_handle_conversation_speaks_answer),
    ("Converse: brain failure speaks fallback line", test_handle_conversation_speaks_fallback_on_failure),
    ("speak_bob delegates to shared voice helper", test_speak_bob_delegates_to_shared_helper),
    ("get_recent_context: last N lines", test_get_recent_context),
    ("get_recent_context: missing file", test_get_recent_context_missing_file),
    ("get_recent_context: fewer lines than requested", test_get_recent_context_fewer_lines),
]
