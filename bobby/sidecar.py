"""
Sidecar v2 transcript pipeline — event log + derived, amend-capable transcript.

Consumes AssemblyAI streaming v3 events (as plain dicts, i.e. model_dump() of
TurnEvent / SpeakerRevisionEvent / BeginEvent) and maintains two files:

  events.jsonl            append-only log of EVERY event (the source of truth;
                          one JSON record per event: {wall, type, data})
  meeting_transcript.txt  derived view, atomically rewritten on every change:
                          finalized lines, overlap-recovered lines, and a live
                          partial line ("⋯ …") that is always the last line.

Why this shape (measured on the 2026-08-04 call, see
docs/2026-08-05-sidecar-v2-design.md):
  - Partials stream by default; discarding them caused 60s monologue
    blackouts. The live partial line closes that gap to ~1-2s.
  - Speaker labels are ~99% right live, but a SpeakerRevisionEvent at session
    end relabels earlier turns — so the transcript must be re-renderable, not
    append-only.
  - Overlapped interjections usually appear in partials and are then erased
    by the final turn-commit; diffing last-partial vs final recovers them as
    "[X~]" lines.

Wake-word modes (orchestrator, Discord) never touch this module — they keep
streaming.should_write_turn semantics.
"""

import difflib
import json
import os
import re
from datetime import datetime


def _norm_words(words):
    """Normalized text list for diffing (lowercase, punctuation stripped)."""
    out = []
    for w in words:
        t = re.sub(r"[^a-z0-9']", "", w.lower())
        out.append(t)
    return out


def _word_speaker(word):
    """Per-word speaker, from a dict (event.model_dump()) or a live SDK Word."""
    if isinstance(word, dict):
        return word.get("speaker")
    return getattr(word, "speaker", None)


# --- Speaker-label helpers, shared with audio_capture's labeled wake-word mode
# (BOBBY_SPEAKER_LABELS=1). Module-level so that mode reuses this rendering
# instead of growing a second, drifting copy of it.

def resolve_speaker_names(base_names=None, names_file=None):
    """
    Label→name mapping merged from a base dict and an optional file.

    Re-read at every render so names can be assigned live mid-call: one
    "A=Max" per line in the file, which wins over the base dict.
    """
    names = dict(base_names or {})
    if names_file and os.path.exists(names_file):
        try:
            with open(names_file) as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        if k.strip() and v.strip():
                            names[k.strip()] = v.strip()
        except OSError:
            pass
    return names


def format_speaker_label(label, names, uncertain=False):
    """Render a label for the transcript: "[Max]", "[Max~]" if uncertain, "[?]" if unknown."""
    if not label:
        return "[?~]" if uncertain else "[?]"
    shown = names.get(label, label)
    return f"[{shown}~]" if uncertain else f"[{shown}]"


def turn_speaker_label(words, turn_label):
    """The turn's own speaker label, falling back to its last labeled word."""
    if turn_label:
        return turn_label
    labels = [s for s in (_word_speaker(w) for w in words) if s in ("A", "B", "C", "D")]
    return labels[-1] if labels else None


class SidecarWriter:
    """Feed it events; it keeps events.jsonl and the derived transcript current.

    All inputs are plain dicts so the same code path serves the live capture
    (event.model_dump()) and offline replay of a recorded events.jsonl —
    which is how the automated tests drive it, deterministically.
    """

    # A dropped word-run must be at least this long to become an overlap line…
    OVERLAP_MIN_RUN = 3
    # …or this long if it ends like a sentence (catches "Reactivity." only via
    # 2-word runs like "What? Reactivity." — a lone word is too noisy).
    OVERLAP_MIN_RUN_SENTENCE = 2

    def __init__(self, transcript_path, events_path, speaker_names=None,
                 speaker_names_file=None, now_fn=None):
        self.transcript_path = str(transcript_path)
        self.events_path = str(events_path)
        self.base_speaker_names = dict(speaker_names or {})
        self.speaker_names_file = str(speaker_names_file) if speaker_names_file else None
        self._now_fn = now_fn or datetime.now
        self._session = -1          # incremented on each Begin
        self._turns = {}            # (session, turn_order) -> turn dict
        self._order = []            # insertion order of keys
        self._partial = None        # (key, label, text, words) of in-flight turn
        self._pending_overlap = []  # overlap candidates awaiting next-final dedupe
        self._last_render = None
        self._bootstrap()

    def _bootstrap(self):
        """Rebuild state from an existing events.jsonl.

        The capture runs under a restart loop (AAI sessions die silently), so
        a fresh process must not render an empty transcript over the previous
        process's work. The event log is the source of truth — replay it.
        """
        if not os.path.exists(self.events_path):
            return
        self._in_bootstrap = True
        try:
            with open(self.events_path) as f:
                for line in f:
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue  # torn tail write from a killed process
                    self._dispatch(rec.get("type"), rec.get("data") or {},
                                   rec.get("wall") or "")
        except OSError:
            pass
        finally:
            self._in_bootstrap = False
        self._render()

    # ---------------------------------------------------------------- events

    def handle_event(self, kind, data, wall=None):
        """kind: "Begin"|"Turn"|"SpeakerRevision"|"Termination"|"Error".

        `wall` is an ISO or "HH:MM:SS" stamp for replay; live callers omit it.
        """
        stamp = wall or self._now_fn().isoformat(timespec="milliseconds")
        self._log_event(kind, data, stamp)
        self._dispatch(kind, data, stamp)

    def _dispatch(self, kind, data, stamp):
        if kind == "Begin":
            self._session += 1
            self._partial = None
        elif kind == "Turn":
            self._on_turn(data, self._hhmmss(stamp))
        elif kind == "SpeakerRevision":
            self._on_revision(data)
        elif kind == "Termination":
            # No further finals will arrive to settle pending overlap
            # candidates — promote the survivors now rather than losing them.
            for cand in self._pending_overlap:
                turn = self._turns.get(cand["after_key"])
                if turn is not None:
                    turn["overlaps"].append(cand)
            self._pending_overlap = []
            self._partial = None
            self._render()

    def _log_event(self, kind, data, stamp):
        rec = {"wall": stamp, "type": kind, "data": data}
        with open(self.events_path, "a") as f:
            f.write(json.dumps(rec, default=str) + "\n")

    @staticmethod
    def _hhmmss(stamp):
        m = re.search(r"(\d\d:\d\d:\d\d)", stamp)
        return m.group(1) if m else stamp[:8]

    # ----------------------------------------------------------------- turns

    def _on_turn(self, d, hhmmss):
        key = (self._session, d.get("turn_order", 0))
        text = (d.get("transcript") or "").strip()
        words = d.get("words") or []
        label = d.get("speaker_label")

        if not d.get("end_of_turn"):
            if text:
                self._partial = (key, self._partial_label(words, label), text, words)
                self._render()
            return

        # Finalized turn.
        prev_partial = self._partial if self._partial and self._partial[0] == key else None
        self._partial = None

        if text:
            if key not in self._turns:
                self._order.append(key)
            self._turns[key] = {
                "wall": hhmmss, "label": label, "text": text,
                "words": words, "overlaps": [],
            }

        # Dedupe pending overlap candidates: if the words resurfaced in this
        # final (turn re-segmentation, not a drop), discard the candidate.
        self._settle_pending(text)

        # New overlap candidates: word-runs present in the last partial of THIS
        # turn but absent from its final.
        if prev_partial and text:
            for run_words, run_label in self._dropped_runs(prev_partial[3], prev_partial[2], words, text):
                self._pending_overlap.append({
                    "after_key": key, "wall": hhmmss,
                    "label": run_label or label, "text": run_words,
                    "seen_finals": 0,
                })
        self._render()

    def _partial_label(self, words, turn_label):
        """See turn_speaker_label()."""
        return turn_speaker_label(words, turn_label)

    # ------------------------------------------------------- overlap recovery

    def _dropped_runs(self, p_words, p_text, f_words, f_text):
        """Yield (text, majority_label) for word-runs the final dropped."""
        p_tokens = _norm_words(p_text.split())
        f_tokens = _norm_words(f_text.split())
        p_raw = p_text.split()
        sm = difflib.SequenceMatcher(a=p_tokens, b=f_tokens, autojunk=False)
        for tag, i1, i2, _, _ in sm.get_opcodes():
            if tag != "delete":
                continue
            run_raw = p_raw[i1:i2]
            n = i2 - i1
            sentence_like = bool(run_raw) and run_raw[-1][-1:] in ".?!"
            if n >= self.OVERLAP_MIN_RUN or (n >= self.OVERLAP_MIN_RUN_SENTENCE and sentence_like):
                label = self._run_label(p_words, i1, i2)
                yield " ".join(run_raw), label

    @staticmethod
    def _run_label(p_words, i1, i2):
        """Majority per-word speaker over the dropped run, if word data exists."""
        labels = [
            w.get("speaker") for w in p_words[i1:i2]
            if isinstance(w, dict) and w.get("speaker") in ("A", "B", "C", "D")
        ]
        if not labels:
            return None
        return max(set(labels), key=labels.count)

    def _settle_pending(self, new_final_text):
        """Confirm or discard overlap candidates against the following finals."""
        new_norm = " ".join(_norm_words(new_final_text.split())) if new_final_text else ""
        kept = []
        for cand in self._pending_overlap:
            cand_norm = " ".join(_norm_words(cand["text"].split()))
            if cand_norm and cand_norm in new_norm:
                continue  # words resurfaced in a later final — not a drop
            cand["seen_finals"] += 1
            if cand["seen_finals"] >= 2:
                # Survived two subsequent finals: promote to the turn store.
                turn = self._turns.get(cand["after_key"])
                if turn is not None:
                    turn["overlaps"].append(cand)
                continue
            kept.append(cand)
        self._pending_overlap = kept

    # -------------------------------------------------------------- revision

    def _on_revision(self, d):
        for rev in d.get("revisions") or []:
            key = (self._session, rev.get("turn_order"))
            turn = self._turns.get(key)
            if turn is None:
                continue
            if rev.get("speaker_label") is not None:
                turn["label"] = rev["speaker_label"]
            if rev.get("words"):
                turn["words"] = rev["words"]
        self._render()

    # ---------------------------------------------------------------- render

    def _speaker_names(self):
        """See resolve_speaker_names()."""
        return resolve_speaker_names(self.base_speaker_names, self.speaker_names_file)

    def _fmt_label(self, label, names, uncertain=False):
        """See format_speaker_label()."""
        return format_speaker_label(label, names, uncertain)

    _in_bootstrap = False

    def _render(self):
        if self._in_bootstrap:
            return
        names = self._speaker_names()
        lines = []
        for key in self._order:
            t = self._turns[key]
            lines.append(f"[{t['wall']}] {self._fmt_label(t['label'], names)} {t['text']}")
            for ov in t["overlaps"]:
                lines.append(
                    f"[{ov['wall']}] {self._fmt_label(ov['label'], names, uncertain=True)} {ov['text']}"
                )
        if self._partial:
            _, label, text, _ = self._partial
            lines.append(f"⋯ {self._fmt_label(label, names)} {text}")
        out = "\n".join(lines) + ("\n" if lines else "")
        if out == self._last_render:
            return
        tmp = self.transcript_path + ".tmp"
        with open(tmp, "w") as f:
            f.write(out)
        os.replace(tmp, self.transcript_path)
        self._last_render = out
