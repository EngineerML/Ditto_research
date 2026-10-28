from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import httpx

from .lane import reads_state
from .protocol import LOCAL_PAIR_PREFIX, MEMORY_TOOL_NAMES, ObservedToolCall, ToolDefinition, ToolExecRequest, handed_out
from .store import Store

log = logging.getLogger("harness.tools")
SEARCH_TEXT_CHARS = 700
LOCAL_PROVENANCE = "read locally from this harness's own memory store for this user, not returned by the tool endpoint"
TOOL_OUTPUT_MAX_CHARS = 6000
TRANSIENT_RE = re.compile(r"transient|temporar|try again|\bretry\b|timed? ?out|\b50[234]\b", re.IGNORECASE)
RETRY_HINT = " This failure is transient: issue the same call once more, unchanged."
ADMISSION_REFUSED_STATUS = 429
ENDPOINT_RETRY_PAUSE = 1.0
UNDELIVERED_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout, httpx.ProxyError, httpx.UnsupportedProtocol, httpx.LocalProtocolError)
DELIVERY_UNKNOWN_NOTE = "Tool error: {name} was sent; no result came back, so whether it ran is unknown."
REFUSED_NOTE = "Tool error: {name} was refused with status {status} and did not run."
ENDPOINT_FAILED_NOTE = "Tool error: {name} was sent and the endpoint answered {status} with no result, so whether it ran is unknown."
BUDGET_SPENT_NOTE = "Tool error: {name} was not sent because this request's time budget is spent, so it did not run."
MIN_TOOL_CALL_SECONDS = 2.0
JSON_HEADERS = {"Content-Type": "application/json"}
COMPLETED = "completed"
DELIVERY_UNKNOWN = "delivery_unknown"
DELIVERED_FAILED = "delivered_failed"
NOT_DELIVERED = "not_delivered"
BLOCKED = "blocked_before_execution"
SEND = "SEND"
HOLD = "HOLD"
# After a memory write went through, the reply should tell the user what was kept, not just "Got it".
MEMORY_WRITES = frozenset({"save_memory", "update_memory"})
KEPT_NOTE = "\n\n[Kept. Your reply tells the user in one short sentence of your own what you kept and its value; do not repeat their message back.]"
REPEAT_OUTCOMES = {COMPLETED: "already ran (its result is above)", DELIVERY_UNKNOWN: "was already sent and no result came back (whether it ran is unknown)"}
HELD_REPEAT_NOTE = "Not sent: an identical {name} call, with exactly these arguments, {outcome} earlier in this request, and the check made before sending found that the user's message does not ask for this exact call more times than it was already sent, so this one was held and nothing was sent."
UNANSWERED_HELD_NOTE = "Not sent: an identical {name} call, with exactly these arguments, {outcome} earlier in this request, and the check made before sending could not be completed, so this one was held and nothing was sent. If the user's message asks for this exact call more times than it was already sent, sending it again puts it to that check again."
SAVED_PAIR_ID = LOCAL_PAIR_PREFIX + "{digest}"
SAVED_AT = "%Y-%m-%dT%H:%M:%SZ"
UNHELD_IDS_NOTE = "Call not sent: {name} names {ids}, and no stored conversation or subject of this user has that identifier. Identifiers are the pair_id and subject id values printed with the records or returned by a search; the mark a record is shown with, such as M4, is not one. Send it again with those identifiers, or search by words."
EMPTY_INPUT_NOTE = "Tool error: {name} was called with an empty {field}, so this harness read no stored conversation for it. Send it again with {field} filled in."


@dataclass(frozen=True)
class Receipt:
    name: str
    args: dict[str, Any]
    state: str
    output: str


Authorize = Callable[[str, dict[str, Any], str, list[Receipt]], Awaitable[str | None]]


def refused_before_execution(status: int) -> bool:
    return 400 <= status < 500


def call_identity(name: str, args: dict[str, Any]) -> str:
    return name + json.dumps(args, sort_keys=True, ensure_ascii=False)


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


def openai_tools(defs: list[ToolDefinition]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in defs:
        parameters = d.parameters if isinstance(d.parameters, dict) and d.parameters else {"type": "object", "properties": {}}
        out.append({"type": "function", "function": {"name": d.name, "description": d.description or d.name, "parameters": parameters}})
    return out


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
        self.read_after: dict[str, int] = {}
        self.changes = 0
        self.ledger: list[Receipt] = []

    def window(self) -> float:
        if self.deadline is None:
            return self.timeout_seconds
        return min(self.timeout_seconds, self.deadline - time.monotonic())

    async def execute(self, name: str, args: dict[str, Any], raw_args: str, authorize: Authorize) -> tuple[str, str]:
        key = call_identity(name, args)
        earlier = self.sent.get(key)
        if earlier is not None and reads_state(name) and self.read_after[key] != self.changes:
            earlier = None
        if earlier is not None:
            verdict = await authorize(name, args, REPEAT_OUTCOMES[earlier], list(self.ledger))
            if verdict != SEND:
                note = (HELD_REPEAT_NOTE if verdict == HOLD else UNANSWERED_HELD_NOTE).format(name=name, outcome=REPEAT_OUTCOMES[earlier])
                self.ledger.append(Receipt(name, args, BLOCKED, note))
                log.info("case=%s identical call %s held before sending, authorization %s", self.case_id, name, verdict)
                return note, BLOCKED
        output, state = await self.send(name, args, raw_args)
        if reads_state(name):
            if state == COMPLETED:
                self.sent[key] = state
                self.read_after[key] = self.changes
        elif state in REPEAT_OUTCOMES:
            self.sent[key] = state
        return output, state

    async def send(self, name: str, args: dict[str, Any], raw_args: str = "") -> tuple[str, str]:
        output, state = await self._deliver(name, args, raw_args)
        self.ledger.append(Receipt(name, args, state, output))
        if state in REPEAT_OUTCOMES and not reads_state(name):
            self.changes += 1
        if state == COMPLETED and self.memory is not None and self.memory.follow(name, args):
            log.info("tool %s completed at the endpoint and this user's own store now follows it", name)
        return output, state

    async def _deliver(self, name: str, args: dict[str, Any], raw_args: str) -> tuple[str, str]:
        if not self.endpoint:
            return f"Tool {name} is unavailable in this environment.", NOT_DELIVERED
        hop = len(self.observed)
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
                self.observed.append(ObservedToolCall(name=name, args=args, hop=hop))
                return DELIVERY_UNKNOWN_NOTE.format(name=name), DELIVERY_UNKNOWN
            if response.status_code == ADMISSION_REFUSED_STATUS and round_trip == 0:
                log.info("tool endpoint refused %s with %d before serving it, waiting to retry", name, response.status_code)
                await asyncio.sleep(min(ENDPOINT_RETRY_PAUSE, max(0.0, self.window())))
                continue
            break
        if refused_before_execution(response.status_code):
            log.warning("tool %s was refused with status %d before it ran, not recording it as executed", name, response.status_code)
            return REFUSED_NOTE.format(name=name, status=response.status_code), DELIVERED_FAILED
        self.observed.append(ObservedToolCall(name=name, args=args, hop=hop))
        if response.status_code != 200:
            log.warning("tool %s crossed to the endpoint and came back %d without a result", name, response.status_code)
            return ENDPOINT_FAILED_NOTE.format(name=name, status=response.status_code), DELIVERY_UNKNOWN
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        error = payload.get("error")
        result = payload.get("result")
        if error:
            text = f"Tool error: {error}"
            return (text + RETRY_HINT if reads_state(name) and TRANSIENT_RE.search(text) else text), DELIVERED_FAILED
        output = str(result if result is not None else "")
        if len(output) > TOOL_OUTPUT_MAX_CHARS:
            log.warning("tool %s output truncated from %d chars", name, len(output))
            output = output[:TOOL_OUTPUT_MAX_CHARS] + " …[truncated]"
        return output, COMPLETED


def shown_entry(pair_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    return {"pair_id": pair_id, **fields} if handed_out(pair_id) else fields


def _snippet(text: str, limit: int = 220) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


class MemoryTools:
    def __init__(self, store: Store, user_id: str | None) -> None:
        self.store = store
        self.user_id = user_id

    def handles(self, name: str) -> bool:
        return name in MEMORY_TOOL_NAMES

    def hits(self, name: str, args: dict[str, Any]) -> list[str]:
        if name == "search_memories":
            return [hit.pair.pair_id for query in self._queries(args.get("queries") or args.get("query") or "") for hit in self.store.search(self.user_id, query, limit=8)]
        if name == "fetch_memories":
            raw = args.get("pairIds") or args.get("pair_ids") or []
            return [p.pair_id for p in self.store.pairs_by_ids(self.user_id, [str(i) for i in raw] if isinstance(raw, list) else [str(raw)])]
        if name == "search_memories_in_subjects":
            return [p.pair_id for p in self.store.subject_pairs(self.user_id, str(args.get("subject_id") or ""))]
        return []

    def unheld_ids(self, name: str, args: dict[str, Any]) -> list[str]:
        if name == "fetch_memories":
            raw = args.get("pairIds") if "pairIds" in args else args.get("pair_ids")
            ids = [str(i) for i in raw] if isinstance(raw, list) else [] if raw is None else [str(raw)]
            held = {p.pair_id for p in self.store.pairs_by_ids(self.user_id, ids) if handed_out(p.pair_id)}
            return [i for i in ids if i not in held]
        if name == "search_memories_in_subjects":
            subject_id = str(args.get("subject_id") if args.get("subject_id") is not None else "")
            return [] if self.store.holds_subject(self.user_id, subject_id) else [subject_id]
        if isinstance(args.get("pair_id"), str) and args["pair_id"].strip():
            pair_id = args["pair_id"]
            return [] if any(handed_out(p.pair_id) for p in self.store.pairs_by_ids(self.user_id, [pair_id])) else [pair_id]
        return []

    def run(self, name: str, args: dict[str, Any]) -> str:
        if name == "search_memories":
            return self._search(args.get("queries") or args.get("query") or "")
        if name == "search_subjects":
            return self._subjects(args.get("queries") or args.get("query") or "")
        if name == "fetch_memories":
            return self._fetch(args.get("pairIds") or args.get("pair_ids") or [])
        if name == "search_memories_in_subjects":
            return self._in_subject(args.get("subject_id") or "", args.get("queries") or args.get("query") or "")
        return f"Tool error: unknown memory tool {name}"

    def follow(self, name: str, args: dict[str, Any]) -> bool:
        pair_id = args.get("pair_id")
        content = args.get("content")
        if not isinstance(content, str) or not content.strip():
            return False
        if name == "save_memory":
            return self.store.save_pair(self.user_id, SAVED_PAIR_ID.format(digest=hashlib.sha256(content.encode()).hexdigest()[:16]), content, time.strftime(SAVED_AT, time.gmtime()))
        if name != "update_memory" or not isinstance(pair_id, str):
            return False
        return self.store.rewrite_pair(self.user_id, pair_id, content)

    @staticmethod
    def _queries(raw: Any) -> list[str]:
        if isinstance(raw, str):
            return [raw] if raw.strip() else []
        if isinstance(raw, list):
            return [str(q) for q in raw if str(q).strip()]
        return []

    def _search(self, raw: Any) -> str:
        if not self._queries(raw):
            return EMPTY_INPUT_NOTE.format(name="search_memories", field="queries")
        seen: dict[str, dict[str, Any]] = {}
        for query in self._queries(raw):
            for hit in self.store.search(self.user_id, query, limit=8):
                if hit.pair.pair_id not in seen:
                    seen[hit.pair.pair_id] = shown_entry(hit.pair.pair_id, {"timestamp": hit.pair.timestamp, "session_id": hit.pair.session_id, "text": _snippet(hit.pair.prompt + " || " + hit.pair.response, SEARCH_TEXT_CHARS)})
        if not seen:
            return json.dumps({"memories": [], "served_by": LOCAL_PROVENANCE, "note": "no stored conversation matches these queries. An empty result is an answer about the user's own history."})
        return json.dumps({"memories": list(seen.values())[:12], "served_by": LOCAL_PROVENANCE, "note": "each entry's pair_id is that stored record's own identifier: pass it to fetch_memories for the full text, and when one of these notes is itself the thing to be changed or removed, take the identifier from the entry whose text is that note"}, ensure_ascii=False)

    def _subjects(self, raw: Any) -> str:
        if not self._queries(raw):
            return EMPTY_INPUT_NOTE.format(name="search_subjects", field="queries")
        found: dict[str, dict[str, Any]] = {}
        for query in self._queries(raw):
            for subject in self.store.subjects_search(self.user_id, query, limit=8):
                found[subject.id] = {"id": subject.id, "name": subject.subject_text, "description": subject.description_text}
        return json.dumps({"subjects": list(found.values()), "served_by": LOCAL_PROVENANCE}, ensure_ascii=False)

    def _fetch(self, raw: Any) -> str:
        ids = [str(i) for i in raw] if isinstance(raw, list) else [str(raw)]
        if not any(i.strip() for i in ids):
            return EMPTY_INPUT_NOTE.format(name="fetch_memories", field="pairIds")
        pairs = self.store.pairs_by_ids(self.user_id, ids)
        return json.dumps({"memories": [shown_entry(p.pair_id, {"timestamp": p.timestamp, "session_id": p.session_id, "prompt": p.prompt, "response": p.response}) for p in pairs], "served_by": LOCAL_PROVENANCE}, ensure_ascii=False)

    def _in_subject(self, subject_id: str, raw: Any) -> str:
        if not str(subject_id).strip():
            return EMPTY_INPUT_NOTE.format(name="search_memories_in_subjects", field="subject_id")
        pairs = self.store.subject_pairs(self.user_id, str(subject_id))
        queries = [q.lower() for q in self._queries(raw)]
        if queries:
            pairs = [p for p in pairs if any(q in (p.prompt + " " + p.response).lower() for q in queries)] or pairs
        return json.dumps({"memories": [{"pair_id": p.pair_id, "timestamp": p.timestamp, "summary": _snippet(p.prompt + " || " + p.response)} for p in pairs[:16]], "served_by": LOCAL_PROVENANCE}, ensure_ascii=False)
