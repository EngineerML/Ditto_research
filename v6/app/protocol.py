from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


LOCAL_PAIR_PREFIX = "saved-"


def handed_out(pair_id: str) -> bool:
    return not pair_id.startswith(LOCAL_PAIR_PREFIX)


class Wire(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class ToolDefinition(Wire):
    name: str
    description: str = ""
    parameters: dict[str, Any] | None = None


class RunRequest(Wire):
    case_id: str
    system_prompt: str = ""
    user_input: str
    tools: list[ToolDefinition] = Field(default_factory=list)
    tool_endpoint: str | None = None
    user_id: str | None = None
    inference_base_url: str | None = None


class ObservedToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    hop: int = 0


class RunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    final_text: str
    tool_calls: list[ObservedToolCall] = Field(default_factory=list)
    prompt_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    answer: str | None = None

    def wire(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "final_text": self.final_text,
            "tool_calls": [call.model_dump() for call in self.tool_calls],
            "prompt_tokens": self.prompt_tokens,
            "output_tokens": self.output_tokens,
            "latency_ms": self.latency_ms,
        }
        if self.answer is not None:
            body["answer"] = self.answer.strip()
        return body


class MemoryPair(Wire):
    pair_id: str
    session_id: str = ""
    timestamp: str = ""
    prompt: str = ""
    response: str = ""


class Subject(Wire):
    id: str
    subject_text: str = ""
    description_text: str = ""


class SubjectLink(Wire):
    subject_id: str
    pair_id: str


class SeedRequest(Wire):
    user_id: str | None = None
    pairs: list[MemoryPair] = Field(default_factory=list)
    subjects: list[Subject] = Field(default_factory=list)
    links: list[SubjectLink] = Field(default_factory=list)


class SeedResponse(BaseModel):
    pairs: int
    subjects: int
    links: int


class ToolExecRequest(BaseModel):
    case_id: str
    user_id: str | None = None
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    hop: int = 0


MEMORY_TOOL_NAMES = frozenset(
    {"search_memories", "search_subjects", "fetch_memories", "search_memories_in_subjects"}
)


def normalize_user_id(user_id: str | None) -> str:
    if user_id is None or not user_id.strip():
        return "default"
    return user_id
