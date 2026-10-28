"""Rewordings of one question over the same notes get one reply: the first writes it, the rest ship it
as it is; when the first comes back without a reply, the others write their own."""
import asyncio
from types import SimpleNamespace

from app.action import Outcome
from app.protocol import MemoryPair, RunRequest
from app.short import ShortPath

NOTES = [
    MemoryPair(pair_id="a", timestamp="2025-01-01T09:00:00Z", prompt="Case file c0123456789abcdef: the plan is booked"),
    MemoryPair(pair_id="b", timestamp="2025-01-02T09:00:00Z", prompt="Case file c0123456789abcdef: the plan is postponed"),
]
REWORDINGS = [
    "Use only case file c0123456789abcdef. Apply the schema first. What is the status of the plan now? One word.",
    "Use only case file c0123456789abcdef. Read the glossary first. What is the status of the plan now? Plain English.",
    "Use only case file c0123456789abcdef. Quick one. What is the status of the plan now? Just the status.",
]


def short_path(replies: list[tuple[bool, str]]) -> tuple[ShortPath, list[str]]:
    path = ShortPath(SimpleNamespace(llm=None, tally=None), effort="medium", max_tokens=100, readings={}, order_max_tokens=100, drafts={}, replies={})
    asked: list[str] = []

    async def groups(req, records, token, deadline, outcome):
        return [[pair] for pair in records]

    async def own_reply(req, key, system, shown, question, records, groups, deadline, outcome):
        handled, text = replies[len(asked)]
        asked.append(req.user_input)
        await asyncio.sleep(0.05)
        outcome.content = text
        outcome.answer = text or None
        return handled

    path.groups = groups
    path.own_reply = own_reply
    return path, asked


async def ask_all(path: ShortPath) -> list[Outcome]:
    outcomes = [Outcome() for _ in REWORDINGS]
    loop = asyncio.get_running_loop()
    await asyncio.gather(*(path.answer(RunRequest(case_id=str(i), user_input=text, user_id="u"), NOTES, "c0123456789abcdef", loop.time() + 600, outcome) for i, (text, outcome) in enumerate(zip(REWORDINGS, outcomes))))
    return outcomes


def test_rewordings_share_the_first_reply() -> None:
    path, asked = short_path([(True, "ANSWER: postponed"), (True, "ANSWER: booked"), (True, "ANSWER: booked")])
    outcomes = asyncio.run(ask_all(path))
    assert len(asked) == 1
    assert [o.content for o in outcomes] == ["ANSWER: postponed"] * 3
    assert all(o.answer == "ANSWER: postponed" for o in outcomes)


def test_without_a_first_reply_each_writes_its_own() -> None:
    path, asked = short_path([(False, ""), (True, "ANSWER: postponed"), (True, "ANSWER: postponed")])
    outcomes = asyncio.run(ask_all(path))
    assert len(asked) == 3
    assert [o.content for o in outcomes[1:]] == ["ANSWER: postponed"] * 2
