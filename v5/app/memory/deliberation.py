from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

from ..action import Outcome, TokenTally
from ..llm import ChatResult, LLMError
from ..tools import BLOCKED

log = logging.getLogger("harness.deliberation")

NO_RECORD_REPLY = "say plainly that you have no record of it, and say which records you did check by naming who or what each one is about — not by its label, and without repeating its contents or figures"
DELIBERATION_BRIEF = """Before you reply, here are {count} drafts of a reply to the message above, each written separately from the same records. They have not been checked, and any of them may be wrong.

{drafts}

Now write the reply the user will get. Where drafts disagree, or a record says otherwise, the records decide. If none of the records states what was asked, """ + NO_RECORD_REPLY + """. A value that a later record withdraws (the user asked you to remove it or stop giving it out, or the record says it was retired or closed) is no longer held: do not give it or repeat it anywhere in the reply, and say only that you no longer have it on record. Do the checking before you reply, not in the reply. When you do answer, answer each thing the message asks, even where the message names the form one of them takes, and state no other value than the ones you answer with. You may keep a refusal or say you are unsure, you may set aside anything a draft suggests, and you may call a tool or reply without calling anything, as the message needs. Write to the user, not about the drafts."""
DRAFT_TEXT = "Draft {index}:\n{text}"
DRAFT_WITHOUT_TEXT = "Draft {index}: came back without text."
DRAFT_FAILED = "Draft {index}: no reply (the request failed)."
DRAFT_CUT = "Draft {index}: cut off at the length limit."
DRAFT_TOOL_CHOICE = "none"
DELIBERATION_MIN_SECONDS = 60.0
DRAFT_BUDGET_SHARE = 0.5


def reply_shape(result: ChatResult) -> str:
    if result.tool_calls:
        return "call " + ", ".join(f"{call.name}{json.dumps(call.args, ensure_ascii=False)[:120]}" for call in result.tool_calls)
    if result.finish_reason == "length":
        return "length"
    return "text" if result.content.strip() else "empty"


def draft_slot(index: int, reply: ChatResult) -> str:
    if reply.finish_reason == "length":
        return DRAFT_CUT.format(index=index)
    if not reply.content.strip():
        return DRAFT_WITHOUT_TEXT.format(index=index)
    return DRAFT_TEXT.format(index=index, text=reply.content.strip())


@dataclass(frozen=True)
class Deliberation:
    drafts: int
    temperature: float
    seed: int

    def skip_reason(self, records: int, seconds_left: float, turns_left: int, names_identifier: bool, statement: bool, names_value: bool) -> str:
        if reason := self.shape_skip(records, names_identifier, statement, names_value):
            return reason
        if seconds_left < DELIBERATION_MIN_SECONDS:
            return f"{int(seconds_left)} s left"
        if turns_left < 1:
            return "no turn left"
        return ""

    def shape_skip(self, records: int, names_identifier: bool, statement: bool, names_value: bool) -> str:
        if records < 1:
            return "no records to check against"
        if names_identifier:
            return "the message names an identifier its records carry"
        if statement:
            return "the message states something and asks nothing"
        if not names_value:
            return "the message names no value its records hold, and no full name, address, code or quoted words"
        return ""

    def draft_seed(self, index: int) -> int:
        return self.seed + index - 1

    def indexes(self) -> range:
        return range(2, self.drafts + 1)

    def draft_deadline(self, deadline: float) -> float:
        now = time.monotonic()
        return now + DRAFT_BUDGET_SHARE * (deadline - now)

    def brief(self, opening: ChatResult, replies: list[ChatResult | BaseException], tally: TokenTally, outcome: Outcome, case_id: str) -> str:
        outcome.events.append(f"deliberation: {len(replies) + 1} drafts")
        slots = [draft_slot(1, opening)]
        cancelled: list[BaseException] = []
        for index, reply in zip(self.indexes(), replies):
            if isinstance(reply, LLMError):
                tally.add(reply.usage)
                outcome.events.append(f"draft {index} failed: {reply}")
                slots.append(DRAFT_FAILED.format(index=index))
                continue
            if isinstance(reply, Exception):
                log.error("case=%s lane=records draft=%d failed", case_id, index, exc_info=reply)
                outcome.events.append(f"draft {index} failed: {reply!r}")
                slots.append(DRAFT_FAILED.format(index=index))
                continue
            if isinstance(reply, BaseException):
                cancelled.append(reply)
                continue
            tally.add(reply)
            outcome.model_calls += 1
            log.info("case=%s lane=records draft=%d finish=%s out=%d shape=%s", case_id, index, reply.finish_reason, reply.completion_tokens, reply_shape(reply))
            outcome.events.append(f"draft {index}: {'length' if reply.finish_reason == 'length' else 'text' if reply.content.strip() else 'empty'}")
            outcome.events.extend(f"{BLOCKED} {call.name}: returned by draft {index}, which is asked for text only; not run" for call in reply.tool_calls)
            slots.append(draft_slot(index, reply))
        if cancelled:
            raise cancelled[0]
        return DELIBERATION_BRIEF.format(count=len(slots), drafts="\n\n".join(slots))
