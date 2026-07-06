"""
Shared streaming-transcription helpers used by both capture modes
(local: audio_capture.py, Discord: discord_sink.py).
"""


def should_write_turn(event, seen_turn_orders):
    """
    Decide whether an AssemblyAI TurnEvent should be written to the
    transcript, recording it in seen_turn_orders when the answer is yes.

    We act only on FINALIZED turns, never partial/interim ones — partial
    transcripts are untrustworthy and could fire a trigger mid-word.

    Turn emission differs by model. Older streaming models sent each
    finalized turn twice (unformatted, then formatted, same turn_order);
    Universal-3.5 Pro formats inline and may not set turn_is_formatted at
    all, so gating on that flag would drop every turn. Gating on end_of_turn
    and deduping by turn_order writes each turn exactly once under both
    emission patterns. Trigger detection normalizes punctuation
    (agent_runner.normalize_text), so formatted vs unformatted text matches
    identically.

    Args:
        event: TurnEvent from assemblyai.streaming.v3
        seen_turn_orders: per-session set of turn_order values already
            written; mutated in place. Reset it whenever a new streaming
            session begins (turn_order restarts from 0).

    Returns:
        bool: True if the caller should write event.transcript
    """
    if not event.end_of_turn:
        return False  # Skip partial/interim transcripts

    if not (event.transcript and event.transcript.strip()):
        return False  # Skip empty finalized turns (e.g. trailing silence)

    if event.turn_order in seen_turn_orders:
        return False  # Already written (e.g. an unformatted->formatted pair)

    seen_turn_orders.add(event.turn_order)
    return True
