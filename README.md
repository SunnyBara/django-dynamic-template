# django-dynamic-template

Django app for **content-type–scoped dynamic templates**: store DTL fragments in the database, address them with a **`named_id`** slug ([django-namedid](https://github.com/octolo/django-namedid)), inject optional **related querysets** and a structured **`object`** dict into each fragment.

## Requirements

- Python ≥ 3.10  
- Django ≥ 3.2  
- **django-namedid** (declared in `pyproject.toml`; VCS pin until stable wheels are available)

## Installation

From the repository root (editable install recommended for local work):

```bash
pip install -e .
```

Add the app and dependencies you need:

```python
INSTALLED_APPS = [
    # ...
    "dynamic_template",
]
```

Optional: **django-boosted** (admin preview), **django-richtextfield** (TinyMCE-style widget) — see `pyproject.toml` `[project.optional-dependencies]` **dev**.

## Concepts

| Piece | Role |
|--------|------|
| **`DynamicTemplate`** | `label`, `content_type`, `named_id`, `template` (richtext), plus `model_fields`, `annotate_fields`, `fields` shaping **`object`** in the fragment |
| **`DynamicRelationContext`** | Related queryset (manager + filters), same three JSON fields per **row**; rows are **tuples of dicts** in the fragment |
| **`{% dyntpl %}`** | Loads a template by `named_id`, merges context, evaluates relation contexts, then replaces **`object`** with a plain **dict** |

- **`model_fields`**: ORM column names (empty → all concrete fields on the model).  
- **`annotate_fields`**: list of annotation **aliases** already on the queryset / instance — this app does **not** call `.annotate()`; your manager or view must provide them.  
- **`fields`**: extra Python names resolved with **`getattr`** (`@property`, class attributes, methods).

Filters on relations: **`filter_spec`** (resolved from **`object`** + template context) and **`filter_literal`** (static ORM kwargs). See **`docs/purpose.md`** for full detail.

## Template tag

```django
{% load dyntpl %}

{% dyntpl "my-block-named-id" %}
{% dyntpl tpl_id obj=article %}
{% dyntpl tpl_id ctype=Product obj=product %}
```

- **`obj=`**: must match the template’s `content_type`.  
- **`ctype=`**: disambiguates when the same `named_id` exists for several models.  
- Other keyword arguments are merged into the **inner** fragment context.

In the fragment, use **`{{ object.name }}`**, **`{% for row in article %}{{ row.title }}{% endfor %}`**, **`{{ rows|length }}`** (not `.count` on querysets).

## Settings (optional)

```python
# Import path to a widget class for the template field in admin
DYNAMIC_TEMPLATE_RICHTEXT_WIDGET = "djrichtextfield.widgets.RichTextWidget"
```

## Development

```bash
pytest
```

`pyproject.toml` sets `DJANGO_SETTINGS_MODULE=tests.settings` and `pythonpath=["src"]`.

Apply migrations for the bundled test project:

```bash
PYTHONPATH=src DJANGO_SETTINGS_MODULE=tests.settings python manage.py migrate
```

More detail: **`docs/`** (`purpose.md`, `structure.md`, `development.md`).

## License

MIT
