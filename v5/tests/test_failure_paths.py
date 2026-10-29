"""Failures that used to end a case or move it off its path: a model call whose connection is cut with an
error httpx does not wrap is retried, and a program request whose order reading fails keeps its notes in
filing order on the program path."""
import asyncio
import time
from types import SimpleNamespace

import anyio
import httpx

from app.action import Outcome
from app.llm import OpenAICompatLLM
from app.protocol import MemoryPair, RunRequest
from app.short import ShortPath

TOKEN = "kr-2207"
NOTES = [
    MemoryPair(pair_id="b", timestamp="2025-01-02T09:00:00Z", prompt="Kitchen job kr-2207: the tiler moved to Thursday"),
    MemoryPair(pair_id="a", timestamp="2025-01-01T09:00:00Z", prompt="Kitchen job kr-2207: the tiler is booked for Monday"),
]
COMPLETION = {"choices": [{"message": {"role": "assistant", "content": "ANSWER: Thursday"}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 5, "completion_tokens": 3}}


def test_a_connection_cut_during_the_handshake_is_retried() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            raise anyio.ClosedResourceError()
        return httpx.Response(200, json=COMPLETION)

    async def run() -> str:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        llm = OpenAICompatLLM("http://relay.test", "ticket", "openai/gpt-oss-20b", timeout_seconds=30, max_attempts=3, client=client)
        result = await llm.chat([{"role": "user", "content": "When is the tiler coming?"}], None, deadline=time.monotonic() + 60)
        await client.aclose()
        return result.content

    assert asyncio.run(run()) == "ANSWER: Thursday"
    assert len(calls) == 2


def test_without_an_order_reading_the_notes_keep_filing_order() -> None:
    path = ShortPath(SimpleNamespace(llm=None, tally=None), effort="medium", max_tokens=100, readings={}, order_max_tokens=100, drafts={}, replies={})

    async def no_reading(req, messages, deadline, outcome):
        return None

    path.read_order = no_reading
    outcome = Outcome()
    groups = asyncio.run(path.groups(RunRequest(case_id="1", user_input="When is the tiler coming now?", user_id="u"), NOTES, TOKEN, time.monotonic() + 600, outcome))
    assert [group[0].pair_id for group in groups] == ["a", "b"]
    assert "order pass: no reading; notes in filing order" in outcome.events
