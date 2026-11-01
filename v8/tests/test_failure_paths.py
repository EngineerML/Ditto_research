"""A model call whose connection is cut with an error httpx does not wrap is retried instead of ending the case."""
import asyncio
import time

import anyio
import httpx

from app.llm import OpenAICompatLLM

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
