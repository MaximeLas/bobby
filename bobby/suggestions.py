#!/usr/bin/env python3
"""
Bobby Proactive Suggestions — offer to build things without being asked.

When BOBBY_PROACTIVE=1, Bobby watches the conversation for concrete,
small, buildable feature ideas and speaks up: "Excuse me, my friends! I
hear you talk about the dark mode toggle — I can build this for you right
now! Just say, hey Bobby, please build this."

Butting into a live meeting is high-risk, so the engine is gate-heavy and
fails closed at every step:

- OFF unless BOBBY_PROACTIVE=1 (callers check config.PROACTIVE_ENABLED)
- never while an agent is building
- never within ACTIVITY_SUPPRESS_SECONDS of an explicit trigger (someone
  is already engaging Bobby — don't pile on)
- at most one LLM analysis per ANALYZE_INTERVAL_SECONDS, and only once
  MIN_NEW_CHARS of fresh discussion accumulated
- at most one OFFER per PROACTIVE_COOLDOWN_SECONDS (default 5 min)
- never the same feature twice in a meeting
- any malformed LLM output or error -> no suggestion, silently

The engine is mode-agnostic and does no I/O of its own: Discord's
transcript watcher and the local orchestrator feed it text and speak the
returned line. Timestamps are passed in (`now`) so all gates are testable
without patching the clock.

The LLM call rides bobby.brain._run_llm, so it gets the fast API path and
the CLI fallback for free.
"""

import re

from bobby.config import PROACTIVE_COOLDOWN_SECONDS
from bobby.prompts import (
    PROACTIVE_PROMPT_TEMPLATE,
    PROACTIVE_PAST_FEATURES_TEMPLATE,
    VOICE_SUGGESTION_TEMPLATE,
)

# Gate tuning. Cooldown comes from config (env-overridable); these are
# implementation constants — change here if rehearsal says so.
ANALYZE_INTERVAL_SECONDS = 45   # min seconds between LLM analyses
MIN_NEW_CHARS = 120             # don't analyze conversational scraps
BUFFER_MAX_CHARS = 4000         # keep only the freshest discussion
ACTIVITY_SUPPRESS_SECONDS = 60  # quiet period after any explicit trigger


def build_proactive_prompt(excerpt, past_features):
    """Build the analysis prompt from a discussion excerpt."""
    past_section = (
        PROACTIVE_PAST_FEATURES_TEMPLATE.format(
            features="\n".join(f"- {f}" for f in past_features)
        )
        if past_features
        else ""
    )
    return PROACTIVE_PROMPT_TEMPLATE.format(
        excerpt=excerpt, past_features_section=past_section
    )


def parse_suggestion(raw):
    """
    Parse the strict three-line LLM answer into {"feature", "pitch"}.

    Fails closed: anything other than a well-formed "SUGGEST: yes" with a
    non-empty feature and pitch returns None.
    """
    if not raw:
        return None

    fields = {}
    for line in raw.strip().splitlines():
        match = re.match(r"^(SUGGEST|FEATURE|PITCH):\s*(.*)$", line.strip())
        if match:
            fields[match.group(1)] = match.group(2).strip()

    if fields.get("SUGGEST", "").lower() != "yes":
        return None

    feature = fields.get("FEATURE", "")
    pitch = fields.get("PITCH", "")
    if not feature or not pitch:
        return None

    # Belt-and-suspenders: the pitch is spoken aloud
    from bobby.brain import strip_for_speech
    return {"feature": feature, "pitch": strip_for_speech(pitch)}


def _normalize_feature(feature):
    """Lowercased alphanumeric words, for repeat detection."""
    return " ".join(re.findall(r"[a-z0-9]+", feature.lower()))


class ProactiveEngine:
    """
    Accumulates transcript text and decides when to run an LLM analysis.

    Usage (both modes):
        engine.note_activity(now)              # on every explicit trigger
        engine.accumulate(text)                # on trigger-free transcript
        excerpt = engine.try_begin(now, agent_running)
        if excerpt:                            # gates passed, claim taken
            # run in a thread/task — analyze() blocks on the LLM
            suggestion = engine.analyze(excerpt, now)
            if suggestion:
                speak(suggestion["voice_line"])
    """

    def __init__(self, cooldown_seconds=None):
        self.cooldown_seconds = (
            PROACTIVE_COOLDOWN_SECONDS if cooldown_seconds is None else cooldown_seconds
        )
        self.pending_text = ""
        self.last_analysis_time = 0.0
        self.last_suggestion_time = 0.0
        self.last_activity_time = 0.0
        self.past_features = []
        self.analysis_in_flight = False

    def accumulate(self, text):
        """Buffer trigger-free transcript text, keeping only the tail."""
        if not text:
            return
        self.pending_text += text
        if len(self.pending_text) > BUFFER_MAX_CHARS:
            self.pending_text = self.pending_text[-BUFFER_MAX_CHARS:]

    def note_activity(self, now):
        """Someone engaged Bobby explicitly — stay quiet for a while."""
        self.last_activity_time = now

    def try_begin(self, now, agent_running=False):
        """
        Run every cheap gate. If analysis is due, claim it (sets
        analysis_in_flight, consumes the buffer) and return the excerpt
        to analyze; otherwise return None.
        """
        if self.analysis_in_flight:
            return None
        if agent_running:
            return None
        if now - self.last_activity_time < ACTIVITY_SUPPRESS_SECONDS and self.last_activity_time > 0:
            return None
        if now - self.last_suggestion_time < self.cooldown_seconds and self.last_suggestion_time > 0:
            return None
        if now - self.last_analysis_time < ANALYZE_INTERVAL_SECONDS and self.last_analysis_time > 0:
            return None

        excerpt = self.pending_text.strip()
        if len(excerpt) < MIN_NEW_CHARS:
            return None

        self.analysis_in_flight = True
        self.pending_text = ""
        self.last_analysis_time = now
        return excerpt

    def analyze(self, excerpt, now):
        """
        Blocking LLM analysis of an excerpt returned by try_begin().

        Returns {"feature", "pitch", "voice_line"} when Bobby should speak
        up, else None. Never raises — a broken suggestion pipeline must
        never take down a transcript watcher.
        """
        try:
            from bobby.brain import _run_llm

            prompt = build_proactive_prompt(excerpt, self.past_features)
            suggestion = parse_suggestion(_run_llm(prompt))
            if suggestion is None:
                return None

            normalized = _normalize_feature(suggestion["feature"])
            if any(_normalize_feature(f) == normalized for f in self.past_features):
                return None

            self.past_features.append(suggestion["feature"])
            self.last_suggestion_time = now
            suggestion["voice_line"] = VOICE_SUGGESTION_TEMPLATE.format(
                pitch=suggestion["pitch"]
            )
            return suggestion
        except Exception as e:
            print(f"Proactive analysis failed (staying quiet): {e}")
            return None
        finally:
            self.analysis_in_flight = False
