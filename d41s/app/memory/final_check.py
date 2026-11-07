from __future__ import annotations

from ..guide_records import read
from .retrieval import identifier_tokens

FINAL_CHECK_NOTE = "One last check before this reply is sent: read it through against the instructions at the start of this conversation and against the message, its last line first. Then write the reply the user will get - the same reply, word for word, if it already follows them, or the reply put right where it does not."
FINAL_CHECK_MIN_SECONDS = 20.0
SPELLING_CHECK = "In the values the reply gives, write each ordinary word correctly spelled, even where a note misspells it, and change nothing else in them: names, codes, addresses and figures keep every character as written."
AGREE_CHECK = "Where the message asks whether the notes agree on where it stands, keep the last line to three parts, the state one of the two latest notes gives, the state the other gives, and the word disagree, not the state of every note, even where the message asks for each record or all of them."
TASK_CHECK = "Keep all three parts of the last line, the person ; the task ; the channel, and in the task part leave out the channel and any time or condition the note adds after it, such as 'by phone', 'before Friday' or 'once it is signed'. The step on the last line is the one set by the latest passage about the work that gives someone a next action: within one note a later passage replaces an earlier one, even where the earlier one uses the message's own words, such as open action or next step."
HOLDER_CHECK = "Where the message asks who holds it now, the person on the last line is the one the latest note that hands or passes it to a person, or says a person picked it up or took it on, puts in charge of it; a company, vendor or supplier the work moved to is never the holder, even where a note says it took the work over, and nor is someone a later note only gives the ball, a task or the next step, or a status."
LESSON_CHECK = "Where the message asks what the user took from it, whatever it calls that, the last line holds the saying the user wrote down as the lesson of it, in their words: not a step, a status, a person or a remark about which note to read first; where a note holds such a saying, give it rather than saying there is none."
STATUS_CHECK = "Where the message asks what state it is in, the last line holds only the state the latest note about where it stands gives it, in that note's words for the state, each spelled correctly: not the person or company it sits with, a place, a task someone still owes or waits on, a reference, or a word from the message. The state is the word or words that say where it stands, which may be a short word such as set or done; give them in full, on hold rather than hold. Where that note adds a remark after the state, such as what it still waits on, what is left over or how sure or glad the user is, the remark neither changes nor takes back the state: the state is still the word or words before it, and no word of the remark is the state. A state word the note misspells is written as the English word it is a slip for."


def final_check_note(message: str) -> str:
    if read(message).asks_disagreement:
        return f"{FINAL_CHECK_NOTE} {AGREE_CHECK}"
    if read(message).asks_next_step:
        return f"{FINAL_CHECK_NOTE} {SPELLING_CHECK}" if identifier_tokens(message) else f"{FINAL_CHECK_NOTE} {SPELLING_CHECK} {TASK_CHECK}"
    if identifier_tokens(message):
        return FINAL_CHECK_NOTE
    if read(message).asks_lesson:
        return f"{FINAL_CHECK_NOTE} {LESSON_CHECK}"
    if read(message).asks_status:
        return f"{FINAL_CHECK_NOTE} {STATUS_CHECK}"
    if read(message).asks_holder:
        return f"{FINAL_CHECK_NOTE} {HOLDER_CHECK}"
    return FINAL_CHECK_NOTE
