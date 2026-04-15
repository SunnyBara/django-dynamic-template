from __future__ import annotations

from django.db import models


def values_list_field_names(raw: list | tuple | None, model: type[models.Model]) -> list[str]:
    """ORM field names for ``values_list`` / fragment ``object`` (empty *raw* → all concrete fields)."""
    if not isinstance(raw, (list, tuple)):
        raw = []
    names = [str(f).strip() for f in raw if str(f).strip()]
    if not names:
        names = [f.name for f in model._meta.concrete_fields]
    return names


def mapping_from_row(names: list[str], row) -> dict[str, object]:
    """One ``values_list`` row as ``{field_name: value, ...}`` (``row`` scalar if a single name)."""
    if len(names) == 1:
        return {names[0]: row}
    return dict(zip(names, row))


def json_str_list(raw: list | tuple | None) -> list[str]:
    if not isinstance(raw, (list, tuple)):
        return []
    return [str(x).strip() for x in raw if str(x).strip()]
