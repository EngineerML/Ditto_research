"""Faithful catalog serialization and existing argument-shape checks."""
from __future__ import annotations

from typing import Any
from app.llm import ChatResult
from app.protocol import ToolDefinition


MISSING_ARGS_NOTE = "Call not sent: {name} needs {missing}. Send it again with each of those filled from the request, the records or earlier results."
BAD_TYPE_NOTE = "Call not sent: {name} argument {problems}. Send it again with arguments shaped as the schema states."
PROVIDER_SHAPE_NOTE = "The call you sent could not be delivered because its arguments did not fit the schema. The provider reported: {message}. Send it again with every argument in the shape the schema states, and leave an optional field out rather than setting it to null."
PROVIDER_MESSAGE_CHARS = 400


def unfilled(value: Any) -> bool:
    if isinstance(value, list):
        return bool(value) and all(item == "" for item in value)
    return value in ("", None)


def missing_required(args: dict[str, Any], required: list[str]) -> list[str]:
    # JSON Schema's required keyword checks presence, not truthiness or meaning.
    return [key for key in required if key not in args]


JSON_TYPES = {"string": str, "integer": int, "number": (int, float), "boolean": bool, "array": list, "object": dict, "null": type(None)}


def matches_type(value: Any, kind: Any) -> bool:
    if isinstance(kind, list):
        return any(matches_type(value, member) for member in kind)
    expected = JSON_TYPES.get(str(kind))
    if expected is None:
        return True  # No declared primitive type to enforce here.
    if kind in ("integer", "number") and isinstance(value, bool):
        return False
    if kind == "integer" and isinstance(value, float):
        return value.is_integer()
    return isinstance(value, expected)


def type_problems(args: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for key, value in args.items():
        spec = (schema.get("properties") or {}).get(key)
        if not isinstance(spec, dict):
            continue
        if not matches_type(value, spec.get("type")):
            problems.append(f"{key} must be {spec.get('type')}")
            continue
        if not isinstance(value, list):
            continue
        item_spec = spec.get("items")
        if isinstance(item_spec, dict) and any(not matches_type(item, item_spec.get("type")) for item in value):
            problems.append(f"{key} must be an array of {spec['items']['type']} values")
    return problems


def shape_rejection(result: ChatResult) -> str:
    if result.finish_reason != "error" or not result.error or result.tool_calls or result.content.strip():
        return ""
    message = " ".join(str(result.error.get("message") or "").split())
    if "schema" not in message.lower() and "validation" not in message.lower():
        return ""
    return message[:PROVIDER_MESSAGE_CHARS]


def openai_tools(defs: list[ToolDefinition]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for d in defs:
        parameters = d.parameters if isinstance(d.parameters, dict) else {"type": "object", "properties": {}}
        out.append({"type": "function", "function": {"name": d.name, "description": d.description, "parameters": parameters}})
    return out
