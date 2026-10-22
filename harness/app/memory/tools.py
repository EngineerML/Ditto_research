"""Tenant-scoped memory reads and persistence after acknowledged mutations."""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any
from app.memory.store import Store
from app.protocol import LOCAL_PAIR_PREFIX, MEMORY_TOOL_NAMES, ToolDefinition, handed_out


SEARCH_TEXT_CHARS = 700
LOCAL_PROVENANCE = "read locally from this harness's own memory store for this user, not returned by the tool endpoint"
SAVED_PAIR_ID = LOCAL_PAIR_PREFIX + "{digest}"
SAVED_AT = "%Y-%m-%dT%H:%M:%SZ"
UNHELD_IDS_NOTE = "Call not sent: {name} names {ids}, and no stored conversation or subject of this user has that identifier. Identifiers are the pair_id and subject id values printed with the records or returned by a search; the mark a record is shown with, such as M4, is not one. Send it again with those identifiers, or search by words."
EMPTY_INPUT_NOTE = "Tool error: {name} was called with an empty {field}, so this harness read no stored conversation for it. Send it again with {field} filled in."


def shown_entry(pair_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    return {"pair_id": pair_id, **fields} if handed_out(pair_id) else fields


def _snippet(text: str, limit: int = 220) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rstrip() + "…"


class MemoryTools:
    def __init__(self, store: Store, user_id: str | None, catalog: list[ToolDefinition] | None = None) -> None:
        self.store = store
        self.user_id = user_id
        signatures = {"save_memory": {"content"}, "update_memory": {"pair_id", "content"}, "delete_memory": {"pair_id"}}
        self.mutations = set(signatures) if catalog is None else set()
        for tool in catalog or []:
            fields = signatures.get(tool.name)
            schema = tool.parameters or {}
            if fields and set(schema.get("required") or []) == fields and all(
                (schema.get("properties") or {}).get(field, {}).get("type") == "string" for field in fields
            ):
                self.mutations.add(tool.name)

    def can_follow(self, name: str) -> bool:
        return name in self.mutations

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
        if name == "delete_memory":
            return isinstance(pair_id, str) and self.store.delete_pair(self.user_id, pair_id)
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
