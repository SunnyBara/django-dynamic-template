"""Resolve ``DynamicRelationContext.filter_spec`` (object/context side) for ``.filter()``."""

from __future__ import annotations

from typing import Any, Mapping

from django.http import HttpRequest
from django.template import engines


def resolve_filter_value(
    raw: Any,
    context: Mapping[str, Any],
    request: HttpRequest | None = None,
) -> Any:
    if raw is None:
        return None
    if not isinstance(raw, str):
        return raw
    s = raw.strip()
    if "{{" in s or "{%" in s:
        return engines["django"].from_string(s).render(context, request).strip()
    return _resolve_dotted_from_object(s, context)


def _resolve_dotted_from_object(path: str, context: Mapping[str, Any]) -> Any:
    """Walk ``path`` as attributes starting from ``context[\"object\"]`` (the ``obj=`` bound instance)."""
    root = context.get("object")
    if root is None:
        return None
    parts = path.split(".")
    if not parts or not parts[0]:
        return None
    cur: Any = root
    for part in parts:
        if cur is None:
            return None
        cur = getattr(cur, part, None)
    return cur


def build_filter_kwargs(
    filter_spec: Mapping[str, Any],
    context: Mapping[str, Any],
    request: HttpRequest | None = None,
) -> dict[str, Any]:
    return {str(k): resolve_filter_value(v, context, request) for k, v in filter_spec.items()}
