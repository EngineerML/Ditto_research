from __future__ import annotations

import os
from dataclasses import dataclass, replace


def _env(name: str, default: str = "") -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip()


@dataclass(frozen=True)
class Settings:
    provider: str
    model: str
    openrouter_api_key: str
    openrouter_base_url: str
    openai_base_url: str
    openai_api_key: str
    platform_base_url: str
    ollama_base_url: str
    db_path: str
    inference_base_url: str = ""
    reasoning_effort: str = "medium"
    log_level: str = "INFO"
    case_budget_seconds: float = 285.0
    packet_char_budget: int = 24000
    llm_timeout_seconds: float = 100.0
    llm_max_attempts: int = 2
    tool_timeout_seconds: float = 20.0
    max_model_turns: int = 12
    max_output_tokens: int = 6000
    max_inflight_calls: int = 4
    action_max_turns: int = 8
    action_max_tokens: int = 6000
    action_reasoning_effort: str = "medium"
    recall_max_tokens: int = 2000
    recall_reasoning_effort: str = "low"
    records_reasoning_effort: str = "medium"
    sampling_temperature: float = 0.0
    sampling_seed: int = 42
    coverage_floor: int = 3
    long_packet_chars: int = 30000
    embed_timeout_seconds: float = 30.0
    meaning_records: int = 5
    meaning_chars: int = 6000
    search_record_chars: int = 7000
    search_long_records: int = 2
    search_passes: int = 2
    search_temperature: float = 0.7
    short_max_chars: int = 30000
    short_effort: str = "medium"
    short_max_tokens: int = 12000
    story_max_chars: int = 30000
    story_min_density: int = 3
    identifier_search_passes: int = 2
    alias_pass: bool = True
    alias_names_only: bool = True
    follow_up: bool = False
    final_check: bool = True
    name_chain: bool = True

    @classmethod
    def from_env(cls) -> "Settings":
        settings = cls(
            provider=_env("DITTOBENCH_PROVIDER", "openrouter").lower(),
            model=_env("DITTOBENCH_MODEL", "openai/gpt-oss-20b"),
            openrouter_api_key=_env("OPENROUTER_API_KEY"),
            openrouter_base_url=_env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            openai_base_url=_env("OPENAI_BASE_URL"),
            openai_api_key=_env("OPENAI_API_KEY"),
            platform_base_url=_env("DITTOBENCH_INFERENCE_BASE_URL") or _env("CHUTES_BASE_URL") or _env("OPENAI_BASE_URL") or _env("OPENROUTER_BASE_URL"),
            ollama_base_url=_env("OLLAMA_BASE_URL", "http://localhost:11434"),
            db_path=_env("DITTOBENCH_DB", "/tmp/dittobench.db"),
            inference_base_url=_env("DITTOBENCH_INFERENCE_BASE_URL"),
        )
        # HARNESS_<FIELD> overrides one of the tuning fields; unset keeps the default above.
        changes: dict[str, object] = {}
        for name in TUNABLE:
            raw = _env("HARNESS_" + name.upper())
            if not raw:
                continue
            default = getattr(settings, name)
            if isinstance(default, bool):
                changes[name] = raw.lower() not in {"0", "false", "no", "off"}
            elif isinstance(default, int):
                changes[name] = int(raw)
            else:
                changes[name] = raw
        return replace(settings, **changes) if changes else settings


TUNABLE = (
    "packet_char_budget", "long_packet_chars", "max_model_turns", "max_output_tokens", "records_reasoning_effort",
    "action_reasoning_effort", "short_effort", "short_max_chars", "story_max_chars", "meaning_records", "meaning_chars",
    "search_passes", "identifier_search_passes", "alias_pass", "alias_names_only", "follow_up", "final_check",
    "name_chain",
)
