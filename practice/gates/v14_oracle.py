"""Exact v14 program shape of every open/personal program case, recomputed from the seed.

Analysis only: this mirrors the draws of datagen universe/v13_contract.go, personal.go and v14_*.go
(OpaqueCaseID, v13Perm, v14Perm, V14FamilyFor, drawV14ChainPlan, the process/sequence draws) so
local runs can be read by shape. It must never reach a harness.

    shapes(seed) -> {case_id: Shape}
"""
import hashlib
from dataclasses import dataclass

MASK64 = (1 << 64) - 1

BUSINESS_FAMILIES = ["owner-after-correction", "standing-status", "latest-event", "client-vs-vendor",
                     "next-action-responsible", "current-channel", "records-disagree", "holder-vs-actor", "identity-join"]
ROLE_SLOTS = [3, 7, 8]
ROLE_FAMILIES = ["client-vs-vendor", "holder-vs-actor", "identity-join"]
TEMPORAL_FAMILIES = ["latest-event", "next-action-responsible", "current-channel"]
TEMPORAL_SHAPE = {"latest-event": "sequence", "next-action-responsible": "process", "current-channel": "as-of"}
CHAIN_BUSINESS = {"owner-after-correction", "standing-status"}
PERSONAL_DOMAINS = ["household-chores", "appointments-medication", "school-logistics", "family-milestones",
                    "subscriptions-renewals", "travel-logistics", "hobbies-clubs"]
CHAIN_TEMPLATES = [("revert", 4), ("revert-to-middle", 4), ("change-then-declined", 3), ("declined", 2),
                   ("error", 2), ("second-error", 3)]
RELATIONS = ["base", "renderer", "distractor", "counterfactual"]


def fnv1a(text: str) -> int:
    h = 0xcbf29ce484222325
    for b in text.encode():
        h = ((h ^ b) * 0x100000001b3) & MASK64
    return h


def v10_seed(seed: int, salt: str) -> int:
    return fnv1a(f"dittobench-v10:{seed}:{salt}") & ((1 << 63) - 1)


def v13_index(seed: int, salt: str, n: int) -> int:
    return v10_seed(seed, "v13:" + salt) % n


def v13_perm(seed: int, salt: str, n: int) -> list[int]:
    idx = list(range(n))
    for i in range(n - 1, 0, -1):
        j = v10_seed(seed, f"v13:{salt}:{i}") % (i + 1)
        idx[i], idx[j] = idx[j], idx[i]
    return idx


def v14_mix(seed: int, salt: str) -> int:
    z = (v10_seed(seed, "v14:" + salt) + 0x9e3779b97f4a7c15) & MASK64
    z = ((z ^ (z >> 30)) * 0xbf58476d1ce4e5b9) & MASK64
    z = ((z ^ (z >> 27)) * 0x94d049bb133111eb) & MASK64
    return z ^ (z >> 31)


def v14_index(seed: int, salt: str, n: int) -> int:
    return v14_mix(seed, salt) % n


def v14_perm(seed: int, salt: str, n: int) -> list[int]:
    idx = list(range(n))
    for i in range(n - 1, 0, -1):
        j = v14_index(seed, f"{salt}:{i}", i + 1)
        idx[i], idx[j] = idx[j], idx[i]
    return idx


def v14_coin(seed: int, salt: str) -> bool:
    return v13_index(seed, salt, 1000) < 500


def opaque_case_id(seed: int, kind: str, ordinal: int) -> str:
    return "c" + hashlib.sha256(f"dittobench-case|{seed}|{kind}|{ordinal}".encode()).hexdigest()[:16]


def business_family(seed: int, group: int) -> str:
    slot = group % len(BUSINESS_FAMILIES)
    if slot in ROLE_SLOTS:
        return ROLE_FAMILIES[v14_perm(seed, "v14-role-slot", len(ROLE_FAMILIES))[ROLE_SLOTS.index(slot)]]
    family = BUSINESS_FAMILIES[slot]
    if family in TEMPORAL_FAMILIES:
        return TEMPORAL_FAMILIES[v13_perm(seed, "v14-temporal-slot", len(TEMPORAL_FAMILIES))[TEMPORAL_FAMILIES.index(family)]]
    return family


def chain_plan(seed: int, domain: str, group: int, max_values: int) -> str:
    fit = [name for name, values in CHAIN_TEMPLATES if values <= max_values]
    template = fit[v13_index(seed, f"v14-chain-{domain}-{group}", len(fit))]
    cue = {2: "free", 3: "misplaced"}.get(v13_index(seed, f"v14-cue-{domain}-{group}", 4), "announced")
    return f"{template}/{cue}"


def process_detail(seed: int, group: int) -> str:
    key = lambda name: f"v14-proc-{name}-{group}"
    n = 3 + v13_index(seed, key("n"), 3)
    mode = "untouched" if v14_coin(seed, key("mode")) else "reopened"
    return f"{mode}/{n}-steps"


def sequence_detail(seed: int, group: int) -> str:
    key = lambda name: f"v14-seq-{name}-{group}"
    n = 5 + v13_index(seed, key("n"), 4)
    query = ["nth", "after", "before"][v13_index(seed, key("query"), 3)]
    return f"{query}/{n}-events"


@dataclass(frozen=True)
class Shape:
    kind: str       # chain, process, sequence, as-of, membership, custody, identity, client-vs-vendor, records-disagree
    detail: str     # template/cue for chains, the family or domain otherwise
    domain: str
    group: int
    relation: str

    @property
    def label(self) -> str:
        return f"{self.kind}:{self.detail}" if self.detail else self.kind


def shapes(seed: int, business_groups: int = 4, personal_groups: int = 6) -> dict[str, Shape]:
    out: dict[str, Shape] = {}
    for group in range(business_groups):
        family = business_family(seed, group)
        if family in CHAIN_BUSINESS:
            kind, detail = "chain", chain_plan(seed, "business", group, 4)
        elif family in TEMPORAL_SHAPE:
            kind = TEMPORAL_SHAPE[family]
            detail = process_detail(seed, group) if kind == "process" else sequence_detail(seed, group) if kind == "sequence" else ""
        elif family == "holder-vs-actor":
            hops = 1 + v14_index(seed, f"v14-hops-{group}", 2)
            ask = "actor" if v14_index(seed, f"v14-ask-actor-{group}", 2) == 1 else "holder"
            kind, detail = "custody", f"{ask}/{hops}-hop"
        elif family == "identity-join":
            contact = v14_index(seed, f"v14-ask-contact-{group}", 2) == 1
            initials = contact and v14_index(seed, f"v14-initials-{group}", 2) == 1
            kind, detail = "identity", ("contact" + ("/initials" if initials else "")) if contact else "name"
        else:
            kind, detail = family, ""
        for variant in range(4):
            out[opaque_case_id(seed, "v13-program-case", group * 4 + variant)] = Shape(kind, detail, family, group, RELATIONS[variant])
    domains = v13_perm(seed, "personal-domains", len(PERSONAL_DOMAINS))
    for group in range(personal_groups):
        domain = PERSONAL_DOMAINS[domains[group % len(domains)]]
        if domain == "school-logistics":
            kind, detail = "membership", ""
        else:
            kind, detail = "chain", chain_plan(seed, "personal", group, 3 if domain == "family-milestones" else 4)
        for variant in range(4):
            out[opaque_case_id(seed, "v13-personal-case", group * 4 + variant)] = Shape(kind, detail, domain, group, RELATIONS[variant])
    return out
