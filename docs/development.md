## Development guidelines

### Environment

- **Python**: `>=3.10` (see `pyproject.toml`).
- **Editable install**: from repo root, `pip install -e .` so `dynamic_template` resolves from `src/`.

### Running tests

```bash
pytest
```

`pyproject.toml` sets `DJANGO_SETTINGS_MODULE = tests.settings` and `pythonpath = ["src"]` for pytest.

### Django commands (local dev DB)

```bash
PYTHONPATH=src DJANGO_SETTINGS_MODULE=tests.settings python manage.py migrate
```

Use **`tests.settings`** when exercising the bundled test project.

### Code style

- Prefer **English** for comments, docstrings, and documentation.
- Add or update **tests** under `tests/` for behavior changes.
- Keep the **library dependency set minimal**; dev-only tools (`ruff`, `mypy`, `pytest-django`, optional admin/richtext packages) belong in optional extras.

### Migrations

- Ship migrations under `src/dynamic_template/migrations/` with the app.
- After model changes, generate migrations with the same settings as above and commit them.

### Optional dev dependencies

Admin preview and boosted UI require **`django-boosted`** (and transitive **`django-virtualqueryset`**) in the environment. Rich text widgets may use **`django-richtextfield`** or another project-specific widget via **`DYNAMIC_TEMPLATE_RICHTEXT_WIDGET`**.
