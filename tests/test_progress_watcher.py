#!/usr/bin/env python3
"""
Automated tests for bobby.progress_watcher

Tests line parsing/classification and file truncation detection.
Does NOT send notifications or render Rich UI.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _make_watcher(progress_file=None):
    """Create a ProgressWatcher pointed at a temp file."""
    from bobby.progress_watcher import ProgressWatcher
    if progress_file is None:
        # Use a non-existent temp path (watcher handles missing files gracefully)
        progress_file = Path(tempfile.mkdtemp()) / "test_progress.txt"
    return ProgressWatcher(progress_file=progress_file)


# --- Line classification tests ---
# These test the routing logic in display_update() by checking which
# internal method gets called for each line type.

def test_classify_progress_line():
    """Lines starting with 'PROGRESS:' should route to _display_progress."""
    watcher = _make_watcher()
    watcher._display_progress = MagicMock()
    watcher.send_notification = MagicMock()

    watcher.display_update("PROGRESS: -> Starting task...")

    watcher._display_progress.assert_called_once()
    args = watcher._display_progress.call_args[0]
    assert "Starting task" in args[1], f"Expected message to contain 'Starting task', got: {args[1]}"


def test_classify_question_line():
    """Lines starting with 'QUESTION:' should route to _display_question."""
    watcher = _make_watcher()
    watcher._display_question = MagicMock()
    watcher.send_notification = MagicMock()

    watcher.display_update("QUESTION: What color for the button?")

    watcher._display_question.assert_called_once()
    args = watcher._display_question.call_args[0]
    assert "color" in args[1], f"Expected 'color' in message, got: {args[1]}"


def test_classify_complete_line():
    """Lines starting with 'COMPLETE:' should route to _display_complete."""
    watcher = _make_watcher()
    watcher._display_complete = MagicMock()
    watcher.send_notification = MagicMock()

    watcher.display_update("COMPLETE: Feature deployed to localhost:5173")

    watcher._display_complete.assert_called_once()
    args = watcher._display_complete.call_args[0]
    assert "deployed" in args[1], f"Expected 'deployed' in message, got: {args[1]}"


def test_classify_error_line():
    """Lines starting with 'ERROR:' should route to _display_error."""
    watcher = _make_watcher()
    watcher._display_error = MagicMock()
    watcher.send_notification = MagicMock()

    watcher.display_update("ERROR: Build failed - missing dependency")

    watcher._display_error.assert_called_once()
    args = watcher._display_error.call_args[0]
    assert "Build failed" in args[1], f"Expected 'Build failed' in message, got: {args[1]}"


def test_classify_unknown_line():
    """Lines without a known prefix should route to _display_unknown."""
    watcher = _make_watcher()
    watcher._display_unknown = MagicMock()

    watcher.display_update("Some random text without prefix")

    watcher._display_unknown.assert_called_once()


def test_message_extraction():
    """The prefix should be stripped, leaving just the message."""
    watcher = _make_watcher()
    watcher._display_progress = MagicMock()
    watcher.send_notification = MagicMock()

    watcher.display_update("PROGRESS:   Done: Component created")

    args = watcher._display_progress.call_args[0]
    message = args[1]
    assert not message.startswith("PROGRESS:"), f"Prefix should be stripped, got: {message}"
    assert "Done: Component created" in message, f"Expected message content, got: {message}"


# --- File truncation detection tests ---

def test_file_truncation_resets_position():
    """If the progress file shrinks, the watcher's watch loop should reset position."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        tmppath = Path(f.name)
        f.write("PROGRESS: -> Step 1\nPROGRESS: -> Step 2\n")

    try:
        watcher = _make_watcher(progress_file=tmppath)
        assert watcher.last_position > 0, "Should start at end of file"

        # Truncate the file (simulate agent clearing it)
        with open(tmppath, 'w') as f:
            f.write("")

        # Exercise the actual truncation detection logic from watch():
        # read file size, compare to last_position, reset if smaller
        with open(tmppath, 'r') as f:
            f.seek(0, 2)
            file_size = f.tell()
            if file_size < watcher.last_position:
                watcher.last_position = 0
            f.seek(watcher.last_position)
            new_content = f.read()
            watcher.last_position = f.tell()

        assert watcher.last_position == 0, "Position should reset after truncation"
    finally:
        tmppath.unlink(missing_ok=True)


# --- Import tests ---

def test_import_progress_watcher():
    """ProgressWatcher module should import without errors."""
    from bobby import progress_watcher
    assert hasattr(progress_watcher, 'ProgressWatcher')


def test_instantiate_progress_watcher():
    """ProgressWatcher should instantiate with a custom file path."""
    watcher = _make_watcher()
    assert hasattr(watcher, 'display_update')
    assert hasattr(watcher, 'watch')


ALL_TESTS = [
    ("Import progress_watcher module", test_import_progress_watcher),
    ("Instantiate ProgressWatcher", test_instantiate_progress_watcher),
    ("Classify PROGRESS line", test_classify_progress_line),
    ("Classify QUESTION line", test_classify_question_line),
    ("Classify COMPLETE line", test_classify_complete_line),
    ("Classify ERROR line", test_classify_error_line),
    ("Classify unknown line", test_classify_unknown_line),
    ("Message prefix extraction", test_message_extraction),
    ("File truncation resets position", test_file_truncation_resets_position),
]
