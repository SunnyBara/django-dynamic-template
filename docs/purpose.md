## Project purpose

**django-dynamic-template** is a Django application that stores **small template fragments** (Django Template Language) in the database. Each fragment is scoped to a **`ContentType`** and addressed by a URL-safe **`named_id`** generated with **django-namedid** (`NamedIDField` from `label`).

Use cases: CMS-style embeds, per-model HTML blocks, A/B or per-tenant copy, without deploying code for every wording change.

## Core models

### `DynamicTemplate`

- **`content_type`**: which model `obj=` / admin preview must use.
- **`template`**: DTL source (richtext field; widget configurable via settings).
- **`named_id`**: read-only slug from `label`, unique per `content_type`.
- **`model_fields`**: list of ORM field names loaded for **`object`** (empty → all concrete DB fields). Values end up as keys on the **`object`** dict.
- **`annotate_fields`**: JSON **list** of annotation **names** already present on the **`obj=`** instance (your view/queryset must call `.annotate` before passing the instance). Values are copied with `getattr`. This app does **not** generate annotations.
- **`fields`**: list of extra Python names resolved with **`getattr(instance, name)`** on the bound model (`@property`, class attributes, methods). Merged into **`object`**.
- **`raw_object`**: boolean (default `False`). When `True`, **`object`** in the fragment is the real model instance instead of a serialized dict — allows calling methods, traversing relations, etc.
- **`context_object`**: dotted path to resolve **`object`** from the parent template context (e.g. `"meeting"`, `"participant.meeting"`). When set, `obj=` is no longer required in the template tag.

By default, **`object` is a plain dict** (not a model instance) unless **`raw_object`** is checked. Relation contexts run **before** `object` is replaced, so their `filter_spec` still sees the real model on the render context.

### `DynamicRelationContext`

Attached to a `DynamicTemplate` via FK. Defines an extra variable (default **`name`** = related model’s `model` name) containing **materialized rows**:

- **`manager_method`**: no-arg chain such as `objects.all` or `objects.get_with_tva`.
- **`filter_spec`**: dynamic `.filter()` kwargs; **string values** are resolved from the bound **`object`** (dotted paths) or as mini-templates with `{{ }}` / `{% %}` for the full render context.
- **`filter_literal`**: static `.filter()` kwargs (no resolution). Merged with `filter_spec`; overlapping keys are **won by `filter_spec`**.
- **`model_fields`**: ORM columns per row (empty → all concrete on the **related** model).
- **`annotate_fields`**: list of annotation aliases already on the queryset returned by **`manager_method`** (e.g. `objects.with_totals`). Not generated here.
- **`fields`**: per-row Python names via **`getattr(row_instance, name)`**.

Rows are exposed as an **immutable tuple of dicts** (no `QuerySet` in the fragment). Use **`|length`**, **`rows.0.name`**, etc.

## Template tag `{% dyntpl %}`

- First argument: **`named_id`** string (or variable).
- **`obj=`**: optional model instance; must match the template’s `content_type`.
- **`ctype=`**: optional disambiguation when the same `named_id` exists for several content types (model class, instance, `app_label.Model`, or `ContentType`). **Not** injected into the inner context.
- **Other keyword arguments** are merged into the fragment context (and are visible to relation filters).

Rendering is implemented in **`render_dynamic_template_fragment`** (shared with admin preview).

## Security and shape

- Dynamic templates execute **DTL**; treat `template` content as **trusted** or sandbox separately if needed.
- Relation rows and `object` are **dicts** built from **`values_list`** / **`getattr`**, not ORM instances, to avoid accidental method exposure on querysets in templates.

## Optional integrations

- **Admin**: `django-boosted` boosted admin with a “Preview fragment” view (dev optional dependency).
- **Richtext**: e.g. `django-richtextfield` + `DYNAMIC_TEMPLATE_RICHTEXT_WIDGET` in project settings.
