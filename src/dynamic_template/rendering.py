"""Render :class:`~dynamic_template.models.DynamicTemplate` fragments (shared by tag and admin)."""

from __future__ import annotations

from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.template import engines

from dynamic_template.models import DynamicTemplate


def render_dynamic_template_fragment(
    dt: DynamicTemplate,
    *,
    request=None,
    bound: models.Model | None = None,
    base_context: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    """
    Evaluate ``dt.template`` with optional ``object`` (*bound*), relation contexts, and context merges.

    Raises ``ValueError`` if *bound* is not compatible with ``dt.content_type``.
    """
    if bound is not None:
        if not hasattr(bound, "_meta"):
            raise ValueError("bound must be a model instance")
        ct = ContentType.objects.get_for_model(bound, for_concrete_model=False)
        if ct != dt.content_type:
            raise ValueError("bound model does not match template content type")

    engine = engines["django"]
    tpl = engine.from_string(dt.template)

    render_ctx: dict[str, Any] = dict(base_context or {})
    if extra:
        render_ctx.update(extra)
    if bound is not None:
        render_ctx["object"] = bound

    for rel_ctx in dt.relation_contexts.select_related("content_type").all():
        render_ctx[rel_ctx.name] = rel_ctx.get_queryset(render_ctx, request)

    if bound is not None:
        render_ctx["object"] = bound if dt.raw_object else dt.freeze_bound_for_fragment(bound)

    return tpl.render(render_ctx, request)
