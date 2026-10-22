from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx

from app.memory.tools import LOCAL_PROVENANCE, MemoryTools
from app.tooling.receipts import Authorize, BLOCKED, COMPLETED, DELIVERED_FAILED, DELIVERY_UNKNOWN, HOLD, NOT_DELIVERED, REPEAT_OUTCOMES, SEND, Receipt, call_identity
from app.protocol import MEMORY_TOOL_NAMES, ObservedToolCall, ToolExecRequest

log = logging.getLogger("harness.tools")
TOOL_OUTPUT_MAX_CHARS = 6000
ADMISSION_REFUSED_STATUS = 429
ENDPOINT_RETRY_PAUSE = 1.0
UNDELIVERED_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout, httpx.ProxyError, httpx.UnsupportedProtocol, httpx.LocalProtocolError)
DELIVERY_UNKNOWN_NOTE = "Tool error: {name} was sent; no result came back, so whether it ran is unknown."
REFUSED_NOTE = "Tool error: {name} was refused with status {status} and did not run."
ENDPOINT_FAILED_NOTE = "Tool error: {name} was sent and the endpoint answered {status} with no result, so whether it ran is unknown."
BUDGET_SPENT_NOTE = "Tool error: {name} was not sent because this request's time budget is spent, so it did not run."
MIN_TOOL_CALL_SECONDS = 2.0
JSON_HEADERS = {"Content-Type": "application/json"}
DECLINED_HELD_NOTE = "Not sent: an identical {name} call, with exactly these arguments, {outcome} earlier in this request, and the check made before sending found that the user's message does not ask for this exact call more times than it was already sent, so this one was held and nothing was sent."
UNANSWERED_HELD_NOTE = "Not sent: an identical {name} call, with exactly these arguments, {outcome} earlier in this request, and the check made before sending could not be completed, so this one was held and nothing was sent. If the user's message asks for this exact call more times than it was already sent, sending it again puts it to that check again."


def refused_before_execution(status: int) -> bool:
    return 400 <= status < 500


def model_authored_object(raw: str) -> bool:
    try:
        return isinstance(json.loads(raw), dict)
    except ValueError:
        return False


def exec_body(request: ToolExecRequest, raw_args: str) -> bytes:
    fields = request.model_dump(exclude_none=True)
    if not model_authored_object(raw_args):
        return json.dumps(fields).encode()
    members = [json.dumps(key) + ":" + json.dumps(value) for key, value in fields.items() if key != "args"]
    members.append('"args":' + raw_args)
    return ("{" + ",".join(members) + "}").encode()


class ToolExecutor:
    def __init__(self, endpoint: str | None, case_id: str, user_id: str | None, client: httpx.AsyncClient, timeout_seconds: float, deadline: float | None = None, memory: MemoryTools | None = None) -> None:
        self.endpoint = endpoint.strip() if endpoint else ""
        self.case_id = case_id
        self.user_id = user_id
        self._client = client
        self.timeout_seconds = timeout_seconds
        self.deadline = deadline
        self.memory = memory
        self.observed: list[ObservedToolCall] = []
        self.sent: dict[str, str] = {}
        self.next_hop = 0
        self.ledger: list[Receipt] = []

    def window(self) -> float:
        if self.deadline is None:
            return self.timeout_seconds
        return min(self.timeout_seconds, self.deadline - time.monotonic())

    async def execute(self, name: str, args: dict[str, Any], raw_args: str, authorize: Authorize) -> tuple[str, str]:
        key = call_identity(name, args)
        earlier = self.sent.get(key)
        if earlier == DELIVERY_UNKNOWN:
            note = "Not sent: the previous identical call has an unknown outcome and this endpoint supplies no idempotency contract."
            self.ledger.append(Receipt(name, args, BLOCKED, note))
            return note, BLOCKED
        if earlier is not None:
            verdict = await authorize(name, args, REPEAT_OUTCOMES[earlier], list(self.ledger))
            if verdict != SEND:
                note = (DECLINED_HELD_NOTE if verdict == HOLD else UNANSWERED_HELD_NOTE).format(name=name, outcome=REPEAT_OUTCOMES[earlier])
                self.ledger.append(Receipt(name, args, BLOCKED, note))
                log.info("case=%s identical call %s held before sending, authorization %s", self.case_id, name, verdict)
                return note, BLOCKED
        output, state = await self.send(name, args, raw_args)
        if state in REPEAT_OUTCOMES:
            self.sent[key] = state
        return output, state

    async def send(self, name: str, args: dict[str, Any], raw_args: str = "") -> tuple[str, str]:
        if self.memory is not None and self.memory.can_follow(name) and name != "save_memory":
            pair_id = args.get("pair_id")
            if not isinstance(pair_id, str) or not self.memory.store.pairs_by_ids(self.user_id, [pair_id]):
                note = "Not sent: this memory identifier is not available in the current user's store."
                self.ledger.append(Receipt(name, args, BLOCKED, note))
                return note, BLOCKED
        output, state = await self._deliver(name, args, raw_args)
        self.ledger.append(Receipt(name, args, state, output))
        if state == COMPLETED and self.memory is not None and self.memory.can_follow(name):
            try:
                followed = self.memory.follow(name, args)
            except Exception:
                log.exception("endpoint completed %s but local persistence failed", name)
                followed = False
            output = json.dumps({"endpoint_result": output, "local_memory": {"served_by": LOCAL_PROVENANCE, "state": COMPLETED if followed else "not_changed"}}, ensure_ascii=False)
        return output, state

    async def _deliver(self, name: str, args: dict[str, Any], raw_args: str) -> tuple[str, str]:
        if not self.endpoint:
            return f"Tool {name} is unavailable in this environment.", NOT_DELIVERED
        hop = self.next_hop
        self.next_hop += 1
        request = ToolExecRequest(case_id=self.case_id, user_id=self.user_id or None, name=name, args=args, hop=hop)
        body = exec_body(request, raw_args)
        response: httpx.Response | None = None
        for round_trip in range(2):
            timeout = self.window()
            if timeout < MIN_TOOL_CALL_SECONDS:
                if response is None:
                    log.warning("tool %s was not sent: %.1fs of the case budget remain", name, timeout)
                    return BUDGET_SPENT_NOTE.format(name=name), BLOCKED
                break
            try:
                response = await self._client.post(self.endpoint, content=body, headers=JSON_HEADERS, timeout=timeout)
            except UNDELIVERED_ERRORS as exc:
                log.warning("tool endpoint unreachable name=%s err=%s", name, exc)
                return f"Tool {name} failed: endpoint unreachable.", NOT_DELIVERED
            except httpx.TransportError as exc:
                log.warning("tool %s left this host without a result, recording the call with its outcome unknown err=%s", name, exc)
                return DELIVERY_UNKNOWN_NOTE.format(name=name), DELIVERY_UNKNOWN
            if response.status_code == ADMISSION_REFUSED_STATUS and round_trip == 0:
                log.info("tool endpoint refused %s with %d before serving it, waiting to retry", name, response.status_code)
                await asyncio.sleep(min(ENDPOINT_RETRY_PAUSE, max(0.0, self.window())))
                continue
            break
        if refused_before_execution(response.status_code):
            log.warning("tool %s was refused with status %d before it ran, not recording it as executed", name, response.status_code)
            return REFUSED_NOTE.format(name=name, status=response.status_code), DELIVERED_FAILED
        if response.status_code != 200:
            log.warning("tool %s crossed to the endpoint and came back %d without a result", name, response.status_code)
            return ENDPOINT_FAILED_NOTE.format(name=name, status=response.status_code), DELIVERY_UNKNOWN
        try:
            payload = response.json()
        except ValueError:
            return DELIVERY_UNKNOWN_NOTE.format(name=name), DELIVERY_UNKNOWN
        if not isinstance(payload, dict) or ("result" not in payload and "error" not in payload):
            return DELIVERY_UNKNOWN_NOTE.format(name=name), DELIVERY_UNKNOWN
        # Only acknowledged tool invocations enter the executed-call transcript.
        # Refused and uncertain deliveries remain in the outcome ledger instead.
        self.observed.append(ObservedToolCall(name=name, args=args, hop=hop))
        error = payload.get("error")
        result = payload.get("result")
        if isinstance(result, dict) and (result.get("error") or result.get("success") is False):
            return json.dumps(payload, ensure_ascii=False), DELIVERED_FAILED
        if error:
            text = f"Tool error: {error}"
            return text, DELIVERED_FAILED
        output = result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
        return output, COMPLETED
