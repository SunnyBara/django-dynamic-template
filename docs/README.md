# Documentation index

Documentation for **django-dynamic-template**: a Django app that stores DTL fragments in the database, keyed by `ContentType` and a `NamedID` slug, with optional related querysets and admin preview.

## Files

| File | Contents |
|------|----------|
| [purpose.md](purpose.md) | Goals, features, template context rules |
| [structure.md](structure.md) | Package layout under `src/dynamic_template/` |
| [development.md](development.md) | Tests, tooling, conventions |
| [AI.md](AI.md) | AI assistant contract and domain reference |

## Assistant quick reference

- **Install**: `pip install -e .` from the repository root (package lives in `src/`).
- **Tests**: `pytest` from the project root (`pythonpath` and `DJANGO_SETTINGS_MODULE` are set in `pyproject.toml`).
- **Migrations** (dev DB): `PYTHONPATH=src DJANGO_SETTINGS_MODULE=tests.settings python manage.py migrate`.
- **Language**: Use English for code, docstrings, and docs unless the user explicitly asks otherwise.
- **Dependencies**: Keep the library lean; optional dev stack is listed under `[project.optional-dependencies]` in `pyproject.toml`.

## Library at a glance

- **`DynamicTemplate`**: `label`, `content_type`, `named_id`, `template` (richtext), `model_fields`, `annotate_fields`, `fields` (Python attrs on `object`).
- **`DynamicRelationContext`**: per-template related queryset (`manager_method`, `filter_spec`, `filter_literal`, `model_fields`, `annotate_fields`, `fields`, `name`).
- **Tag** `{% dyntpl %}` and **`render_dynamic_template_fragment`** share the same rendering pipeline.
- **Fragment context**: `object` is a **dict** (after relation contexts run); relation variables are **tuples of dicts** per row. See [purpose.md](purpose.md).
