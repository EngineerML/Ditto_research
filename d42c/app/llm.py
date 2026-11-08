from __future__ import annotations

import asyncio
import json
import logging
import time
import weakref
from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import Settings

log = logging.getLogger("harness.llm")


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]
    raw_arguments: str = ""
    unreadable_arguments: str = ""


@dataclass
class ChatResult:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = ""
    raw_message: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(self.prompt_tokens + other.prompt_tokens, self.completion_tokens + other.completion_tokens)


def _as_whole_number(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def usage_of(body: Any) -> Usage:
    usage = body.get("usage") if isinstance(body, dict) else None
    if not isinstance(usage, dict):
        return Usage()
    return Usage(_as_whole_number(usage.get("prompt_tokens")), _as_whole_number(usage.get("completion_tokens")))


class LLMError(RuntimeError):
    def __init__(self, message: str, usage: Usage = Usage()) -> None:
        super().__init__(message)
        self.usage = usage


class LLM:
    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None, *, deadline: float, max_tokens: int | None = None, reasoning_effort: str | None = None, temperature: float | None = None, seed: int | None = None, tool_choice: str | None = None, once: bool = False) -> ChatResult:
        raise NotImplementedError

    async def aclose(self) -> None:
        return None


def wire_body(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode("ascii")


def _sendable(value: dict[str, Any]) -> bool:
    try:
        json.dumps(value, allow_nan=False, ensure_ascii=False).encode("utf-8")
    except ValueError:
        return False
    return True


def _parse_args(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        if _sendable(raw):
            return raw
        log.warning("tool arguments carry a value JSON cannot hold, call not sent: %r", raw)
        return None
    if not (isinstance(raw, str) and raw.strip()) or raw.strip() == "null":
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        parsed = None
    if isinstance(parsed, dict) and _sendable(parsed):
        return parsed
    log.warning("unparsable tool arguments, call not sent: %r", raw.strip()[:300])
    return None


PROVIDER_REJECTION_MARKERS = ("tool call validation failed", "schema", "tool choice is none", "failed to parse tool call arguments")


def provider_rejected_the_call(error: dict[str, Any]) -> bool:
    message = str(error.get("message") or "").lower()
    return any(marker in message for marker in PROVIDER_REJECTION_MARKERS)


def parse_chat_completion(body: Any) -> ChatResult:
    if not isinstance(body, dict):
        raise LLMError(f"completion body is not a JSON object: {str(body)[:300]}")
    usage = usage_of(body)
    choices = body.get("choices") or []
    if not choices:
        error = body.get("error")
        if isinstance(error, dict) and provider_rejected_the_call(error):
            return ChatResult(content="", finish_reason="error", error=error, prompt_tokens=usage.prompt_tokens, completion_tokens=usage.completion_tokens)
        raise LLMError(f"no choices in completion: {json.dumps(body)[:300]}")
    choice = choices[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    calls: list[ToolCall] = []
    for index, call in enumerate(message.get("tool_calls") or []):
        function = call.get("function") or {}
        name = function.get("name") or ""
        if not name:
            log.warning("tool call %d came without a name, not run: blocked_before_execution", index)
            continue
        raw_arguments = function.get("arguments")
        parsed = _parse_args(raw_arguments)
        calls.append(ToolCall(id=call.get("id") or f"call_{index}", name=name, args=parsed or {}, raw_arguments=raw_arguments if isinstance(raw_arguments, str) else "", unreadable_arguments="" if parsed is not None else str(raw_arguments)))
    served_by = body.get("provider")
    if isinstance(served_by, str) and served_by:
        log.info("llm provider=%s model=%s", served_by, body.get("model"))
    return ChatResult(
        content=content or "",
        tool_calls=calls,
        prompt_tokens=usage.prompt_tokens,
        completion_tokens=usage.completion_tokens,
        finish_reason=choice.get("finish_reason") or "",
        raw_message=message,
        error=choice.get("error") if isinstance(choice.get("error"), dict) else None,
    )


MAX_CAPACITY_WAITS = 30
RELAY_PROVIDER_PREFERENCES = {"sort": "throughput", "ignore": ["coreweave"], "allow_fallbacks": False, "data_collection": "deny", "zdr": True}
CLIENT_RESET_AFTER_FAILURES = 3
POOL_LIMITS = httpx.Limits(max_connections=16, max_keepalive_connections=0)
RETRY_TOKEN_FACTOR = 0.4
MIN_RETRY_TOKENS = 1200
DEFAULT_RETRY_AFTER = 1.0
MAX_RETRY_AFTER = 5.0
QUICK_FAILURE_SECONDS = 5.0
MAX_BACKOFF = 4.0
MAX_RETRY_SLEEP = 20.0
_gates: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, tuple[asyncio.Semaphore, list[int]]]" = weakref.WeakKeyDictionary()


def call_gate(limit: int) -> asyncio.Semaphore:
    loop = asyncio.get_running_loop()
    entry = _gates.get(loop)
    if entry is None:
        entry = (asyncio.Semaphore(max(1, limit)), [max(1, limit)])
        _gates[loop] = entry
    return entry[0]


def grow_call_gate(limit: int) -> int:
    loop = asyncio.get_running_loop()
    entry = _gates.get(loop)
    if entry is None:
        call_gate(limit)
        return max(1, limit)
    gate, current = entry
    while current[0] < limit:
        current[0] += 1
        gate.release()
    return current[0]


def at_capacity(response: httpx.Response) -> bool:
    return response.status_code == 429 or (response.status_code == 503 and "Retry-After" in response.headers)


def response_body(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def retry_after_seconds(header: str | None) -> float:
    try:
        return min(MAX_RETRY_AFTER, max(0.0, float(header)))
    except (TypeError, ValueError):
        return DEFAULT_RETRY_AFTER


class OpenAICompatLLM(LLM):
    def __init__(self, base_url: str, api_key: str, model: str, *, timeout_seconds: float, max_attempts: int, extra_headers: dict[str, str] | None = None, client: httpx.AsyncClient | None = None, reasoning_effort: str = "", reasoning_style: str = "openai", max_inflight: int = 4, temperature: float = 0.0, seed: int = 42) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.reasoning_effort = reasoning_effort if reasoning_effort in {"low", "medium", "high"} else ""
        self.temperature = temperature
        self.seed = seed
        self.reasoning_style = reasoning_style
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max(1, max_attempts)
        self.max_inflight = max(1, max_inflight)
        self.headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if extra_headers:
            self.headers.update(extra_headers)
        self._owns_client = client is None
        self._client = client or self._new_client()
        self._consecutive_failures = 0

    @staticmethod
    def _new_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(limits=POOL_LIMITS, timeout=httpx.Timeout(60.0, connect=10.0, pool=10.0))

    async def _replace_client(self) -> None:
        if not self._owns_client:
            return
        log.error("llm client wedged after %d consecutive transport failures, rebuilding it", self._consecutive_failures)
        stale, self._client = self._client, self._new_client()
        self._consecutive_failures = 0
        try:
            await asyncio.wait_for(stale.aclose(), timeout=5)
        except Exception:
            log.warning("stale llm client did not close cleanly")

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]] | None, *, deadline: float, max_tokens: int | None = None, reasoning_effort: str | None = None, temperature: float | None = None, seed: int | None = None, tool_choice: str | None = None, once: bool = False) -> ChatResult:
        payload: dict[str, Any] = {"model": self.model, "messages": messages, "temperature": self.temperature if temperature is None else temperature, "seed": self.seed if seed is None else seed}
        effort = reasoning_effort if reasoning_effort in {"low", "medium", "high"} else self.reasoning_effort
        if effort:
            if self.reasoning_style == "openrouter":
                payload["reasoning"] = {"effort": effort, "exclude": True}
            else:
                payload["reasoning_effort"] = effort
        if self.reasoning_style == "openrouter":
            payload["provider"] = RELAY_PROVIDER_PREFERENCES
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"
        if max_tokens:
            payload["max_tokens"] = max_tokens
        last_error: Exception | None = None
        attempt = 0
        quick_failures = 0
        slept = 0.0
        capacity_waits = 0
        spent = Usage()
        while attempt < self.max_attempts:
            remaining = deadline - time.monotonic()
            if remaining <= 1:
                break
            gate = call_gate(self.max_inflight)
            try:
                await asyncio.wait_for(gate.acquire(), timeout=remaining - 0.5)
            except (asyncio.TimeoutError, TimeoutError):
                raise LLMError("no free inference slot before the deadline", spent)
            response: httpx.Response | None = None
            sent_at = time.monotonic()
            try:
                timeout = min(self.timeout_seconds, max(1.0, deadline - time.monotonic()))
                response = await asyncio.wait_for(self._client.post(f"{self.base_url}/chat/completions", headers=self.headers, content=wire_body(payload), timeout=timeout), timeout=timeout)
            except (httpx.TimeoutException, httpx.TransportError, asyncio.TimeoutError) as exc:
                timed_out = isinstance(exc, (httpx.TimeoutException, asyncio.TimeoutError))
                if timed_out or time.monotonic() - sent_at >= QUICK_FAILURE_SECONDS:
                    attempt += 1
                else:
                    quick_failures += 1
                last_error = exc
                self._consecutive_failures += 1
                if self._consecutive_failures >= CLIENT_RESET_AFTER_FAILURES:
                    await self._replace_client()
                if timed_out and payload.get("max_tokens"):
                    payload["max_tokens"] = max(MIN_RETRY_TOKENS, int(payload["max_tokens"] * RETRY_TOKEN_FACTOR))
                    log.warning("llm timed out, retrying with max_tokens=%d", payload["max_tokens"])
                log.warning("llm transport failure attempt=%d quick=%d err=%r", attempt, quick_failures, exc)
            finally:
                gate.release()
            if response is not None:
                body = response_body(response)
                if response.status_code == 200:
                    self._consecutive_failures = 0
                    try:
                        result = parse_chat_completion(body)
                    except (ValueError, LLMError) as exc:
                        spent += usage_of(body)
                        attempt += 1
                        last_error = exc
                        log.warning("llm bad body attempt=%d err=%r", attempt, exc)
                    else:
                        result.prompt_tokens += spent.prompt_tokens
                        result.completion_tokens += spent.completion_tokens
                        if not result.content and not result.tool_calls:
                            log.warning("llm empty content finish=%s completion_tokens=%d reasoning_chars=%d error=%r", result.finish_reason, result.completion_tokens, len(str(result.raw_message.get("reasoning_content") or result.raw_message.get("reasoning") or "")), result.error)
                        return result
                else:
                    spent += usage_of(body)
                    if at_capacity(response) and capacity_waits < MAX_CAPACITY_WAITS and not once:
                        capacity_waits += 1
                        last_error = LLMError(f"llm http {response.status_code}: {response.text[:300]}")
                        pause = min(retry_after_seconds(response.headers.get("Retry-After")), max(0.0, deadline - time.monotonic() - 1))
                        log.info("llm source at capacity, waiting %.1fs (wait %d)", pause, capacity_waits)
                        if pause > 0:
                            await asyncio.sleep(pause)
                        continue
                    if response.status_code in (408, 409, 425, 429) or response.status_code >= 500:
                        if time.monotonic() - sent_at < QUICK_FAILURE_SECONDS:
                            quick_failures += 1
                        else:
                            attempt += 1
                        last_error = LLMError(f"llm http {response.status_code}: {response.text[:300]}")
                        log.warning("llm retryable status=%d attempt=%d quick=%d", response.status_code, attempt, quick_failures)
                    else:
                        raise LLMError(f"llm http {response.status_code}: {response.text[:300]}", spent)
            if once or attempt >= self.max_attempts:
                break
            backoff = min(MAX_BACKOFF, 0.5 * (2 ** (attempt + quick_failures)), max(0.0, deadline - time.monotonic() - 1))
            if slept + backoff > MAX_RETRY_SLEEP:
                break
            if backoff > 0:
                slept += backoff
                await asyncio.sleep(backoff)
        raise LLMError(f"llm exhausted attempts: {last_error!r}", spent)


KNOWN_PROVIDERS = frozenset({"openrouter", "platform", "chutes", "ollama", "openai"})


def build_llm(settings: Settings, inference_base_url: str | None = None, *, client: httpx.AsyncClient | None = None) -> LLM:
    common = dict(timeout_seconds=settings.llm_timeout_seconds, max_attempts=settings.llm_max_attempts, client=client, max_inflight=settings.max_inflight_calls, temperature=settings.sampling_temperature, seed=settings.sampling_seed)
    if inference_base_url and inference_base_url.strip():
        return OpenAICompatLLM(inference_base_url.strip(), "ticket", settings.model, **common)
    if settings.provider in {"platform", "chutes"} or settings.provider not in KNOWN_PROVIDERS:
        if not settings.platform_base_url:
            raise LLMError(f"no inference base url for provider {settings.provider!r}; set DITTOBENCH_INFERENCE_BASE_URL")
        return OpenAICompatLLM(settings.platform_base_url, "ticket", settings.model, **common)
    if settings.provider == "ollama":
        return OpenAICompatLLM(f"{settings.ollama_base_url.rstrip('/')}/v1", "ollama", settings.model, **common)
    if settings.provider == "openai":
        if not settings.openai_base_url or not settings.openai_api_key:
            raise LLMError("OPENAI_BASE_URL and OPENAI_API_KEY are required for the openai provider")
        return OpenAICompatLLM(settings.openai_base_url, settings.openai_api_key, settings.model, reasoning_effort=settings.reasoning_effort, reasoning_style="openai", **common)
    if not settings.openrouter_api_key:
        if settings.inference_base_url:
            return OpenAICompatLLM(settings.inference_base_url, "ticket", settings.model, **common)
        raise LLMError("OPENROUTER_API_KEY is not set")
    return OpenAICompatLLM(settings.openrouter_base_url, settings.openrouter_api_key, settings.model, extra_headers={"HTTP-Referer": "https://heyditto.ai", "X-Title": "Ditto"}, reasoning_effort=settings.reasoning_effort, reasoning_style="openrouter", **common)
