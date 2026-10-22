"""Per-case outcome and token accounting shared by execution engines."""
from __future__ import annotations

from dataclasses import dataclass, field
from app.llm import ChatResult, Usage


@dataclass
class TokenTally:
    prompt: int = 0
    output: int = 0

    def add(self, result: ChatResult | Usage) -> None:
        self.prompt += result.prompt_tokens
        self.output += result.completion_tokens


@dataclass
class Outcome:
    content: str = ""
    host_calls: int = 0
    memory_calls: int = 0
    answer: str | None = None
    model_calls: int = 0
    events: list[str] = field(default_factory=list)
