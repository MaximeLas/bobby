# Launch doc — rehearsal & demo day (written 17 Aug 2026, ~22:00, post-merge)

_For the agent running the rehearsals and the David demo (18 Aug). The session that
wrote this ("Demo-week execution") merged the stack and built the pre-demo items in
one evening and ran deep — treat this as orientation and re-derive load-bearing facts
from the files. `docs/NEXT.md` is the playbook; `docs/modes.md` is the concept map;
this is the "what's next, in order" layer._

## State as of tonight

- **Everything is on `main`; no other branches exist, local or remote.** The PR stack
  (#1→#2→#3) merged 17 Aug evening. One catch, recorded in merge `52ec08f`: the
  4–17 Aug commits (all of sidecar v2) had never been pushed, so they reached main
  by a follow-up local merge — if history looks odd, that's why.
- **Offline suite: 112/112** (`uv run python3 tests/run_tests.py`), no keys needed.
- **Both live checks passed** (agent loop built + browser-verified a page; brain
  answered in 10s, in character), and **credentials verified live ~21:55** by
  `tools/preflight.py`: AAI token ✅, a real ElevenLabs generation ✅ (Borat voice),
  claude CLI ✅ — all green in 2.1s.
- Sandbox is the committed blank canvas. `tools/reset_sandbox.sh` returns it there
  after any run.
- Decisions locked (do not re-litigate): LOCAL mode, in person; brain on the
  `claude` CLI; `--dangerously-skip-permissions` stays for the demo (the auto-mode
  permission bridge is designed in NEXT.md, post-demo).

## The order of work

1. **Preflight** (before every session, 2s): `uv run python3 tools/preflight.py`.
2. **Solo sandbox rehearsal** — `./start_bobby.sh`, then the full voice loop:
   - "Hey Bobby, please build this" on a small feature → spoken ack → build →
     spoken COMPLETE. If it asks a QUESTION, answer aloud and close with
     "Thank you, Bobby."
   - Converse **between** builds: "Hey Bobby, what do you think of …" → spoken
     answer. ⚠️ **Not mid-build** — in local mode the watch loop blocks during a
     build (PR #3 documented limitation; fix is in NEXT.md). Bobby still speaks
     QUESTION/COMPLETE, so there is live feedback while he works.
   - ⚠️ Don't say a casual "thanks, Bobby" while a question is pending — resume
     grabs the preceding lines as the answer.
   - **Two rehearsal-gated flags to exercise** (details in NEXT.md runbook):
     `BOBBY_LEAN_AGENT` is already ON (watch launch latency drop; if any build
     misbehaves, `BOBBY_LEAN_AGENT=0` restores the old behavior) and
     `BOBBY_SPEAKER_LABELS=1 BOBBY_SPEAKER_NAMES="A=Max,B=David"` (try with two
     REAL voices — synthetic-audio testing showed labels never delay finals but
     can misattribute; decide from the rehearsal whether the demo keeps them).
   - `tools/reset_sandbox.sh` between takes.
3. **Publico worktree rehearsal** — exact commands in NEXT.md's demo runbook
   (worktree keeps publico main structurally untouchable; `BOBBY_DEV_URL=` port
   3000; local-mode launcher).
4. **Go live with David.** Back-pocket features (26 Jun call): hero page upgrade
   (safest), drafting-window source footnotes (David explicitly wants it —
   rehearse it first). Scope bar: small / visual / additive / self-contained.

## Side quests, if the day leaves room

- **Sidecar v2's first-ever live wire check** (command in NEXT.md "Current state" —
  it is a first run, not a rerun; all green sidecar results so far are offline).
- Consolidate `discord_bot._speak_in_voice`'s inline ElevenLabs unwrap onto
  `tts.elevenlabs_error_message` (noted during tonight's build; Discord surface, so
  post-demo is fine).

## Pointers

- `docs/NEXT.md` — current state, demo runbook with the rehearsal-gated flags, and
  the new design anchors (E2E two-tier tests, per-workspace Bobby config file +
  onboarding, permission bridge, proactive refinements).
- `docs/modes.md` — what Bobby's modes actually are (stance vs rig). Read before
  adding or renaming any "mode".
- Project memory `MEMORY.md` — the one-line-per-fact history, including tonight.

## Kickoff (paste into the fresh session)

```
Read docs/2026-08-17-rehearsal-launch.md and take ownership of Bobby's rehearsal-and-demo day. Start by running preflight with me, then drive the solo sandbox rehearsal (including the two rehearsal-gated flags), then the publico worktree rehearsal, and get us to the live demo with David.
```

## Self-epitaph

This session (17 Aug evening, "(17 Aug) Demo-week execution"): drove both live checks
green, merged the PR stack and caught the never-pushed sidecar commits, cleaned all
branches, committed the 5 Aug replay evidence in meetings/max-os (plus the sidecar
prompt supersession Max asked for on 4 Aug), built the six pre-demo items
(preflight, sandbox reset, tts unwrap, shrink guard, lean launches, speaker labels —
112/112), wrote modes.md from two independent brainstorms, and rewrote NEXT.md's
current state + backlog. Once this doc is read by the rehearsal session, this one is
archivable — nothing load-bearing lives only in its transcript.
