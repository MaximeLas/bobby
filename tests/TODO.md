# Test Suite — Remaining Work

Findings from two independent code review agents (March 2026). Everything
below is valid but was deferred because each item is a meaningful chunk of
work and the current 35-test suite already covers the core logic well.

## Priority 1: Missing component coverage

### audio_capture has zero automated tests
The `write_transcript` function in `bobby/audio_capture.py` has two testable
filter mechanisms that prevent real failure modes:
1. **Pause flag check** — skips transcription when `PAUSE_FLAG_FILE` exists
   (prevents Bobby from hearing himself)
2. **Bobby speech filter** — compares incoming text against
   `BOBBY_SPEECH_FILE` to filter out Bobby's own words

The `on_turn` event handler also has filtering logic (`end_of_turn`,
`turn_is_formatted`) that's testable with a mock event object.

**Why deferred:** The module imports `pyaudio` and `assemblyai` at the top
level, making it hard to import in tests without those dependencies
configured. Would need either lazy imports in the module or import mocking
in tests.

### tts.py has zero automated tests
The `speak()` function's structure (ElevenLabs → temp file → afplay, with
fallback to macOS `say`) could be verified with mocks.

**Why deferred:** `tts.py` creates an ElevenLabs client at import time
(`load_dotenv()` + `ElevenLabs(api_key=...)` on lines 14-17). Importing
the module has side effects and requires a valid `.env`. Would need
restructuring the module to defer client creation.

## Priority 2: Logic coverage gaps

### speak_bob pause flag lifecycle
The orchestrator's `speak_bob` creates `PAUSE_FLAG_FILE`, calls TTS, then
removes the flag. A bug here means Bobby transcribes his own voice. Testable
by mocking `bobby.tts.speak` and asserting the flag exists during the call
and is removed after.

### Normalization tests verify a copy, not the production code
The `_normalize()` helper in `test_orchestrator.py` replicates the inline
normalization logic from `watch_transcript()`. If someone changes the
production code but not the test helper, tests still pass. Fix: extract the
normalization into a standalone function in `orchestrator.py` and import it
in tests.

### extract_answer edge case
What happens with `extract_answer("")`? Empty string input is untested.

## Priority 3: Infrastructure improvements

### Consider migrating to pytest
The custom `ALL_TESTS` runner works but has limitations:
- No single-test execution (`-k` filter)
- No test isolation (shared module state)
- No fixtures or setup/teardown
- No assertion introspection (custom messages only)

Natural next step as the suite grows. Would require adding `pytest` to
dev dependencies in `pyproject.toml`.

### ProgressWatcher signal handler side effects
The constructor registers `signal.SIGINT`, so every `_make_watcher()` call
in tests overwrites the global signal handler. Not causing issues now but
would break if the test runner adds its own Ctrl+C handling.

### Shell demos hardcode paths
`demo_orchestrator.sh` and `demo_progress_watcher.sh` hardcode
`sandbox/meeting_transcript.txt` etc. because bash can't import Python
config. If someone changes filenames in `bobby/config.py`, the demos
silently break. Comments were added explaining this, but there's no
automated guard.
