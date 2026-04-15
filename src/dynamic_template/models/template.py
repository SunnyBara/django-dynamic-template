from __future__ import annotations

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import gettext_lazy as _
from namedid import NamedIDField

from dynamic_template.fields import RichTextField

from ._helpers import json_str_list, mapping_from_row, values_list_field_names


class DynamicTemplateQuerySet(models.QuerySet):
    def with_relation_context_count(self):
        """Annotate each row with ``relation_context_count`` (related ``DynamicRelationContext`` rows)."""
        return self.annotate(
            relation_context_count=models.Count("relation_contexts", distinct=True),
        )


DynamicTemplateManager = models.Manager.from_queryset(DynamicTemplateQuerySet)


class DynamicTemplate(models.Model):
    """
    Template fragment stored in the DB, scoped to a single ContentType.

    ``model_fields`` selects ORM columns; ``annotate_fields`` is a list of annotation **aliases**
    already present on the bound instance (your queryset / manager must call ``.annotate``).
    ``fields`` lists extra Python names via ``getattr``. ``object`` in the fragment is a **dict**.
    Relation contexts still see the real model instance until after they run.
    """

    objects = DynamicTemplateManager()

    label = models.CharField(
        _("label"),
        max_length=255,
        help_text=_("Human-readable name; used with NamedID to build `named_id`."),
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="dynamic_templates",
        verbose_name=_("content type"),
    )
    template = RichTextField(
        _("template"),
        help_text=_(
            "Django template language source rendered by the `dyntpl` tag. "
            "Admin widget: set DYNAMIC_TEMPLATE_RICHTEXT_WIDGET (import path to a Widget class)."
        ),
    )
    named_id = NamedIDField(
        source_fields=["label"],
        unique=["content_type"],
        max_length=255,
    )
    model_fields = models.JSONField(
        _("model fields"),
        default=list,
        blank=True,
        help_text=_(
            "ORM field names on ``object`` (empty → all concrete DB fields). "
            "Exposed as dict keys, e.g. ``{{ object.name }}``."
        ),
    )
    annotate_fields = models.JSONField(
        _("annotate fields"),
        default=list,
        blank=True,
        help_text=_(
            "Names of annotations to copy onto ``object`` (must already exist on the ``obj=`` "
            "instance, e.g. loaded via ``Model.objects.my_annotated_manager().get(...)``)."
        ),
    )
    fields = models.JSONField(
        _("fields"),
        default=list,
        blank=True,
        help_text=_(
            "Extra Python names merged into ``object`` via ``getattr(instance, name)``: "
            "``@property``, class attributes, or methods."
        ),
    )
    raw_object = models.BooleanField(
        _("raw object"),
        default=False,
        help_text=_(
            "When checked, ``object`` in the template is the real model instance "
            "instead of a serialized dict. Allows calling methods, traversing "
            "relations, etc. via ``{{ object.my_method }}``."
        ),
    )
    context_object = models.CharField(
        _("object from context"),
        max_length=255,
        blank=True,
        default="",
        help_text=_(
            "Dotted path to resolve ``object`` from the parent template context "
            "(e.g. ``meeting``, ``participant.meeting``). "
            "When set, ``obj=`` is no longer required in the template tag."
        ),
    )

    class Meta:
        verbose_name = _("dynamic template")
        verbose_name_plural = _("dynamic templates")
        indexes = [
            models.Index(fields=["content_type", "named_id"]),
        ]

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # NamedIDField is filled in pre_save but the in-memory instance is not updated (django-namedid).
        if self.pk:
            self.refresh_from_db(fields=["named_id"])

    def __str__(self) -> str:
        return f"{self.label} ({self.named_id})"

    def freeze_bound_for_fragment(self, instance: models.Model):
        """Build ``object`` as a field-name → value dict (no model instance in the fragment)."""
        model = instance.__class__
        names = values_list_field_names(self.model_fields, model)
        if not names:
            return instance
        prop_names = json_str_list(self.fields)
        ann_aliases = json_str_list(self.annotate_fields)

        if instance.pk is None or ann_aliases or prop_names:
            out = {n: getattr(instance, n, None) for n in names}
            for a in ann_aliases:
                out[a] = getattr(instance, a, None)
            for p in prop_names:
                out[p] = getattr(instance, p, None)
            return out

        qs = model.objects.filter(pk=instance.pk)
        if len(names) == 1:
            return mapping_from_row(names, qs.values_list(names[0], flat=True).first())
        row = qs.values_list(*names).first()
        if row is None:
            return {n: None for n in names}
        return mapping_from_row(names, row)
