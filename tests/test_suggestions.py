#!/usr/bin/env python3
"""
Automated tests for bobby.suggestions — the proactive suggestion engine.

Does NOT call any LLM — bobby.brain._run_llm is mocked. All time-based
gates are exercised by passing explicit `now` values (the engine never
reads the clock itself).
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bobby import suggestions
from bobby.suggestions import (
    ProactiveEngine,
    parse_suggestion,
    build_proactive_prompt,
    ANALYZE_INTERVAL_SECONDS,
    ACTIVITY_SUPPRESS_SECONDS,
    BUFFER_MAX_CHARS,
    MIN_NEW_CHARS,
)

# A discussion excerpt long enough to clear MIN_NEW_CHARS
DISCUSSION = (
    "[Max] I really think the settings page needs a dark mode toggle. "
    "[David] Yes, users keep asking for it, it should be a simple switch. "
    "[Max] Right, just a toggle in the header would do it for now. "
)

LLM_YES = (
    "SUGGEST: yes\n"
    "FEATURE: dark mode toggle\n"
    "PITCH: I hear you talk about dark mode — I can build this right now!"
)


def _ready_engine(**kwargs):
    """Engine with enough buffered text to pass the cheap gates."""
    engine = ProactiveEngine(**kwargs)
    engine.accumulate(DISCUSSION)
    assert len(DISCUSSION) >= MIN_NEW_CHARS, "test fixture too short"
    return engine


# --- Parsing tests (fail closed) ---

def test_parse_valid_yes():
    result = parse_suggestion(LLM_YES)
    assert result == {
        "feature": "dark mode toggle",
        "pitch": "I hear you talk about dark mode — I can build this right now!",
    }


def test_parse_no():
    assert parse_suggestion("SUGGEST: no") is None


def test_parse_malformed_returns_none():
    assert parse_suggestion("") is None
    assert parse_suggestion(None) is None
    assert parse_suggestion("Sure! I'd suggest a dark mode toggle.") is None
    assert parse_suggestion("SUGGEST: yes\nFEATURE: dark mode") is None  # no pitch
    assert parse_suggestion("SUGGEST: yes\nPITCH: something") is None    # no feature


def test_parse_strips_markdown_from_pitch():
    raw = "SUGGEST: yes\nFEATURE: contact form\nPITCH: I build the **contact form** now!"
    assert parse_suggestion(raw)["pitch"] == "I build the contact form now!"


def test_prompt_includes_excerpt_and_past_features():
    prompt = build_proactive_prompt("we discussed a footer", ["dark mode toggle"])
    assert "we discussed a footer" in prompt
    assert "dark mode toggle" in prompt
    prompt_no_past = build_proactive_prompt("we discussed a footer", [])
    assert "ALREADY offered" not in prompt_no_past


# --- Gate tests (try_begin) ---

def test_fresh_engine_with_enough_text_begins():
    engine = _ready_engine()
    excerpt = engine.try_begin(now=1000.0)
    assert excerpt is not None and "dark mode" in excerpt
    assert engine.analysis_in_flight is True
    assert engine.pending_text == ""  # buffer consumed


def test_too_little_text_does_not_begin():
    engine = ProactiveEngine()
    engine.accumulate("[Max] short remark")
    assert engine.try_begin(now=1000.0) is None
    assert engine.analysis_in_flight is False


def test_no_double_begin_while_in_flight():
    engine = _ready_engine()
    assert engine.try_begin(now=1000.0) is not None
    engine.accumulate(DISCUSSION)
    assert engine.try_begin(now=2000.0) is None  # in flight


def test_agent_running_blocks():
    engine = _ready_engine()
    assert engine.try_begin(now=1000.0, agent_running=True) is None


def test_recent_activity_blocks():
    engine = _ready_engine()
    engine.note_activity(now=1000.0)
    assert engine.try_begin(now=1000.0 + ACTIVITY_SUPPRESS_SECONDS - 1) is None
    assert engine.try_begin(now=1000.0 + ACTIVITY_SUPPRESS_SECONDS + 1) is not None


def test_analysis_interval_blocks():
    engine = _ready_engine()
    assert engine.try_begin(now=1000.0) is not None
    engine.analysis_in_flight = False  # simulate analysis done, no suggestion
    engine.accumulate(DISCUSSION)
    assert engine.try_begin(now=1000.0 + ANALYZE_INTERVAL_SECONDS - 1) is None
    assert engine.try_begin(now=1000.0 + ANALYZE_INTERVAL_SECONDS + 1) is not None


def test_cooldown_blocks_after_suggestion():
    engine = _ready_engine(cooldown_seconds=300)
    excerpt = engine.try_begin(now=1000.0)
    with patch("bobby.brain._run_llm", return_value=LLM_YES):
        assert engine.analyze(excerpt, now=1000.0) is not None

    engine.accumulate(DISCUSSION)
    late = 1000.0 + ANALYZE_INTERVAL_SECONDS + 1
    assert late - 1000.0 < 300, "fixture must land inside the cooldown"
    assert engine.try_begin(now=late) is None  # cooldown active
    assert engine.try_begin(now=1000.0 + 301) is not None  # cooldown over


def test_buffer_keeps_only_tail():
    engine = ProactiveEngine()
    engine.accumulate("OLD " * 2000)
    engine.accumulate("THE NEWEST PART")
    assert len(engine.pending_text) <= BUFFER_MAX_CHARS
    assert engine.pending_text.endswith("THE NEWEST PART")


# --- Analysis tests (mocked LLM) ---

def test_analyze_returns_voice_line():
    engine = _ready_engine()
    excerpt = engine.try_begin(now=1000.0)
    with patch("bobby.brain._run_llm", return_value=LLM_YES):
        suggestion = engine.analyze(excerpt, now=1000.0)

    assert suggestion["feature"] == "dark mode toggle"
    assert "I hear you talk about dark mode" in suggestion["voice_line"]
    assert "hey Bobby, please build this" in suggestion["voice_line"]
    assert engine.analysis_in_flight is False
    assert engine.last_suggestion_time == 1000.0


def test_analyze_no_suggestion_returns_none():
    engine = _ready_engine()
    excerpt = engine.try_begin(now=1000.0)
    with patch("bobby.brain._run_llm", return_value="SUGGEST: no"):
        assert engine.analyze(excerpt, now=1000.0) is None
    assert engine.analysis_in_flight is False
    assert engine.last_suggestion_time == 0.0  # no cooldown burned


def test_analyze_never_repeats_a_feature():
    engine = _ready_engine()
    excerpt = engine.try_begin(now=1000.0)
    with patch("bobby.brain._run_llm", return_value=LLM_YES):
        assert engine.analyze(excerpt, now=1000.0) is not None

    engine.accumulate(DISCUSSION)
    excerpt2 = engine.try_begin(now=5000.0)
    with patch("bobby.brain._run_llm", return_value=LLM_YES.replace(
            "dark mode toggle", "Dark  Mode toggle!")):
        assert engine.analyze(excerpt2, now=5000.0) is None, \
            "same feature (modulo case/punctuation) must not be offered twice"


def test_analyze_llm_error_fails_closed():
    engine = _ready_engine()
    excerpt = engine.try_begin(now=1000.0)
    with patch("bobby.brain._run_llm", side_effect=RuntimeError("boom")):
        assert engine.analyze(excerpt, now=1000.0) is None
    assert engine.analysis_in_flight is False


# --- Config tests ---

def test_proactive_disabled_by_default():
    """Without BOBBY_PROACTIVE, the feature must be off."""
    import importlib
    import os
    from bobby import config

    old = os.environ.pop("BOBBY_PROACTIVE", None)
    try:
        importlib.reload(config)
        assert config.PROACTIVE_ENABLED is False
        os.environ["BOBBY_PROACTIVE"] = "1"
        importlib.reload(config)
        assert config.PROACTIVE_ENABLED is True
    finally:
        if old is None:
            os.environ.pop("BOBBY_PROACTIVE", None)
        else:
            os.environ["BOBBY_PROACTIVE"] = old
        importlib.reload(config)


ALL_TESTS = [
    ("Parse: valid yes answer", test_parse_valid_yes),
    ("Parse: no answer", test_parse_no),
    ("Parse: malformed fails closed", test_parse_malformed_returns_none),
    ("Parse: markdown stripped from pitch", test_parse_strips_markdown_from_pitch),
    ("Prompt: includes excerpt and past features", test_prompt_includes_excerpt_and_past_features),
    ("Gate: fresh engine with text begins", test_fresh_engine_with_enough_text_begins),
    ("Gate: too little text blocks", test_too_little_text_does_not_begin),
    ("Gate: no double-begin while in flight", test_no_double_begin_while_in_flight),
    ("Gate: agent running blocks", test_agent_running_blocks),
    ("Gate: recent explicit trigger blocks", test_recent_activity_blocks),
    ("Gate: analysis interval enforced", test_analysis_interval_blocks),
    ("Gate: cooldown after a suggestion", test_cooldown_blocks_after_suggestion),
    ("Gate: buffer keeps only the tail", test_buffer_keeps_only_tail),
    ("Analyze: returns spoken voice line", test_analyze_returns_voice_line),
    ("Analyze: 'no' returns None, no cooldown", test_analyze_no_suggestion_returns_none),
    ("Analyze: never repeats a feature", test_analyze_never_repeats_a_feature),
    ("Analyze: LLM error fails closed", test_analyze_llm_error_fails_closed),
    ("Config: off by default, on with BOBBY_PROACTIVE=1", test_proactive_disabled_by_default),
]
