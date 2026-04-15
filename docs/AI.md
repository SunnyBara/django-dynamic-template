# AI assistant contract — django-dynamic-template

**Use this file as the primary reference** when working in this repository. If instructions conflict, prefer **observable code** and **`docs/purpose.md`** for product behavior.

---

## Absolute rules

- Do not invent tooling that does not exist here (there is **no** `service.py` / qualitybase entrypoint in this repo).
- Do not hardcode secrets, API keys, or credentials.
- Do not manipulate `sys.path` in library code; consumers install the package (`pip install -e .`) or use `PYTHONPATH=src` for local commands.
- Prefer **minimal, focused diffs**; do not refactor unrelated code unless asked.
- **Comments**: only where they remove real ambiguity (not narration of obvious code).

---

## Required practices

- **Language**: English for code, docstrings, errors, and `docs/*` unless the user explicitly requests another language.
- **Tests**: use **pytest**; configuration is in `pyproject.toml` (`tests.settings`, `pythonpath`).
- **Typing**: public APIs should remain type-hinted consistently with the rest of the module.
- **Migrations**: model changes that affect the DB should include migrations under `src/dynamic_template/migrations/`.

---

## Project overview

**django-dynamic-template** is a Django app providing:

- **`DynamicTemplate`**: DB-stored DTL fragment per `ContentType`, keyed by **`named_id`** (`NamedIDField` from `label`).
- **`DynamicRelationContext`**: optional related queryset injected into the fragment context as a **tuple of dicts** (materialized rows).
- **`{% dyntpl %}`** and **`render_dynamic_template_fragment`** for rendering.

Dependencies include **Django** and **django-namedid** (see `pyproject.toml`).

---

## Domain reference (keep in sync with code)

### Context merge order (`rendering.py`)

1. Flatten outer template `Context` into `base_context`.
2. Merge tag **`extra`** kwargs (everything except `obj` / `ctype` from `dyntpl`).
3. Set **`object`** to the **model instance** (if `bound`) for relation **`filter_spec`** resolution.
4. Evaluate each **`DynamicRelationContext`** → tuple of row dicts.
5. Replace **`object`** with **`DynamicTemplate.freeze_bound_for_fragment`** → **dict** only in the fragment.

### Field JSON columns

| Model | `model_fields` | `annotate_fields` | `fields` |
|-------|------------------|-------------------|----------|
| `DynamicTemplate` | ORM names for `object` dict | List of annotation **aliases** on the bound instance | Python names via `getattr(instance, …)` |
| `DynamicRelationContext` | ORM names per row | List of aliases on the relation queryset | Python names via `getattr(row, …)` |

**`filter_spec`** string values: dotted paths start from **`object`** as model instance during step 3; **`{{ }}`** uses full render context. **`filter_literal`**: static ORM kwargs.

### Annotations

**`annotate_fields`** is only a **list of names** to read from instances that already carry those annotations (custom manager / queryset). The library does **not** call `.annotate()`.

### Fragment variables

- **`object`**: `dict` by default; real model instance when **`raw_object=True`**.
- **Relation name** (e.g. `article`): **tuple** of **`dict`** rows — use **`row.field`**, **`rel.0.field`**, **`|length`**.

---

## Commands (informational)

- **Tests**: `pytest` from repository root.
- **Migrate (dev)**: `PYTHONPATH=src DJANGO_SETTINGS_MODULE=tests.settings python manage.py migrate`

---

## Anti-hallucination

If a request assumes APIs, scripts, or services that are not in this tree, **stop** and point to the actual layout in `docs/structure.md` or `src/dynamic_template/`.

---

## Checklist before finishing a change

- [ ] Behavior matches `docs/purpose.md` and existing tests (or tests updated).
- [ ] No unrelated refactors; migrations included if models changed.
- [ ] No fake project commands documented as mandatory.
- [ ] English for new code/docs unless user asked otherwise.
