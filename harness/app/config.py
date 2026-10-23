from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip()


def _flag(name: str, default: bool) -> bool:
    value = _env(name)
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Levers:
    route_catalog: bool = True
    route_order: bool = True
    result_suffix: bool = True
    result_read: bool = True
    typo_cues: bool = True
    route_preamble: bool = True
    route_asking: bool = True
    route_anchor: bool = True
    route_lexicon: bool = True
    route_operands: bool = True
    route_save: bool = True
    route_counting: bool = True
    plan_first: bool = True

    @classmethod
    def from_env(cls) -> "Levers":
        return cls(
            route_catalog=_flag("HARNESS_ROUTE_CATALOG", True),
            route_order=_flag("HARNESS_ROUTE_ORDER", True),
            result_suffix=_flag("HARNESS_RESULT_SUFFIX", True),
            result_read=_flag("HARNESS_RESULT_READ", True),
            typo_cues=_flag("HARNESS_TYPO_CUES", True),
            route_preamble=_flag("HARNESS_ROUTE_PREAMBLE", True),
            route_asking=_flag("HARNESS_ROUTE_ASKING", True),
            route_anchor=_flag("HARNESS_ROUTE_ANCHOR", True),
            route_lexicon=_flag("HARNESS_ROUTE_LEXICON", True),
            route_operands=_flag("HARNESS_ROUTE_OPERANDS", True),
            route_save=_flag("HARNESS_ROUTE_SAVE", True),
            route_counting=_flag("HARNESS_ROUTE_COUNTING", True),
            plan_first=_flag("HARNESS_PLAN_FIRST", True),
        )


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    openrouter_api_key: str
    openrouter_base_url: str
    openai_base_url: str
    openai_api_key: str
    reasoning_effort: str
    platform_base_url: str
    ollama_base_url: str
    db_path: str
    case_budget_seconds: float
    packet_char_budget: int
    llm_timeout_seconds: float
    llm_max_attempts: int
    tool_timeout_seconds: float
    max_model_turns: int
    mock_model: bool
    log_level: str
    max_output_tokens: int = 6000
    max_inflight_calls: int = 4
    action_max_turns: int = 8
    action_max_tokens: int = 6000
    action_reasoning_effort: str = "medium"
    recall_max_tokens: int = 2000
    recall_reasoning_effort: str = "low"
    records_reasoning_effort: str = "medium"
    inference_base_url: str = ""
    levers: Levers = field(default_factory=Levers)
    subject_discipline: bool = True
    arc_contiguous: bool = True
    worksheet: bool = True
    records_effort_high: bool = False
    thread_first: bool = True
    thread_reading: bool = True
    evidence_closure: bool = True
    link_hop: bool = True
    coverage: bool = True
    sampling_temperature: float = 0.0
    sampling_seed: str = "42"
    sampling_top_p: str = ""
    coverage_floor: int = 3
    deliberation: bool = True
    drafts: int = 3
    draft_temperature: float = 0.7
    long_packet_chars: int = 30000
    embeddings: bool = False
    embed_timeout_seconds: float = 30.0
    meaning_records: int = 0
    meaning_chars: int = 0
    meaning_order: bool = False
    search_record_chars: int = 7000
    search_long_records: int = 2
    search_passes: int = 5
    search_temperature: float = 0.7
    short_programs: bool = True
    short_route: bool = True
    short_order_cache: bool = True
    short_shared_draft: bool = True
    short_max_chars: int = 30000
    short_effort: str = "medium"
    topic_decide_effort: str = "medium"
    short_max_tokens: int = 12000
    short_story: bool = True
    story_max_chars: int = 30000
    story_min_density: int = 3
    follow_up: bool = True
    follow_up_retry: bool = True
    topic_draft: bool = True
    program_full_dates: bool = True
    order_max_tokens: int = 16000
    finder_order: bool = True
    action_topic: bool = True
    meaning_route: bool = True
    meaning_sure: float = 0.8
    widen: bool = True
    widen_dense: int = 12
    widen_text: int = 8
    widen_chars: int = 24000
    widen_anchored: bool = True
    short_order_votes: int = 3
    select_mode: str = "refill"
    swap_top: int = 12

    @classmethod
    def from_env(cls) -> "Settings":
        provider = _env("DITTOBENCH_PROVIDER", "openrouter").lower()
        return cls(
            provider=provider,
            model=_env("DITTOBENCH_MODEL", "openai/gpt-oss-20b"),
            openrouter_api_key=_env("OPENROUTER_API_KEY"),
            openrouter_base_url=_env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            openai_base_url=_env("OPENAI_BASE_URL"),
            openai_api_key=_env("OPENAI_API_KEY"),
            reasoning_effort=_env("HARNESS_REASONING_EFFORT", "medium").lower(),
            platform_base_url=_env("DITTOBENCH_INFERENCE_BASE_URL") or _env("CHUTES_BASE_URL") or _env("OPENAI_BASE_URL") or _env("OPENROUTER_BASE_URL"),
            ollama_base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),
            db_path=_env("DITTOBENCH_DB", "/tmp/dittobench.db"),
            case_budget_seconds=float(_env("HARNESS_CASE_BUDGET_SECONDS", "285")),
            packet_char_budget=int(_env("HARNESS_PACKET_CHAR_BUDGET", "24000")),
            llm_timeout_seconds=float(_env("HARNESS_LLM_TIMEOUT_SECONDS", "100")),
            llm_max_attempts=int(_env("HARNESS_LLM_MAX_ATTEMPTS", "2")),
            tool_timeout_seconds=float(_env("HARNESS_TOOL_TIMEOUT_SECONDS", "20")),
            max_model_turns=int(_env("HARNESS_MAX_MODEL_TURNS", "12")),
            mock_model=_env("HARNESS_MOCK_MODEL", "0") in {"1", "true", "yes"},
            log_level=_env("HARNESS_LOG_LEVEL", "INFO").upper(),
            max_output_tokens=int(_env("HARNESS_MAX_OUTPUT_TOKENS", "6000")),
            max_inflight_calls=int(_env("HARNESS_MAX_INFLIGHT_CALLS", "4")),
            action_max_turns=int(_env("HARNESS_ACTION_MAX_TURNS", "8")),
            action_max_tokens=int(_env("HARNESS_ACTION_MAX_TOKENS", "6000")),
            action_reasoning_effort=_env("HARNESS_ACTION_REASONING_EFFORT", "medium").lower(),
            recall_max_tokens=int(_env("HARNESS_RECALL_MAX_TOKENS", "2000")),
            recall_reasoning_effort=_env("HARNESS_RECALL_REASONING_EFFORT", "low").lower(),
            records_reasoning_effort=_env("HARNESS_RECORDS_REASONING_EFFORT", "medium").lower(),
            inference_base_url=_env("DITTOBENCH_INFERENCE_BASE_URL"),
            levers=Levers.from_env(),
            subject_discipline=_flag("HARNESS_SUBJECT_DISCIPLINE", True),
            arc_contiguous=_flag("HARNESS_ARC_CONTIGUOUS", True),
            worksheet=_flag("HARNESS_WORKSHEET", True),
            records_effort_high=_flag("HARNESS_RECORDS_EFFORT_HIGH", False),
            thread_first=_flag("HARNESS_THREAD_FIRST", True),
            thread_reading=_flag("HARNESS_THREAD_READING", True),
            evidence_closure=_flag("HARNESS_EVIDENCE_CLOSURE", True),
            link_hop=_flag("HARNESS_LINK_HOP", True),
            coverage=_flag("HARNESS_COVERAGE", True),
            sampling_temperature=float(_env("HARNESS_SAMPLING_TEMPERATURE", "0")),
            sampling_seed=_env("HARNESS_SAMPLING_SEED", "42").strip(),
            sampling_top_p=_env("HARNESS_SAMPLING_TOP_P", "").strip(),
            coverage_floor=int(_env("HARNESS_COVERAGE_FLOOR", "3")),
            deliberation=_flag("HARNESS_DELIBERATION", True),
            drafts=int(_env("HARNESS_DRAFTS", "3")),
            draft_temperature=float(_env("HARNESS_DRAFT_TEMPERATURE", "0.7")),
            long_packet_chars=int(_env("HARNESS_LONG_PACKET_CHARS", "30000")),
            search_record_chars=int(_env("HARNESS_SEARCH_RECORD_CHARS", "7000")),
            search_long_records=int(_env("HARNESS_SEARCH_LONG_RECORDS", "2")),
            search_passes=int(_env("HARNESS_SEARCH_PASSES", "5")),
            search_temperature=float(_env("HARNESS_SEARCH_TEMPERATURE", "0.7")),
            embeddings=_flag("HARNESS_EMBEDDINGS", True),
            embed_timeout_seconds=float(_env("HARNESS_EMBED_TIMEOUT_SECONDS", "30")),
            meaning_records=int(_env("HARNESS_MEANING_RECORDS", "5")),
            meaning_chars=int(_env("HARNESS_MEANING_CHARS", "6000")),
            meaning_order=_flag("HARNESS_MEANING_ORDER", True),
            short_max_chars=int(_env("HARNESS_SHORT_MAX_CHARS", "30000")),
            short_effort=_env("HARNESS_SHORT_EFFORT", "medium").lower(),
            topic_decide_effort=_env("HARNESS_TOPIC_DECIDE_EFFORT", "medium").lower(),
            short_max_tokens=int(_env("HARNESS_SHORT_MAX_TOKENS", "12000")),
            story_max_chars=int(_env("HARNESS_STORY_MAX_CHARS", "30000")),
            story_min_density=int(_env("HARNESS_STORY_MIN_DENSITY", "3")),
            follow_up=_flag("HARNESS_FOLLOW_UP", True),
            follow_up_retry=_flag("HARNESS_FOLLOW_UP_RETRY", True),
            topic_draft=_flag("HARNESS_TOPIC_DRAFT", True),
            program_full_dates=_flag("HARNESS_PROGRAM_FULL_DATES", True),
            order_max_tokens=int(_env("HARNESS_ORDER_MAX_TOKENS", "16000")),
            finder_order=_flag("HARNESS_FINDER_ORDER", True),
            action_topic=_flag("HARNESS_ACTION_TOPIC", True),
            meaning_route=_flag("HARNESS_MEANING_ROUTE", True),
            meaning_sure=float(_env("HARNESS_MEANING_SURE", "0.8")),
            widen=_flag("HARNESS_WIDEN", True),
            widen_dense=int(_env("HARNESS_WIDEN_DENSE", "12")),
            widen_text=int(_env("HARNESS_WIDEN_TEXT", "8")),
            # the 20B model reads long prompts badly: widening only fills room inside the base packet budget
            widen_chars=int(_env("HARNESS_WIDEN_CHARS", "24000")),
            widen_anchored=_flag("HARNESS_WIDEN_ANCHORED", True),
            short_order_votes=int(_env("HARNESS_ORDER_VOTES", "3")),
            # refill: fill the base packet's own size from the fused order; swap: bring the top fused records into it;
            # widen: add records within widen_chars; off: base packet only
            select_mode=_env("HARNESS_SELECT", "refill").lower(),
            swap_top=int(_env("HARNESS_SWAP_TOP", "12")),
        )
