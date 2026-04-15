from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _

from ._helpers import json_str_list, mapping_from_row, values_list_field_names
from .template import DynamicTemplate


class DynamicRelationContext(models.Model):
    """
    Dynamic relation context: load a related queryset when rendering a :class:`DynamicTemplate`.

    ``manager_method`` is a no-arg manager call: default ``objects.all`` → ``Model.objects.all()``,
    or e.g. ``objects.get_with_tva``. A bare name (legacy) still means a method on the
    **default** manager only, e.g. ``all`` → ``_default_manager.all()``.
    ``filter_spec`` (from the bound ``object`` / render context) and ``filter_literal``
    (hard-coded ORM kwargs) are merged, then applied as ``.filter(**merged)``.
    ``filter_spec`` values: dotted paths from ``object`` (e.g. ``product.pk``),
    mini-templates (``{{ site.pk }}``), or JSON literals for that side only.
    ``filter_literal`` is copied as-is (no resolution). If the same key appears in both,
    ``filter_spec`` wins.
    ``name`` is the context key for the queryset; if left blank it defaults to
    ``content_type.model`` (already lowercase in Django).
    ``model_fields`` selects ORM columns; ``annotate_fields`` lists annotation aliases already
    on the queryset from ``manager_method``; ``fields`` lists extra Python names per row.
    Each row is a **dict**;
    the injected value is an **immutable tuple** of dicts (``|length``, ``rows.0``).
    """

    dynamic_template = models.ForeignKey(
        DynamicTemplate,
        on_delete=models.CASCADE,
        related_name="relation_contexts",
        verbose_name=_("dynamic template"),
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="relation_context_loaders",
        verbose_name=_("related model"),
        help_text=_("Model whose manager will be used to build the queryset."),
    )
    manager_method = models.CharField(
        _("manager method"),
        max_length=128,
        default="objects.all",
        help_text=_(
            "`manager.method` with no arguments (default `objects.all`). "
            "Example: `objects.get_with_tva`. Legacy: a single name calls `_default_manager.<name>()`."
        ),
    )
    filter_spec = models.JSONField(
        _("filter (from object)"),
        default=dict,
        blank=True,
        help_text=_(
            "``.filter()`` kwargs with **resolved** values: dotted paths from ``object``, or "
            '``{{ }}`` / ``{% %}`` for the full render context, e.g. ``{"product_id": "pk"}``, '
            "``{\"site_id\": \"{{ site.pk }}\"}``. Non-string JSON values are ORM literals."
        ),
    )
    filter_literal = models.JSONField(
        _("filter (literal)"),
        default=dict,
        blank=True,
        help_text=_(
            "Static ``.filter()`` kwargs (exact ORM values, no ``object`` paths, no templates). "
            'Example: {"is_active": true, "role": "staff"}. Merged with filter (from object); '
            "object-based keys override the same key here."
        ),
    )
    model_fields = models.JSONField(
        _("model fields"),
        default=list,
        blank=True,
        help_text=_(
            "ORM columns per row (empty → all concrete). Dict keys in the fragment: "
            "``{{ row.name }}``. Example: `[\"id\", \"title\"]`."
        ),
    )
    annotate_fields = models.JSONField(
        _("annotate fields"),
        default=list,
        blank=True,
        help_text=_(
            "Annotation aliases already on the queryset returned by ``manager_method`` "
            "(e.g. ``[\"n_articles\"]``). This app does not call ``.annotate()`` for you."
        ),
    )
    fields = models.JSONField(
        _("fields"),
        default=list,
        blank=True,
        help_text=_(
            "Extra Python names per row via ``getattr(obj, name)``: properties, class attrs, methods."
        ),
    )
    name = models.CharField(
        _("name"),
        max_length=64,
        blank=True,
        help_text=_(
            "Variable injected into the fragment context. "
            "Leave blank to use the related model name (lowercase, e.g. article)."
        ),
    )

    class Meta:
        verbose_name = _("dynamic relation context")
        verbose_name_plural = _("dynamic relation contexts")
        constraints = [
            models.UniqueConstraint(
                fields=("dynamic_template", "name"),
                name="dynamic_template_relation_context_name_uniq",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.content_type_id:
            raw = (self.name or "").strip()
            self.name = self.content_type.model if not raw else raw
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.dynamic_template} → {self.content_type.model} ({self.name})"

    def get_queryset(self, render_context: dict, request=None):
        from django.core.exceptions import FieldError
        from django.http import HttpRequest

        from dynamic_template.resolve import build_filter_kwargs

        model = self.content_type.model_class()
        if model is None:
            return tuple()

        empty_result = ()
        spec = (self.manager_method or "").strip()
        qs = None
        if "." in spec:
            mgr_name, _, meth_name = spec.partition(".")
            if mgr_name and meth_name:
                manager = getattr(model, mgr_name, None)
                if manager is not None:
                    meth = getattr(manager, meth_name, None)
                    if meth is not None:
                        try:
                            qs = meth()
                        except TypeError:
                            qs = None
        else:
            manager = model._default_manager
            meth = getattr(manager, spec, None) if spec else None
            if meth is not None:
                try:
                    qs = meth()
                except TypeError:
                    qs = None
        if qs is None or not hasattr(qs, "filter"):
            return empty_result

        req = request if isinstance(request, HttpRequest) else None
        try:
            literal_kw = self._literal_filter_kwargs()
            from_object_kw = build_filter_kwargs(self.filter_spec or {}, render_context, req)
            merged = {**literal_kw, **from_object_kw}
            qs = qs.filter(**merged)
            ann_aliases = json_str_list(self.annotate_fields)
            model_names = values_list_field_names(self.model_fields, qs.model)
            prop_names = json_str_list(self.fields)

            if prop_names:
                return self._freeze_rows_from_instances(qs, model_names, ann_aliases, prop_names)

            all_names = model_names + ann_aliases
            if not all_names:
                return tuple()
            if len(all_names) == 1:
                flat = qs.values_list(all_names[0], flat=True)
                return tuple(mapping_from_row(all_names, s) for s in flat)
            return tuple(mapping_from_row(all_names, r) for r in qs.values_list(*all_names))
        except (TypeError, ValueError, FieldError):
            return empty_result

    def _literal_filter_kwargs(self) -> dict:
        raw = self.filter_literal
        if not isinstance(raw, dict):
            return {}
        return {str(k): v for k, v in raw.items()}

    def _freeze_rows_from_instances(
        self,
        qs,
        model_names: list[str],
        ann_aliases: list[str],
        prop_names: list[str],
    ):
        rows = []
        for obj in qs:
            d = {n: getattr(obj, n, None) for n in model_names}
            for a in ann_aliases:
                d[a] = getattr(obj, a, None)
            for p in prop_names:
                d[p] = getattr(obj, p, None)
            rows.append(d)
        return tuple(rows)
