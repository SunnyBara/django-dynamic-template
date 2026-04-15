"""JSON export / import for :class:`~dynamic_template.models.DynamicTemplate` (+ relation contexts)."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

from django.apps import apps
from django.http import HttpResponse
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from dynamic_template.models import DynamicRelationContext, DynamicTemplate

EXPORT_FORMAT_VERSION = 1


def _split_ct(label: str) -> tuple[str, str]:
    label = str(label).strip()
    parts = label.split(".", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid content_type label {label!r} (expected app_label.model).")
    return parts[0], parts[1].lower()


def resolve_content_type(label: str) -> ContentType:
    app_label, model_name = _split_ct(label)
    Model = apps.get_model(app_label, model_name)
    if Model is None:
        raise ValueError(f"Unknown model {label!r}.")
    return ContentType.objects.get_for_model(Model, for_concrete_model=False)


def serialize_relation(rc: DynamicRelationContext) -> dict[str, Any]:
    return {
        "content_type": f"{rc.content_type.app_label}.{rc.content_type.model}",
        "manager_method": rc.manager_method,
        "filter_spec": rc.filter_spec or {},
        "filter_literal": rc.filter_literal or {},
        "model_fields": list(rc.model_fields) if rc.model_fields is not None else [],
        "annotate_fields": list(rc.annotate_fields) if rc.annotate_fields is not None else [],
        "fields": list(rc.fields) if rc.fields is not None else [],
        "name": rc.name,
    }


def serialize_template(dt: DynamicTemplate) -> dict[str, Any]:
    data: dict[str, Any] = {
        "label": dt.label,
        "named_id": dt.named_id,
        "content_type": f"{dt.content_type.app_label}.{dt.content_type.model}",
        "template": dt.template,
        "model_fields": list(dt.model_fields) if dt.model_fields is not None else [],
        "annotate_fields": list(dt.annotate_fields) if dt.annotate_fields is not None else [],
        "fields": list(dt.fields) if dt.fields is not None else [],
        "raw_object": dt.raw_object,
        "context_object": dt.context_object or "",
        "relation_contexts": [serialize_relation(r) for r in dt.relation_contexts.all()],
    }
    return data


def serialize_export(qs) -> dict[str, Any]:
    templates = []
    for dt in qs.order_by("pk").select_related("content_type").prefetch_related(
        "relation_contexts", "relation_contexts__content_type"
    ):
        templates.append(serialize_template(dt))
    return {
        "format_version": EXPORT_FORMAT_VERSION,
        "dynamic_templates": templates,
    }


def content_disposition_attachment(filename: str) -> str:
    """``Content-Disposition`` with ASCII ``filename`` and RFC 5987 ``filename*`` when needed."""
    try:
        filename.encode("ascii")
    except UnicodeEncodeError:
        pass
    else:
        return f'attachment; filename="{filename}"'
    ascii_fallback = filename.encode("ascii", "replace").decode("ascii").replace("?", "_")
    quoted = quote(filename, safe="")
    return f'attachment; filename="{ascii_fallback}"; filename*=UTF-8\'\'{quoted}'


def json_attachment_response(filename: str, payload: dict[str, Any]) -> HttpResponse:
    body = (
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")
    response = HttpResponse(body, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = content_disposition_attachment(filename)
    return response


def import_payload(data: dict[str, Any], *, replace: bool = True) -> dict[str, Any]:
    version = data.get("format_version", 1)
    if version != EXPORT_FORMAT_VERSION:
        raise ValueError(f"Unsupported format_version {version!r} (expected {EXPORT_FORMAT_VERSION}).")
    items = data.get("dynamic_templates") or data.get("templates")
    if not isinstance(items, list):
        raise ValueError("Expected a JSON object with key 'dynamic_templates' (array).")
    created = 0
    updated = 0
    errors: list[str] = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"#{idx}: not an object")
            continue
        try:
            with transaction.atomic():
                c, u = _import_one_template(item, replace=replace)
                created += c
                updated += u
        except (ValueError, TypeError, KeyError, ContentType.DoesNotExist) as exc:
            errors.append(f"#{idx} ({item.get('label', '?')}): {exc}")
    return {"created": created, "updated": updated, "errors": errors}


def _import_one_template(item: dict[str, Any], *, replace: bool) -> tuple[int, int]:
    label = str(item.get("label", "")).strip()
    if not label:
        raise ValueError("label is required")
    ct = resolve_content_type(item["content_type"])
    template_body = item.get("template", "") or ""
    model_fields = item.get("model_fields") or []
    annotate_fields = item.get("annotate_fields") or []
    fields = item.get("fields") or []

    if not isinstance(model_fields, list):
        raise ValueError("model_fields must be a list")
    if not isinstance(annotate_fields, list):
        raise ValueError("annotate_fields must be a list")
    if not isinstance(fields, list):
        raise ValueError("fields must be a list")

    raw_object = bool(item.get("raw_object", False))
    context_object = str(item.get("context_object", "") or "").strip()

    dt = DynamicTemplate.objects.filter(content_type=ct, label=label).first()
    if dt:
        if not replace:
            return (0, 0)
        dt.template = template_body
        dt.model_fields = model_fields
        dt.annotate_fields = annotate_fields
        dt.fields = fields
        dt.raw_object = raw_object
        dt.context_object = context_object
        dt.save()
        DynamicRelationContext.objects.filter(dynamic_template=dt).delete()
        updated = 1
        created = 0
    else:
        dt = DynamicTemplate.objects.create(
            label=label,
            content_type=ct,
            template=template_body,
            model_fields=model_fields,
            annotate_fields=annotate_fields,
            fields=fields,
            raw_object=raw_object,
            context_object=context_object,
        )
        created, updated = 1, 0

    rels = item.get("relation_contexts") or []
    if not isinstance(rels, list):
        raise ValueError("relation_contexts must be a list")
    for rel in rels:
        if not isinstance(rel, dict):
            raise ValueError("Each relation_context must be an object")
        r_ct = resolve_content_type(rel["content_type"])
        DynamicRelationContext.objects.create(
            dynamic_template=dt,
            content_type=r_ct,
            manager_method=str(rel.get("manager_method") or "objects.all"),
            filter_spec=rel.get("filter_spec") or {},
            filter_literal=rel.get("filter_literal") or {},
            model_fields=rel.get("model_fields") or [],
            annotate_fields=rel.get("annotate_fields") or [],
            fields=rel.get("fields") or [],
            name=str(rel.get("name", "")).strip(),
        )
    return (created, updated)
