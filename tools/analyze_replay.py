#!/usr/bin/env python3
"""Quick-look analysis of a tools/replay_stream.py JSONL event log: partial
cadence, speaker labels, revisions, and coverage of a searched phrase.

Usage: python tools/analyze_replay.py events.jsonl ["search phrase"]
(The deeper batch-ground-truth comparison used for the 2026-08-05 experiment is
snapshotted next to its artifacts in the meetings repo, `….replay/analysis-used-2026-08-05.py`.)"""
import json
import sys
from collections import Counter

path = sys.argv[1]
search = sys.argv[2].lower() if len(sys.argv) > 2 else None

events = [json.loads(l) for l in open(path)]
counts = Counter(e["type"] for e in events)
print("event counts:", dict(counts))

turns = [e for e in events if e["type"] == "Turn"]
finals = [e for e in turns if e["data"]["end_of_turn"]]
partials = [e for e in turns if not e["data"]["end_of_turn"]]
print(f"turns: {len(turns)} total, {len(finals)} final, {len(partials)} partial")

if partials:
    gaps = [round(b["elapsed"] - a["elapsed"], 2) for a, b in zip(turns, turns[1:])]
    print(f"inter-turn-event gaps (s): max={max(gaps)}, "
          f">5s: {sum(1 for g in gaps if g > 5)}, >10s: {sum(1 for g in gaps if g > 10)}")
    per_order = Counter(t["data"]["turn_order"] for t in partials)
    top = per_order.most_common(3)
    print(f"partials per turn_order (top): {top}")

labels = Counter(t["data"].get("speaker_label") for t in finals)
print("final-turn speaker labels:", dict(labels))
word_speakers = Counter(w.get("speaker") for t in finals for w in t["data"]["words"])
print("per-word speakers (finals):", dict(word_speakers))

for e in events:
    if e["type"] == "SpeakerRevision":
        revs = e["data"]["revisions"]
        print(f"SpeakerRevision at elapsed={e['elapsed']}: {len(revs)} turns revised: "
              f"{[(r['turn_order'], r['speaker_label']) for r in revs][:10]}")

if search:
    hits_f = [t for t in finals if search in t["data"]["transcript"].lower()]
    hits_p = [t for t in partials if search in t["data"]["transcript"].lower()]
    print(f"search '{search}': in finals: {len(hits_f)}, in partials-only: {len(hits_p)}")
    for t in (hits_f or hits_p)[:3]:
        d = t["data"]
        print(f"  turn {d['turn_order']} (final={d['end_of_turn']}, spk={d.get('speaker_label')}): "
              f"...{d['transcript'][:140]}")

print("\n--- final transcript (labeled) ---")
for t in finals:
    d = t["data"]
    print(f"[{t['elapsed']:7.1f}s] [{d.get('speaker_label')}] {d['transcript'][:160]}")
