from __future__ import annotations

import asyncio
import hashlib
import json
import time

from ..action import Outcome
from ..packet import THREAD_MIN_RECORDS
from ..protocol import MemoryPair, RunRequest, normalize_user_id
from .finder import fold, record_parts
from .retrieval import identifier_tokens

ENTRY_PARTS_CAP = 400
REPLIES_HELD = 256
REPLY_WAITS = 2
REPLY_WAIT_RESERVE = 150.0

EarlierReply = tuple[str, str]


def filing_label(
    message: str, pairs: list[MemoryPair]
) -> tuple[str, list[MemoryPair]]:
    for token in identifier_tokens(message):
        carrying = [
            pair
            for pair in pairs
            if token in (pair.prompt + ' ' + pair.response).lower()
        ]
        if len(carrying) >= THREAD_MIN_RECORDS:
            return token, carrying
    return '', []


def entry_identifiers(
    message: str, pairs: list[MemoryPair], label: str
) -> frozenset[str] | None:
    parts = [
        set(identifier_tokens(fold(part.text))) - {label}
        for index, pair in enumerate(pairs)
        for part in record_parts(str(index), pair.prompt, pair.response)
    ]
    known = set(identifier_tokens(message)) - {label}
    if not known:
        return None
    taken: set[int] = set()
    grew = True
    while grew:
        grew = False
        for index, named in enumerate(parts):
            if index in taken or not named & known:
                continue
            taken.add(index)
            if len(taken) > ENTRY_PARTS_CAP:
                return None
            known |= named
            grew = True
    return frozenset(known)


def entries_key(
    user_id: str | None, operator: str, message: str, pairs: list[MemoryPair]
) -> str:
    label, filed = filing_label(message, pairs)
    if not label:
        return ''
    entries = entry_identifiers(message, filed, label)
    if entries is None:
        return ''
    asked = ' '.join(fold(message).replace(label, ' ').split())
    return hashlib.sha256(
        json.dumps(
            [normalize_user_id(user_id), operator, asked, sorted(entries)]
        ).encode()
    ).hexdigest()


class SameEntries:
    def __init__(
        self,
        held: dict[str, asyncio.Future[EarlierReply | None]],
        req: RunRequest,
        pairs: list[MemoryPair],
    ) -> None:
        self.held = held
        self.message = req.user_input
        self.key = entries_key(
            req.user_id, req.system_prompt, req.user_input, pairs
        )
        self.writing: asyncio.Future[EarlierReply | None] | None = None

    async def earlier(
        self, deadline: float, events: list[str]
    ) -> EarlierReply | None:
        if not self.key:
            return None
        for _ in range(REPLY_WAITS):
            future = self.held.get(self.key)
            if future is None:
                self.writing = self.hold()
                events.append(
                    f'same entries {self.key[:8]}: this reply, for later requests over the same entries'
                )
                return None
            try:
                reply = await asyncio.wait_for(
                    asyncio.shield(future),
                    max(
                        0.01, deadline - time.monotonic() - REPLY_WAIT_RESERVE
                    ),
                )
            except TimeoutError:
                events.append(
                    f'same entries {self.key[:8]}: the earlier reply over the same entries is not ready in time'
                )
                return None
            if reply is not None:
                events.append(
                    f'same entries {self.key[:8]}: an earlier reply over the same entries'
                )
                return reply
            if self.held.get(self.key) is future:
                del self.held[self.key]
        events.append(f'same entries {self.key[:8]}: no earlier reply')
        return None

    def hold(self) -> asyncio.Future[EarlierReply | None]:
        future: asyncio.Future[EarlierReply | None] = (
            asyncio.get_running_loop().create_future()
        )
        self.held[self.key] = future
        while len(self.held) > REPLIES_HELD:
            del self.held[next(iter(self.held))]
        return future

    def publish(self, outcome: Outcome) -> None:
        if self.writing is None or self.writing.done():
            return
        reply = (
            (self.message, outcome.content.strip())
            if outcome.answer and outcome.content.strip()
            else None
        )
        if reply is None and self.held.get(self.key) is self.writing:
            del self.held[self.key]
        self.writing.set_result(reply)
