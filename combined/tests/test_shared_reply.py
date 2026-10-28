"""The same user asking the same question of the same notes again has the first answer shown as a note:
every request goes to the deciding model with its whole message, which may give that answer again or
replace it; when the first comes back without an answer, the others write their own from the draft."""
import asyncio
from types import SimpleNamespace

from app import short
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
    "Kitchen job kr-2207 again. When is the tiler coming now? Give the day and the time.",
]


def ask_all(monkeypatch, replies: list[str]) -> tuple[list[Outcome], list[str]]:
    path = ShortPath(SimpleNamespace(llm=None, tally=None), effort="medium", max_tokens=100, readings={}, order_max_tokens=100, drafts={}, replies={})
    shown: list[str] = []

    async def groups(req, records, token, deadline, outcome):
        return [[pair] for pair in records]

    async def shared_draft(req, key, messages, deadline, outcome):
        return None

    async def decide(engine, req, messages, effort, max_tokens, deadline, outcome):
        text = replies[len(shown)]
        shown.append(messages[-1]["content"])
        await asyncio.sleep(0.05)
        outcome.content = text
        return bool(text)

    path.groups = groups
    path.shared_draft = shared_draft
    monkeypatch.setattr(short, "decide", decide)

    async def run() -> list[Outcome]:
        outcomes = [Outcome() for _ in ASKED]
        loop = asyncio.get_running_loop()
        await asyncio.gather(*(path.answer(RunRequest(case_id=str(i), user_input=text, user_id="u"), NOTES, TOKEN, loop.time() + 600, outcome) for i, (text, outcome) in enumerate(zip(ASKED, outcomes))))
        return outcomes

    return asyncio.run(run()), shown


def test_a_later_request_sees_the_first_answer_and_decides(monkeypatch) -> None:
    outcomes, shown = ask_all(monkeypatch, ["ANSWER: Thursday", "ANSWER: Thursday", "Thursday at 8.\nANSWER: Thursday 8:00"])
    assert len(shown) == 3
    assert "ANSWER: Thursday" not in shown[0]
    for message, prompt in zip(shown[1:], ASKED[1:]):
        assert "A reply given earlier" in message and "ANSWER: Thursday" in message
        assert message.endswith(prompt)
    assert [o.content for o in outcomes] == ["ANSWER: Thursday", "ANSWER: Thursday", "Thursday at 8.\nANSWER: Thursday 8:00"]


def test_without_a_first_answer_each_writes_its_own(monkeypatch) -> None:
    outcomes, shown = ask_all(monkeypatch, ["", "ANSWER: Thursday", "ANSWER: Thursday"])
    assert len(shown) == 3
    assert not any("A reply given earlier" in message for message in shown)
    assert [o.content for o in outcomes[1:]] == ["ANSWER: Thursday"] * 2
