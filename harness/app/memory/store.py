from __future__ import annotations

import re
import sqlite3
import threading
from array import array
from dataclasses import dataclass

from app.protocol import MemoryPair, Subject, SubjectLink, normalize_user_id

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
CREATE TABLE IF NOT EXISTS pairs (
    user_id TEXT NOT NULL,
    pair_id TEXT NOT NULL,
    session_id TEXT NOT NULL DEFAULT '',
    ts TEXT NOT NULL DEFAULT '',
    prompt TEXT NOT NULL DEFAULT '',
    response TEXT NOT NULL DEFAULT '',
    seq INTEGER NOT NULL,
    PRIMARY KEY (user_id, pair_id)
);
CREATE INDEX IF NOT EXISTS pairs_session ON pairs(user_id, session_id, seq);
CREATE INDEX IF NOT EXISTS pairs_ts ON pairs(user_id, ts, seq);
CREATE VIRTUAL TABLE IF NOT EXISTS pairs_fts USING fts5(
    prompt, response, content='pairs', content_rowid='rowid', tokenize='unicode61'
);
CREATE TRIGGER IF NOT EXISTS pairs_ai AFTER INSERT ON pairs BEGIN
    INSERT INTO pairs_fts(rowid, prompt, response) VALUES (new.rowid, new.prompt, new.response);
END;
CREATE TRIGGER IF NOT EXISTS pairs_ad AFTER DELETE ON pairs BEGIN
    INSERT INTO pairs_fts(pairs_fts, rowid, prompt, response) VALUES ('delete', old.rowid, old.prompt, old.response);
END;
CREATE TABLE IF NOT EXISTS subjects (
    user_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    subject_text TEXT NOT NULL DEFAULT '',
    description_text TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (user_id, subject_id)
);
CREATE TABLE IF NOT EXISTS links (
    user_id TEXT NOT NULL,
    subject_id TEXT NOT NULL,
    pair_id TEXT NOT NULL,
    PRIMARY KEY (user_id, subject_id, pair_id)
);
CREATE TABLE IF NOT EXISTS counters (name TEXT PRIMARY KEY, value INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS vectors (user_id TEXT NOT NULL, h TEXT NOT NULL, v BLOB NOT NULL, PRIMARY KEY (user_id, h));
INSERT OR IGNORE INTO counters(name, value) VALUES ('seq', 0);
"""

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
CODE_RE = re.compile(r"\b(?:(?=[A-Za-z0-9-]*\d)(?=[A-Za-z0-9-]*[A-Za-z])[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+|[A-Z]{2,6}-[A-Z0-9]{4,}(?:-[A-Z0-9]+)*)\b")
WORD_RE = re.compile(r"[A-Za-z0-9]+")


def fts_query(text: str, limit_terms: int = 24) -> str:
    words = [w.lower() for w in WORD_RE.findall(text) if len(w) >= 2]
    seen: list[str] = []
    for word in words:
        if word not in seen:
            seen.append(word)
    if not seen:
        return ""
    return " OR ".join(f'"{w}"' for w in seen[:limit_terms])


@dataclass(frozen=True)
class SearchHit:
    pair: MemoryPair
    score: float


class Store:
    def __init__(self, path: str) -> None:
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.executescript(SCHEMA)
        self._versions: dict[str, int] = {}
        self._vectors: dict[tuple[str, str], array] = {}

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def version(self, user_id: str | None) -> int:
        return self._versions.get(normalize_user_id(user_id), 0)

    def _next_seq(self) -> int:
        row = self._conn.execute("UPDATE counters SET value = value + 1 WHERE name = 'seq' RETURNING value").fetchone()
        return int(row[0])

    def upsert_seed(self, user_id: str | None, pairs: list[MemoryPair], subjects: list[Subject], links: list[SubjectLink]) -> tuple[int, int, int]:
        uid = normalize_user_id(user_id)
        self._versions[uid] = self._versions.get(uid, 0) + 1
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                for pair in pairs:
                    existing = self._conn.execute(
                        "SELECT seq FROM pairs WHERE user_id = ? AND pair_id = ?", (uid, pair.pair_id)
                    ).fetchone()
                    seq = int(existing[0]) if existing else self._next_seq()
                    if existing:
                        self._conn.execute("DELETE FROM pairs WHERE user_id = ? AND pair_id = ?", (uid, pair.pair_id))
                    self._conn.execute(
                        "INSERT INTO pairs(user_id, pair_id, session_id, ts, prompt, response, seq) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (uid, pair.pair_id, pair.session_id, pair.timestamp, pair.prompt, pair.response, seq),
                    )
                for subject in subjects:
                    self._conn.execute(
                        "INSERT OR REPLACE INTO subjects(user_id, subject_id, subject_text, description_text) VALUES (?, ?, ?, ?)",
                        (uid, subject.id, subject.subject_text, subject.description_text),
                    )
                for link in links:
                    self._conn.execute(
                        "INSERT OR IGNORE INTO links(user_id, subject_id, pair_id) VALUES (?, ?, ?)",
                        (uid, link.subject_id, link.pair_id),
                    )
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
        return len(pairs), len(subjects), len(links)

    def rewrite_pair(self, user_id: str | None, pair_id: str, text: str) -> bool:
        uid = normalize_user_id(user_id)
        with self._lock:
            row = self._conn.execute("SELECT session_id, ts, seq FROM pairs WHERE user_id = ? AND pair_id = ?", (uid, pair_id)).fetchone()
            if row is None:
                return False
            self._conn.execute("BEGIN")
            try:
                self._conn.execute("DELETE FROM pairs WHERE user_id = ? AND pair_id = ?", (uid, pair_id))
                self._conn.execute(
                    "INSERT INTO pairs(user_id, pair_id, session_id, ts, prompt, response, seq) VALUES (?, ?, ?, ?, ?, '', ?)",
                    (uid, pair_id, row["session_id"], row["ts"], text, row["seq"]),
                )
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
            self._versions[uid] = self._versions.get(uid, 0) + 1
        return True

    def save_pair(self, user_id: str | None, pair_id: str, text: str, timestamp: str) -> bool:
        uid = normalize_user_id(user_id)
        with self._lock:
            if self._conn.execute("SELECT 1 FROM pairs WHERE user_id = ? AND pair_id = ?", (uid, pair_id)).fetchone() is not None:
                return False
            self._conn.execute("BEGIN")
            try:
                self._conn.execute(
                    "INSERT INTO pairs(user_id, pair_id, session_id, ts, prompt, response, seq) VALUES (?, ?, '', ?, ?, '', ?)",
                    (uid, pair_id, timestamp, text, self._next_seq()),
                )
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
            self._versions[uid] = self._versions.get(uid, 0) + 1
        return True

    def delete_pair(self, user_id: str | None, pair_id: str) -> bool:
        uid = normalize_user_id(user_id)
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                self._conn.execute("DELETE FROM links WHERE user_id = ? AND pair_id = ?", (uid, pair_id))
                deleted = self._conn.execute("DELETE FROM pairs WHERE user_id = ? AND pair_id = ?", (uid, pair_id)).rowcount
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
            if deleted:
                self._versions[uid] = self._versions.get(uid, 0) + 1
            return bool(deleted)

    def vectors(self, user_id: str | None, keys: list[str]) -> dict[str, array]:
        uid = normalize_user_id(user_id)
        out: dict[str, array] = {}
        with self._lock:
            for key in keys:
                vector = self._vectors.get((uid, key))
                if vector is None:
                    row = self._conn.execute("SELECT v FROM vectors WHERE user_id = ? AND h = ?", (uid, key)).fetchone()
                    if row is None:
                        continue
                    vector = array("f")
                    vector.frombytes(row[0])
                    self._vectors[(uid, key)] = vector
                out[key] = vector
        return out

    def put_vectors(self, user_id: str | None, vectors: dict[str, array]) -> None:
        if not vectors:
            return
        uid = normalize_user_id(user_id)
        with self._lock:
            self._conn.execute("BEGIN")
            try:
                self._conn.executemany("INSERT OR REPLACE INTO vectors(user_id, h, v) VALUES (?, ?, ?)", [(uid, key, vector.tobytes()) for key, vector in vectors.items()])
                self._conn.execute("COMMIT")
            except Exception:
                self._conn.execute("ROLLBACK")
                raise
            self._vectors.update({(uid, key): vector for key, vector in vectors.items()})

    @staticmethod
    def _row_pair(row: sqlite3.Row) -> MemoryPair:
        return MemoryPair(
            pair_id=row["pair_id"], session_id=row["session_id"], timestamp=row["ts"],
            prompt=row["prompt"], response=row["response"],
        )

    def pairs_by_ids(self, user_id: str | None, pair_ids: list[str]) -> list[MemoryPair]:
        uid = normalize_user_id(user_id)
        out: list[MemoryPair] = []
        with self._lock:
            for pair_id in pair_ids:
                row = self._conn.execute("SELECT * FROM pairs WHERE user_id = ? AND pair_id = ?", (uid, pair_id)).fetchone()
                if row:
                    out.append(self._row_pair(row))
        return out

    def holds_subject(self, user_id: str | None, subject_id: str) -> bool:
        uid = normalize_user_id(user_id)
        with self._lock:
            row = self._conn.execute("SELECT 1 FROM subjects WHERE user_id = ? AND subject_id = ?", (uid, subject_id)).fetchone()
        return row is not None

    def all_pairs(self, user_id: str | None) -> list[MemoryPair]:
        uid = normalize_user_id(user_id)
        with self._lock:
            rows = self._conn.execute("SELECT * FROM pairs WHERE user_id = ? ORDER BY ts, seq", (uid,)).fetchall()
        return [self._row_pair(r) for r in rows]

    def search(self, user_id: str | None, query: str, limit: int = 20) -> list[SearchHit]:
        uid = normalize_user_id(user_id)
        match = fts_query(query)
        if not match:
            return []
        with self._lock:
            rows = self._conn.execute(
                "SELECT p.*, bm25(pairs_fts) AS score FROM pairs_fts JOIN pairs p ON p.rowid = pairs_fts.rowid "
                "WHERE pairs_fts MATCH ? AND p.user_id = ? ORDER BY score LIMIT ?",
                (match, uid, limit),
            ).fetchall()
        return [SearchHit(pair=self._row_pair(r), score=float(r["score"])) for r in rows]

    def subjects_search(self, user_id: str | None, query: str, limit: int = 10) -> list[Subject]:
        uid = normalize_user_id(user_id)
        words = {w.lower() for w in WORD_RE.findall(query) if len(w) >= 3}
        with self._lock:
            rows = self._conn.execute("SELECT * FROM subjects WHERE user_id = ?", (uid,)).fetchall()
        scored: list[tuple[int, Subject]] = []
        for row in rows:
            text = (row["subject_text"] + " " + row["description_text"]).lower()
            hits = sum(1 for w in words if w in text)
            if hits:
                scored.append((hits, Subject(id=row["subject_id"], subject_text=row["subject_text"], description_text=row["description_text"])))
        scored.sort(key=lambda item: -item[0])
        return [s for _, s in scored[:limit]]

    def subject_pairs(self, user_id: str | None, subject_id: str) -> list[MemoryPair]:
        uid = normalize_user_id(user_id)
        with self._lock:
            rows = self._conn.execute(
                "SELECT p.* FROM links l JOIN pairs p ON p.user_id = l.user_id AND p.pair_id = l.pair_id "
                "WHERE l.user_id = ? AND l.subject_id = ? ORDER BY p.ts, p.seq",
                (uid, subject_id),
            ).fetchall()
        return [self._row_pair(r) for r in rows]
