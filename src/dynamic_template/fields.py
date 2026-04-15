"""Model fields; rich-text widget is chosen via ``DYNAMIC_TEMPLATE_RICHTEXT_WIDGET`` (like django-pymissive)."""

from __future__ import annotations

from typing import Any

from django.db import models


class RichTextField(models.TextField):
    """``TextField`` whose ModelForm/admin widget is configurable in settings."""

    def formfield(self, **kwargs: Any) -> Any:
        from django.conf import settings
        from django.utils.module_loading import import_string

        widget_path = getattr(
            settings,
            "DYNAMIC_TEMPLATE_RICHTEXT_WIDGET",
            "django.forms.Textarea",
        )
        widget_class = import_string(widget_path)
        kwargs.setdefault("widget", widget_class)
        return super().formfield(**kwargs)
