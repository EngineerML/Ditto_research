from __future__ import annotations

from ..guide_records import read

FINAL_CHECK_NOTE = "One last check before this reply is sent: read it through against the instructions at the start of this conversation and against the message, its last line first. Then write the reply the user will get - the same reply, word for word, if it already follows them, or the reply put right where it does not - ending with its 'ANSWER:' line."
FINAL_CHECK_MIN_SECONDS = 20.0
SPELLING_CHECK = "In the values the reply gives, write each ordinary word correctly spelled, even where a note misspells it, and change nothing else in them: names, codes, addresses and figures keep every character as written."


def final_check_note(message: str) -> str:
    return f"{FINAL_CHECK_NOTE} {SPELLING_CHECK}" if read(message).asks_next_step else FINAL_CHECK_NOTE
