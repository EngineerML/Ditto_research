"""A turn cut off before it wrote anything is asked again at the same effort with more room, and
later turns and reply drafts keep the configured effort."""
import asyncio
import time

from app.action import LENGTH_RETRY_MAX_TOKENS, ActionEngine
from app.llm import ChatResult
from app.packet import Packet
from app.protocol import RunRequest, ToolDefinition


class FakeLLM:
    """Replies empty with finish=length once, then with a short reply that makes no call."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def chat(self, messages, tools, *, deadline, max_tokens, reasoning_effort=None, temperature=None, seed=None, once=False):
        self.calls.append({"max_tokens": max_tokens, "effort": reasoning_effort, "temperature": temperature})
        if len(self.calls) == 1:
            return ChatResult(content="", finish_reason="length", completion_tokens=max_tokens)
        return ChatResult(content="Which do you prefer for your reasoning effort: quick or deep?", finish_reason="stop")


class Tally:
    def add(self, _):
        pass


class Executor:
    ledger: list = []


class Memory:
    def handles(self, name: str) -> bool:
        return False


def test_length_retry_keeps_effort() -> None:
    llm = FakeLLM()
    engine = ActionEngine(llm, Executor(), Memory(), Tally(), max_turns=6, max_tokens=6000, effort="medium")
    tool = ToolDefinition(name="set_reasoning_effort", description="Set how deeply to think.", parameters={"type": "object", "properties": {"effort": {"type": "string"}}})
    req = RunRequest(case_id="c1", user_input="Sort out your reasoning depth for me.", tools=[tool])
    asyncio.run(engine.run(req, Packet(), time.monotonic() + 300))
    first, retry, *rest = llm.calls
    assert first == {"max_tokens": 6000, "effort": "medium", "temperature": None}
    assert retry["effort"] == "medium" and retry["max_tokens"] == LENGTH_RETRY_MAX_TOKENS
    assert all(call["effort"] == "medium" and call["max_tokens"] == 6000 for call in rest), rest
