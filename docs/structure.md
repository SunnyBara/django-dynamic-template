## Project structure

Python package **`dynamic_template`** lives under **`src/`** (setuptools `where = ["src"]`).

### Layout

```
django-dynamic-template/
├── src/
│   └── dynamic_template/
│       ├── __init__.py
│       ├── admin/
│       │   ├── __init__.py
│       │   ├── relation_context.py   # DynamicRelationContextInline
│       │   └── template.py           # DynamicTemplateAdmin + forms + boost views
│       ├── fields.py                 # RichTextField wrapper
│       ├── io.py                     # JSON export / import helpers
│       ├── models/
│       │   ├── __init__.py
│       │   ├── _helpers.py           # values_list_field_names, mapping_from_row, json_str_list
│       │   ├── relation_context.py   # DynamicRelationContext
│       │   └── template.py           # DynamicTemplate, QuerySet, Manager
│       ├── rendering.py              # render_dynamic_template_fragment
│       ├── resolve.py                # filter_spec value resolution
│       ├── migrations/
│       ├── templates/                # admin preview partials
│       └── templatetags/
│           └── dyntpl.py             # {% dyntpl %}
├── tests/
│   ├── settings.py
│   ├── app/                          # Example models (Product, Article)
│   ├── test_dyntpl.py
│   ├── test_dynamic_relation_context.py
│   └── test_io.py
├── docs/
├── manage.py
├── pyproject.toml
└── README.md
```

### Module roles

| Module | Role |
|--------|------|
| `models/template.py` | `DynamicTemplate` model, queryset, manager, `freeze_bound_for_fragment` |
| `models/relation_context.py` | `DynamicRelationContext` model, `get_queryset` |
| `models/_helpers.py` | `values_list_field_names`, `mapping_from_row`, `json_str_list` |
| `admin/template.py` | `DynamicTemplateAdmin` (django-boosted), import/export/preview views, forms |
| `admin/relation_context.py` | `DynamicRelationContextInline` |
| `io.py` | JSON serialization, import, `json_attachment_response`, `content_disposition_attachment` |
| `resolve.py` | `build_filter_kwargs` / dotted paths from `object` |
| `rendering.py` | Build render context: flatten + `extra`, relation loops, freeze `object` |
| `templatetags/dyntpl.py` | Tag: resolve `ctype`, load `DynamicTemplate`, call `rendering` |

### Public surface

Install exposes the **`dynamic_template`** Django app and the **`dyntpl`** template library. There is no requirement to import submodules from application code beyond `INSTALLED_APPS` and `{% load dyntpl %}`.
