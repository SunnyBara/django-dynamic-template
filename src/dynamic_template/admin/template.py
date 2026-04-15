import json

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django_boosted import AdminBoostModel, admin_boost_view
from django_boosted.decorators import AdminBoostViewConfig

from .relation_context import DynamicRelationContextInline
from dynamic_template.io import import_payload, json_attachment_response, serialize_export
from dynamic_template.models import DynamicTemplate
from dynamic_template.rendering import render_dynamic_template_fragment


def _preview_form_for_template(obj: DynamicTemplate) -> type[forms.Form]:
    Model = obj.content_type.model_class()
    model_label = Model._meta.label if Model else "?"

    class DynamicTemplatePreviewForm(forms.Form):
        object_id = forms.CharField(
            label=_("Object primary key"),
            required=False,
            help_text=_(
                "Primary key of a %(model)s instance for relation filters and for `object` in the fragment "
                "(after relation contexts, `object` is a dict from model_fields / annotate_fields / fields). "
                "Leave empty if the fragment does not use `object`."
            )
            % {"model": model_label},
        )

    return DynamicTemplatePreviewForm


class DynamicTemplateImportForm(forms.Form):
    file = forms.FileField(label=_("JSON file"), required=False)
    payload = forms.CharField(
        label=_("Or paste JSON"),
        widget=forms.Textarea(attrs={"rows": 24, "cols": 100, "class": "vLargeTextField"}),
        required=False,
    )
    replace = forms.BooleanField(
        label=_("Replace existing templates (same content type + label)"),
        required=False,
        initial=True,
    )

    def clean(self):
        cleaned = super().clean()
        file = cleaned.get("file")
        text = (cleaned.get("payload") or "").strip()
        raw: str | None = None
        if file:
            data = file.read()
            raw = data.decode("utf-8") if isinstance(data, bytes) else str(data)
        elif text:
            raw = text
        if not raw:
            raise forms.ValidationError(_("Provide a JSON file or paste JSON."))
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise forms.ValidationError(str(exc)) from exc
        if not isinstance(parsed, dict):
            raise forms.ValidationError(_("Root JSON value must be an object."))
        cleaned["parsed"] = parsed
        return cleaned


@admin.register(DynamicTemplate)
class DynamicTemplateAdmin(AdminBoostModel):
    list_display = ("label", "named_id", "content_type", "relation_context_count_display")
    list_filter = ("content_type",)
    search_fields = ("label", "named_id", "template")
    readonly_fields = ("named_id",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "label",
                    "named_id",
                    "content_type",
                    "model_fields",
                    "annotate_fields",
                    "fields",
                    "raw_object",
                    "context_object",
                    "template",
                ),
            },
        ),
    )
    inlines = (DynamicRelationContextInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).with_relation_context_count()

    @admin.display(
        ordering="relation_context_count",
        description=_("Relation contexts"),
    )
    def relation_context_count_display(self, obj):
        return getattr(obj, "relation_context_count", 0)

    @admin_boost_view(
        "adminform",
        _("Import JSON"),
        config=AdminBoostViewConfig(
            path_fragment="import-json",
            requires_object=False,
            permission="change",
        ),
    )
    def admin_import_json(self, request, form=None):
        if not self.has_change_permission(request):
            raise PermissionDenied
        if form is None:
            return {"form": DynamicTemplateImportForm()}
        result = import_payload(
            form.cleaned_data["parsed"],
            replace=form.cleaned_data.get("replace", True),
        )
        messages.success(
            request,
            _("Import finished: %(c)d created, %(u)d updated.")
            % {"c": result["created"], "u": result["updated"]},
        )
        for err in result["errors"][:25]:
            messages.warning(request, err)
        url = reverse(
            f"admin:{self.model._meta.app_label}_{self.model._meta.model_name}_changelist",
            current_app=self.admin_site.name,
        )
        return {"redirect_url": url}

    @admin_boost_view(
        "json",
        _("Export JSON (all)"),
        config=AdminBoostViewConfig(
            path_fragment="export-json-bulk",
            requires_object=False,
            permission="view",
        ),
    )
    def admin_export_json_bulk(self, request):
        qs = self.get_queryset(request).prefetch_related("relation_contexts")
        return json_attachment_response("dynamic-templates.json", serialize_export(qs))

    @admin_boost_view(
        "json",
        _("Export JSON"),
        config=AdminBoostViewConfig(
            path_fragment="export-json",
            requires_object=True,
            permission="view",
        ),
    )
    def admin_export_json_single(self, request, obj):
        payload = serialize_export(
            DynamicTemplate.objects.filter(pk=obj.pk).prefetch_related("relation_contexts"),
        )
        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in obj.named_id)[:80]
        return json_attachment_response(
            f"dynamic-template-{obj.pk}-{safe}.json",
            payload,
        )

    @admin_boost_view(
        "adminform",
        _("Preview fragment"),
        config=AdminBoostViewConfig(
            template_name="dynamic_template/admin/preview_render.html",
            path_fragment="preview-render",
            permission="change",
        ),
    )
    def admin_preview_render(self, request, obj, form=None):
        PreviewForm = _preview_form_for_template(obj)
        Model = obj.content_type.model_class()

        if form is None:
            return {"form": PreviewForm()}

        bound = None
        oid = (form.cleaned_data.get("object_id") or "").strip()
        if oid:
            if Model is None:
                form.add_error("object_id", _("Unknown content type."))
            else:
                try:
                    bound = Model.objects.get(pk=oid)
                except (Model.DoesNotExist, ValueError, TypeError):
                    form.add_error(
                        "object_id",
                        _("No %(model)s found with this primary key.")
                        % {"model": Model._meta.verbose_name},
                    )

        if form.errors:
            return {"form": form}

        try:
            html = render_dynamic_template_fragment(
                obj,
                request=request,
                bound=bound,
                base_context={},
                extra={},
            )
        except ValueError as exc:
            form.add_error(None, str(exc))
            return {"form": form}

        return {"form": form, "rendered_preview": html}
