"""The same user asking the same question of the same notes again gets the first answer: the first
request writes it, the others ship it as it is; when the first comes back without an answer, the
others write their own."""
import asyncio
from types import SimpleNamespace

from app.action import Outcome
from app.protocol import MemoryPair, RunRequest
from app.short import ShortPath

TOKEN = "kr-2207"
NOTES = [
    MemoryPair(pair_id="a", timestamp="2025-01-01T09:00:00Z", prompt="Kitchen job kr-2207: the tiler is booked for Monday"),
    MemoryPair(pair_id="b", timestamp="2025-01-02T09:00:00Z", prompt="Kitchen job kr-2207: the tiler moved to Thursday"),
]
ASKED = [
    "About kitchen job kr-2207. When is the tiler coming now? Just the day.",
    "Quick check on kitchen job kr-2207. When is the tiler coming now? One word is fine.",
    "Kitchen job kr-2207 again. When is the tiler coming now? Thanks.",
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
    outcomes = [Outcome() for _ in ASKED]
    loop = asyncio.get_running_loop()
    await asyncio.gather(*(path.answer(RunRequest(case_id=str(i), user_input=text, user_id="u"), NOTES, TOKEN, loop.time() + 600, outcome) for i, (text, outcome) in enumerate(zip(ASKED, outcomes))))
    return outcomes


def test_the_same_question_gets_the_first_answer() -> None:
    path, asked = short_path([(True, "ANSWER: Thursday"), (True, "ANSWER: Monday"), (True, "ANSWER: Monday")])
    outcomes = asyncio.run(ask_all(path))
    assert len(asked) == 1
    assert [o.content for o in outcomes] == ["ANSWER: Thursday"] * 3


def test_without_a_first_answer_each_writes_its_own() -> None:
    path, asked = short_path([(False, ""), (True, "ANSWER: Thursday"), (True, "ANSWER: Thursday")])
    outcomes = asyncio.run(ask_all(path))
    assert len(asked) == 3
    assert [o.content for o in outcomes[1:]] == ["ANSWER: Thursday"] * 2
