from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from ..protocol import MemoryPair
from ..store import CODE_RE, EMAIL_RE, Store

STOPWORDS = frozenset("""a an the and or but if then else of to in on at by for with about from into over after before during between under without within
i me my mine we our you your yours he him his she her hers they them their it its this that these those what which who whom whose where when why how
is are was were be been being am do does did done have has had having can could should would will shall may might must
not no yes so as than too very just only also still again ever never now then here there once twice
please tell give remind remember recall know think say said mention mentioned told ask asked need want like
get got use used using find found look looked back go went come came make made take took keep kept
one two three first last next current currently latest actually really exactly right ago earlier later up down out off
that's what's i'm i've you're don't doesn't didn't isn't aren't can't won't let's ok okay hey hi hello thanks thank
which should now mean began around conversation talking going did much many how long far whole altogether everything anything something
already any every per here ll re ve""".split())

QUOTE_RE = re.compile(r"“([^”\n]{2,60})”|\"([^\"\n]{2,60})\"|‘([^’\n]{2,60})’")
NAME_RE = re.compile(r"\b([A-Z][a-z]+(?:[ -][A-Z][a-z]+)+)\b")
CAP_RE = re.compile(r"\b([A-Z][a-z]{2,})\b")
SHORT_CAP_RE = re.compile(r"\b([A-Z][a-z])\b")
LOWER_RE = re.compile(r"\b[a-z]{3,}\b")
WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’]*")
IDENTIFIER_RE = re.compile(r"\b(?=[0-9a-z]*[0-9])(?=[0-9a-z]*[a-z])[0-9a-z]{12,}\b")
SENTENCE_BREAK_RE = re.compile(r"(?:(?<=[.?!])|(?<=[.?!][\"'”’)\]]))\s+|(?<=[:;])\s+(?=[A-Z])|\s+[—–]\s+(?=[A-Z])")
QUESTION_END_RE = re.compile(r"\?[\"'”’)\]]*$")
SENTENCE_START = frozenset("""What Which Who Where When How Why Give Remind Think Remember Before After Looking For Can Did Work Read Answer Please
Quick Checking Sorting Just Note Tell Find Search Look Use Set Switch Change Make Put Add Run Start Kick Time Go Have Send See Two Real Oh Hey
The This That These Those Our My Your And But Or So If Then Also Once Again Now Later Earlier Here There Yes No Not Update Side Random Off One
Notes Adding Recorded Noted Logged Kept Tracked Understood Got Nice Thanks Subject From Pasted Everyone Back Contact Handoff
Ignore Treat When Against Do Assume Local Within Separately Eventually Lovely Perfect Underneath Meanwhile""".split())

TYPE_ANCHOR = {"e": 1.2, "c": 1.2, "q": 2.4, "n": 0.9, "i": 0.7, "k": 0.6, "b": 0.8, "w": 0.0}
TYPE_EDGE = {"e": 1.0, "c": 0.4, "q": 0.9, "n": 0.85, "i": 0.7, "k": 0.4}
TYPE_FANOUT = {"e": 32, "c": 32, "q": 24, "n": 16, "i": 16, "k": 12, "b": 12, "w": 6}
TYPE_ORDER = {"e": 0, "c": 1, "q": 2, "n": 3, "i": 4, "k": 5}
LONG_PAIR_CHARS = 2500
ALIAS_RECORD_CHARS = 400
LONG_CONFIDENCE_FACTOR = 1.5
TAIL_LONG_MIN_SHARE = 0.25
MAX_TRAVERSED_VALUES = 16
HUB_VALUES = 10
MAX_EXPANSIONS_PER_HOP = 24
COVERAGE_MAX_DF = 24
COVERAGE_WEIGHT = 0.75
CONJUNCTION_BONUS = 0.5
HOP_CONJUNCTION_BONUS = 1.0
COVERAGE_LENGTH_CHARS = 3000.0
LINK_FANOUT = 16
MIN_EXPANSION_SHARE = 0.3
PRIMARY_BAND_SHARE = 0.45
SECONDARY_BAND_SHARE = 0.20


@dataclass
class Candidate:
    pair: MemoryPair
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    hop: int = 0
    anchored: bool = False
    keys: frozenset[str] = frozenset()
    pinned: bool = False


@dataclass
class Node:
    pair: MemoryPair
    size: int
    words: set[str]
    values: dict[str, str]


def identifier_tokens(text: str) -> list[str]:
    return IDENTIFIER_RE.findall(text.lower())


def asked_part(text: str, identifiers: frozenset[str] = frozenset()) -> str:
    sentences = [part.strip() for part in SENTENCE_BREAK_RE.split(text) if part.strip()]
    if not sentences:
        return text
    kept = {index for index, sentence in enumerate(sentences) if QUESTION_END_RE.search(sentence)}
    if not kept:
        kept = {max(range(len(sentences)), key=lambda index: len(sentences[index]))}
    kept |= {index for index, sentence in enumerate(sentences) if identifiers & set(identifier_tokens(sentence))}
    return " ".join(sentences[index] for index in sorted(kept))


def tokens(text: str) -> list[str]:
    out: list[str] = []
    for raw in WORD_RE.findall(text):
        w = raw.lower().replace("’", "'").strip("'")
        out.append(w[:-2] if raw[:1].isupper() and w.endswith("'s") and len(w) > 3 else w)
    return out


def content_words(text: str) -> list[str]:
    out: list[str] = []
    for w in tokens(text):
        if (len(w) < 3 and not w.isdigit()) or w in STOPWORDS:
            continue
        if w not in out:
            out.append(w)
    return out


def specificity(df: int) -> float:
    return 1.0 / (1.0 + math.log(max(1, df)))


def within_one_edit(a: str, b: str) -> bool:
    if a == b:
        return False
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diffs = [i for i in range(la) if a[i] != b[i]]
        if len(diffs) == 1:
            return True
        return len(diffs) == 2 and diffs[1] == diffs[0] + 1 and a[diffs[0]] == b[diffs[1]] and a[diffs[1]] == b[diffs[0]]
    short, long_ = (a, b) if la < lb else (b, a)
    i = 0
    while i < len(short) and short[i] == long_[i]:
        i += 1
    return short[i:] == long_[i + 1 :]


class UserIndex:
    def __init__(self, pairs: list[MemoryPair]) -> None:
        self.nodes: dict[str, Node] = {}
        self.df: Counter[str] = Counter()
        self.lower_df: Counter[str] = Counter()
        self.cap_df: Counter[str] = Counter()
        self.word_postings: dict[str, set[str]] = defaultdict(set)
        self.postings: dict[str, set[str]] = defaultdict(set)
        self.bigrams: dict[tuple[str, str], set[str]] = defaultdict(set)
        texts = {p.pair_id: p.prompt + "\n" + p.response for p in pairs}
        for pid, text in texts.items():
            words = set(tokens(text))
            for w in words:
                self.df[w] += 1
                self.word_postings[w].add(pid)
            for w in set(LOWER_RE.findall(EMAIL_RE.sub(" ", text))):
                self.lower_df[w] += 1
            for w in set(CAP_RE.findall(text)) | set(SHORT_CAP_RE.findall(text)):
                self.cap_df[w.lower()] += 1
        self.vocab_by_len: dict[int, list[str]] = defaultdict(list)
        for w in sorted(self.df):
            self.vocab_by_len[len(w)].append(w)
        for pair in sorted(pairs, key=lambda p: (p.timestamp, p.pair_id)):
            text = texts[pair.pair_id]
            toks = tokens(text)
            values = self.extract_values(text)
            self.nodes[pair.pair_id] = Node(pair=pair, size=len(text), words=set(toks), values=values)
            for key in values:
                self.postings[key].add(pair.pair_id)
            for bigram in set(zip(toks, toks[1:])):
                self.bigrams[bigram].add(pair.pair_id)

    def neighbours(self, sources: list[str], seen: set[str], max_chars: int, limit: int) -> dict[str, float]:
        reach: dict[str, set[str]] = defaultdict(set)
        for pid in sources:
            node = self.nodes.get(pid)
            if node is None:
                continue
            for key, kind in node.values.items():
                if kind not in TYPE_EDGE:
                    continue
                carrying = self.postings.get(key) or set()
                if not 1 < len(carrying) <= LINK_FANOUT:
                    continue
                for target in carrying:
                    if target not in seen and self.nodes[target].size <= max_chars:
                        reach[target].add(key)
        ranked = sorted(reach, key=lambda pid: (-len(reach[pid]), self.nodes[pid].size, pid))[:limit]
        return {pid: float(len(reach[pid])) for pid in ranked}

    def linked(self, sources: list[str], pool: set[str]) -> set[str]:
        keys: set[str] = set()
        for pid in sources:
            node = self.nodes.get(pid)
            if node is None:
                continue
            for key, kind in node.values.items():
                if kind in TYPE_EDGE and 1 < len(self.postings.get(key) or ()) <= LINK_FANOUT:
                    keys.add(key)
        return {pid for pid in pool if keys & set(self.nodes[pid].values)}

    def hub_factor(self, pid: str) -> float:
        return min(1.0, HUB_VALUES / max(1, len(self.nodes[pid].values))) ** 0.5

    def name_like(self, word: str) -> bool:
        if word in SENTENCE_START or len(word) < 2:
            return False
        low = word.lower()
        return self.lower_df[low] <= self.cap_df[low] / 2

    def clean_name(self, name: str) -> list[str]:
        parts = re.split(r"[ -]", name)
        while parts and not self.name_like(parts[0]):
            parts.pop(0)
        return parts

    def extract_values(self, text: str) -> dict[str, str]:
        values: dict[str, str] = {}
        for email in EMAIL_RE.findall(text):
            values["e:" + email.lower()] = "e"
            local = [p for p in re.split(r"[._-]", email.split("@")[0].lower()) if p.isalpha() and len(p) >= 2]
            if len(local) >= 2:
                values["n:" + " ".join(local)] = "n"
            elif len(local) == 1 and len(local[0]) >= 5:
                values["i:" + local[0]] = "i"
        for code in CODE_RE.findall(text):
            values["c:" + code.upper()] = "c"
        for m in QUOTE_RE.finditer(text):
            quoted = (m.group(1) or m.group(2) or m.group(3) or "").strip(" .,;:!?").lower()
            if 2 <= len(quoted) <= 40 and len(quoted.split()) <= 5:
                values["q:" + quoted] = "q"
        covered: set[str] = set()
        for m in NAME_RE.finditer(text):
            parts = self.clean_name(m.group(1))
            if len(parts) >= 2:
                values["n:" + " ".join(parts).lower()] = "n"
                values["i:" + parts[0][0].lower() + parts[-1].lower()] = "i"
                covered.update(parts)
            elif len(parts) == 1:
                values["k:" + parts[0].lower()] = "k"
                covered.add(parts[0])
        for word in CAP_RE.findall(text):
            if word not in covered and self.name_like(word):
                values["k:" + word.lower()] = "k"
        for word in SHORT_CAP_RE.findall(text):
            if word not in covered and word not in SENTENCE_START and self.lower_df[word.lower()] == 0 and 0 < self.cap_df[word.lower()] <= TYPE_FANOUT["k"]:
                values["k:" + word.lower()] = "k"
        return values

    def fix_typo(self, word: str) -> str:
        if self.df[word] or len(word) < 4 or not word.isalpha():
            return word
        best, best_df = word, 0
        for length in (len(word) - 1, len(word), len(word) + 1):
            for cand in self.vocab_by_len.get(length, ()):
                if self.df[cand] > best_df and within_one_edit(word, cand):
                    best, best_df = cand, self.df[cand]
        return best


class Retriever:
    def __init__(self, store: Store, max_depth: int = 3, size_alpha: float = 0.5, confident_share: float = 0.4, hop_gain: float = 1.5, confident_alpha: float = 0.25, coverage_floor: int = 3) -> None:
        self.store = store
        self.coverage_floor = coverage_floor
        self.max_depth = max_depth
        self.size_alpha = size_alpha
        self.confident_share = confident_share
        self.hop_gain = hop_gain
        self.confident_alpha = confident_alpha
        self._indexes: dict[tuple[str, int], UserIndex] = {}

    def index(self, user_id: str | None) -> UserIndex:
        key = (user_id or "", self.store.version(user_id))
        cached = self._indexes.get(key)
        if cached is None:
            cached = UserIndex(self.store.all_pairs(user_id))
            self._indexes = {key: cached}
        return cached

    def question_anchors(self, index: UserIndex, question: str) -> dict[str, tuple[str, float]]:
        fixed = [index.fix_typo(w) for w in tokens(question)]
        claimed: set[int] = set()
        anchors: dict[str, tuple[str, float]] = {}

        def span(words: list[str]) -> list[int] | None:
            for start in range(len(fixed) - len(words) + 1):
                positions = list(range(start, start + len(words)))
                if fixed[start : start + len(words)] == words and not claimed.intersection(positions):
                    return positions
            return None

        def put(key: str, kind: str, df: int, words: list[str]) -> None:
            if df == 0 or df > TYPE_FANOUT[kind] * 2:
                return
            positions = span(words)
            if positions is None:
                return
            claimed.update(positions)
            anchors[key] = (kind, TYPE_ANCHOR[kind] * specificity(df))

        values = index.extract_values(question)
        for kind in ("e", "c", "q", "n", "i", "k"):
            for key, value_kind in values.items():
                if value_kind == kind:
                    put(key, kind, len(index.postings.get(key, ())), tokens(key[2:]))
        for first, second in zip(fixed, fixed[1:]):
            if first in STOPWORDS or second in STOPWORDS or len(first) < 3 or len(second) < 3 or first.isdigit() or second.isdigit():
                continue
            put(f"b:{first} {second}", "b", len(index.bigrams.get((first, second), ())), [first, second])
        if TYPE_ANCHOR["w"] > 0:
            for word in fixed:
                if len(word) >= 4 and word not in STOPWORDS and not word.isdigit():
                    put("w:" + word, "w", index.df[word], [word])
        return anchors

    def alias_anchors(self, index: UserIndex, anchors: dict[str, tuple[str, float]]) -> dict[str, tuple[str, float]]:
        out: dict[str, tuple[str, float]] = {}
        for key, (kind, _) in anchors.items():
            if kind != "n":
                continue
            for pid in sorted(index.postings.get(key, ())):
                node = index.nodes[pid]
                if node.size > ALIAS_RECORD_CHARS:
                    continue
                for value, value_kind in node.values.items():
                    alias = "k:" + value[2:]
                    df = len(index.postings.get(alias, ()))
                    if value_kind == "q" and " " not in value[2:] and 0 < df <= TYPE_FANOUT["k"] * 2:
                        out.setdefault(alias, ("k", TYPE_ANCHOR["k"] * specificity(df)))
        return out

    def coverage_seeds(self, index: UserIndex, question: str, claimed: set[str]) -> list[tuple[float, str]]:
        words = [index.fix_typo(w) for w in content_words(question)]
        total = max(1, len(index.nodes))
        idf = {w: math.log(1.0 + total / index.df[w]) for w in words if 0 < index.df[w] <= COVERAGE_MAX_DF}
        total_idf = sum(idf.values())
        open_words = [w for w in idf if w not in claimed]
        if not total_idf or not open_words:
            return []
        pool: set[str] = set()
        for w in sorted(open_words, key=lambda w: index.df[w])[:8]:
            pool.update(index.word_postings[w])
        seeds: list[tuple[float, str]] = []
        for pid in pool:
            node = index.nodes[pid]
            covered = sum(idf[w] for w in open_words if w in node.words)
            coverage = (covered / total_idf) * (1.0 / (1.0 + node.size / COVERAGE_LENGTH_CHARS)) ** 0.5
            if coverage > 0:
                seeds.append((coverage, pid))
        seeds.sort(key=lambda item: (-item[0], item[1]))
        return seeds

    def rank(self, user_id: str | None, question: str, nicknames: bool = False) -> tuple[list[Candidate], bool]:
        index = self.index(user_id)
        if not index.nodes:
            return [], False
        found: dict[str, Candidate] = {}

        def add(pid: str, score: float, reason: str, hop: int, anchored: bool = False) -> Candidate:
            cand = found.get(pid)
            if cand is None:
                cand = Candidate(pair=index.nodes[pid].pair, hop=hop, keys=frozenset(index.nodes[pid].values))
                found[pid] = cand
            cand.score += score
            cand.anchored = cand.anchored or anchored
            cand.reasons.append(f"{reason}={score:.2f}")
            return cand

        pinned: set[str] = set()
        for token in identifier_tokens(question):
            carrying = [pid for pid, node in index.nodes.items() if token in (node.pair.prompt + " " + node.pair.response).lower()]
            if len(carrying) >= 3:
                for pid in carrying:
                    add(pid, 1.0, f"id:{token}", 0, anchored=True)
                    pinned.add(pid)
                break
        anchors = self.question_anchors(index, question)
        if nicknames:
            for key, anchor in self.alias_anchors(index, anchors).items():
                anchors.setdefault(key, anchor)
        anchor_hits: dict[str, int] = Counter()
        for key, (kind, weight) in anchors.items():
            if kind == "b":
                first, second = key[2:].split(" ", 1)
                targets = index.bigrams.get((first, second), set())
            elif kind == "w":
                targets = index.word_postings.get(key[2:], set())
            else:
                targets = index.postings.get(key, set())
            for pid in sorted(targets):
                add(pid, weight * index.hub_factor(pid), key, 0, anchored=kind != "w")
                if kind != "w":
                    anchor_hits[pid] += 1
                if kind in ("e", "c"):
                    pinned.add(pid)
        for pid, hits in anchor_hits.items():
            if hits > 1:
                add(pid, found[pid].score * CONJUNCTION_BONUS * (hits - 1), f"conj:{hits}", 0)
        claimed = {w for key, (kind, _) in anchors.items() if kind != "w" for w in tokens(key[2:])}
        for position, (coverage, pid) in enumerate(self.coverage_seeds(index, question, claimed)):
            add(pid, COVERAGE_WEIGHT * coverage * coverage, f"cover:{coverage:.2f}", 0)
            if position < self.coverage_floor:
                pinned.add(pid)
        if not found:
            return [], bool(anchors)
        top_seed = max(cand.score for cand in found.values())
        hop_received: dict[str, float] = defaultdict(float)
        propagated: dict[str, float] = {}
        for hop in range(1, self.max_depth + 1):
            frontier = sorted((pid for pid in found if found[pid].score - propagated.get(pid, 0.0) >= MIN_EXPANSION_SHARE * top_seed), key=lambda pid: (propagated.get(pid, 0.0) - found[pid].score, pid))[:MAX_EXPANSIONS_PER_HOP]
            if not frontier:
                break
            for pid in frontier:
                origin_score = found[pid].score - propagated.get(pid, 0.0)
                propagated[pid] = found[pid].score
                node = index.nodes[pid]
                traversable = [(key, kind) for key, kind in node.values.items() if kind in TYPE_EDGE and 1 < len(index.postings[key]) <= TYPE_FANOUT[kind]]
                if node.size > LONG_PAIR_CHARS:
                    traversable = [(key, kind) for key, kind in traversable if kind in ("e", "c", "q")]
                traversable.sort(key=lambda item: (TYPE_ORDER[item[1]], len(index.postings[item[0]])))
                traversable = traversable[:MAX_TRAVERSED_VALUES]
                kind_counts = Counter(kind for _, kind in traversable)
                gains: dict[str, list[tuple[float, str]]] = defaultdict(list)
                for key, kind in traversable:
                    targets = sorted(target for target in index.postings[key] if target != pid)
                    if not targets:
                        continue
                    gain = min(origin_score, self.hop_gain * origin_score * TYPE_EDGE[kind] / kind_counts[kind] / len(targets))
                    for target in targets:
                        gains[target].append((gain, key))
                for target, shares in sorted(gains.items()):
                    room = top_seed - hop_received[target]
                    target_hub = index.hub_factor(target) * (1.0 + HOP_CONJUNCTION_BONUS * (len({key for _, key in shares}) - 1))
                    for gain, key in shares:
                        gain = min(gain * target_hub, room)
                        if gain <= 0:
                            break
                        room -= gain
                        hop_received[target] += gain
                        add(target, gain, f"h{hop}:{key}", hop)
        top_score = top_seed
        def threshold(pid: str) -> float:
            return self.confident_share * top_score * (LONG_CONFIDENCE_FACTOR if index.nodes[pid].size > LONG_PAIR_CHARS else 1.0)

        confident = [c for c in found.values() if c.pair.pair_id in pinned or c.score >= threshold(c.pair.pair_id)]
        confident.sort(key=lambda c: (c.pair.pair_id not in pinned, -c.score / (index.nodes[c.pair.pair_id].size + 64) ** self.confident_alpha, c.pair.pair_id))
        tail = [c for c in found.values() if c.pair.pair_id not in pinned and c.score < threshold(c.pair.pair_id) and (index.nodes[c.pair.pair_id].size <= LONG_PAIR_CHARS or c.score >= TAIL_LONG_MIN_SHARE * top_score)]
        admitted = {c.pair.pair_id for c in confident + tail}
        arc_keys = {key for pid in admitted for key, kind in index.nodes[pid].values.items() if kind == "c"}
        tail += [c for c in found.values() if c.pair.pair_id not in admitted and any(kind == "c" and key in arc_keys for key, kind in index.nodes[c.pair.pair_id].values.items())]
        tail.sort(key=lambda c: (-c.score / (index.nodes[c.pair.pair_id].size + 64) ** self.size_alpha, c.pair.pair_id))
        return confident + tail, bool(anchors)


def relevance_band(score: float, top: float) -> int:
    if top <= 0 or score >= PRIMARY_BAND_SHARE * top:
        return 0
    return 1 if score >= SECONDARY_BAND_SHARE * top else 2
