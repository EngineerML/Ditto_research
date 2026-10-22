"""Generated DittoBench datasets turned into lab cases with their ground truth.

A lab case is what one /run carries (the text, the user, the records that user holds
when the case runs) plus what the answer key says about it: which lane it belongs in
and which records it needs. Datasets come from the official generator, so they match
what validators build for the same seed and surface salt.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GENERATE = ROOT / ".cache" / "dittobench-generate"
DATASETS = ROOT / ".cache" / "datasets"
BENCH = 13

MEMORY_READS = frozenset({"search_memories", "search_subjects", "fetch_memories", "search_memories_in_subjects"})
MEMORY_WRITES = frozenset({"save_memory", "update_memory", "delete_memory"})
DECLINE_PREFIX = "("
MAX_ARG_HOLDERS = 3


@dataclass(frozen=True)
class Record:
    pair_id: str
    session_id: str
    timestamp: str
    prompt: str
    response: str

    @cached_property
    def text(self) -> str:
        return self.prompt + "\n" + self.response


@dataclass
class Case:
    key: str
    phase: str            # tool | memory
    kind: str             # tool category or memory question type
    text: str
    user: str
    store: tuple[Record, ...]
    lane: str             # records | action | none (answer without any call)
    tools: tuple[str, ...]
    needs: frozenset[str]
    answers: tuple[str, ...]
    twin: str
    catalog: tuple[dict, ...]


def dataset_path(seed: int, salt: int = 0, size: str = "full") -> Path:
    path = DATASETS / f"v{BENCH}_s{seed}_salt{salt}_{size}.json"
    if not path.is_file():
        DATASETS.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(GENERATE), "-bench-version", str(BENCH), "-seed", str(seed), "-surface-salt", str(salt),
                        "-run-size", size, "-out", str(path)], check=True, capture_output=True)
    return path


def records(raw: list[dict]) -> list[Record]:
    return [Record(p["pair_id"], p.get("session_id", ""), p.get("timestamp", ""), p.get("prompt", ""), p.get("response", "")) for p in raw]


def tool_lane(names: set[str]) -> str:
    if not names:
        return "none"
    return "records" if names <= MEMORY_READS else "action"


def tool_needs(case: dict, world: tuple[Record, ...]) -> set[str]:
    needs: set[str] = set()
    prerequisites = case.get("prerequisite_pairs") or []
    if 0 < len(prerequisites) <= 2:
        needs |= {p["pair_id"] for p in prerequisites}
    for tool in case.get("expected_tools") or []:
        for name, value in (tool.get("required_args") or {}).items():
            if name == "pair_id" and isinstance(value, str):
                needs.add(value)
            elif isinstance(value, str) and len(value) >= 4:
                holders = [r.pair_id for r in world if value.lower() in r.text.lower()]
                if 1 <= len(holders) <= MAX_ARG_HOLDERS:
                    needs |= set(holders)
    return needs


def load(seed: int, salt: int = 0, size: str = "full") -> list[Case]:
    d = json.load(open(dataset_path(seed, salt, size)))
    tag = f"s{seed}/salt{salt}"
    catalog = tuple(d.get("catalog") or [])
    world = tuple(r for c in d["tool_cases"] for r in records(c.get("prerequisite_pairs") or []))
    cases: list[Case] = []
    for c in d["tool_cases"]:
        names = {t["name"] for t in c.get("expected_tools") or []}
        cases.append(Case(f"{tag}/{c['id']}", "tool", c["category"], c["prompt"], "miner", world, tool_lane(names),
                          tuple(sorted(names)), frozenset(tool_needs(c, world)), (), "", catalog))
    # Memory waves extend the same store the tool phase used; another user's graph stands alone.
    held: dict[str, list[Record]] = {"miner": list(world)}
    snapshots: dict[tuple[str, int], tuple[Record, ...]] = {}
    for wave in d["memory_waves"]:
        user = wave.get("user_id") or "miner"
        held.setdefault(user, []).extend(records(wave.get("pairs") or []))
        snapshots[(user, wave.get("wave", 0))] = tuple(held[user])
    for c in d["memory_cases"]:
        user = c.get("user_id") or "miner"
        wave = c.get("run_after_wave") or 0
        store = snapshots.get((user, wave)) or snapshots.get((user, 0)) or tuple(held.get(user, ()))
        expected = c.get("expected_answer") or ""
        answers = tuple(c.get("answer_items") or ([expected] if expected and not expected.startswith(DECLINE_PREFIX) else []))
        cases.append(Case(f"{tag}/{c['id']}", "memory", c["question_type"], c["question"], user, store, "records", (),
                          frozenset(c.get("v10_evidence_pair_ids") or []), answers, c.get("twin_group") or "", catalog))
    return cases
