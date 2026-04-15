"""Tests for dynamic_template.io (export / import round-trip, raw_object, context_object)."""

import json

import pytest
from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template

from dynamic_template.io import (
    content_disposition_attachment,
    import_payload,
    json_attachment_response,
    serialize_export,
)
from dynamic_template.models import DynamicRelationContext, DynamicTemplate
from tests.app.models import Article, Product


# ---------------------------------------------------------------------------
# content_disposition_attachment
# ---------------------------------------------------------------------------


def test_content_disposition_ascii():
    assert content_disposition_attachment("foo.json") == 'attachment; filename="foo.json"'


def test_content_disposition_non_ascii():
    header = content_disposition_attachment("café.json")
    assert "filename*=UTF-8''" in header
    assert "caf" in header


# ---------------------------------------------------------------------------
# json_attachment_response
# ---------------------------------------------------------------------------


def test_json_attachment_response():
    resp = json_attachment_response("test.json", {"a": 1})
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/json; charset=utf-8"
    assert "attachment" in resp["Content-Disposition"]
    body = json.loads(resp.content)
    assert body == {"a": 1}


# ---------------------------------------------------------------------------
# serialize / export round-trip
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_export_contains_raw_object_and_context_object():
    ct = ContentType.objects.get_for_model(Product)
    DynamicTemplate.objects.create(
        label="Export test",
        content_type=ct,
        template="Hello",
        raw_object=True,
        context_object="product",
    )
    payload = serialize_export(DynamicTemplate.objects.all())
    tpl_data = payload["dynamic_templates"][0]
    assert tpl_data["raw_object"] is True
    assert tpl_data["context_object"] == "product"


@pytest.mark.django_db
def test_export_includes_relation_contexts():
    ct_product = ContentType.objects.get_for_model(Product)
    ct_article = ContentType.objects.get_for_model(Article)
    dt = DynamicTemplate.objects.create(
        label="With rels",
        content_type=ct_product,
        template="x",
    )
    DynamicRelationContext.objects.create(
        dynamic_template=dt,
        content_type=ct_article,
        manager_method="objects.all",
        filter_spec={"product_id": "pk"},
        name="articles",
    )
    payload = serialize_export(DynamicTemplate.objects.all())
    rels = payload["dynamic_templates"][0]["relation_contexts"]
    assert len(rels) == 1
    assert rels[0]["name"] == "articles"
    assert rels[0]["filter_spec"] == {"product_id": "pk"}


# ---------------------------------------------------------------------------
# import_payload
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_creates_template():
    ct = ContentType.objects.get_for_model(Product)
    data = {
        "format_version": 1,
        "dynamic_templates": [
            {
                "label": "Imported",
                "content_type": f"{ct.app_label}.{ct.model}",
                "template": "{{ object.name }}",
                "model_fields": ["name"],
                "raw_object": True,
                "context_object": "product",
            }
        ],
    }
    result = import_payload(data)
    assert result["created"] == 1
    assert result["updated"] == 0
    assert result["errors"] == []
    dt = DynamicTemplate.objects.get()
    assert dt.label == "Imported"
    assert dt.raw_object is True
    assert dt.context_object == "product"
    assert dt.model_fields == ["name"]


@pytest.mark.django_db
def test_import_updates_existing_template():
    ct = ContentType.objects.get_for_model(Product)
    DynamicTemplate.objects.create(
        label="Updatable",
        content_type=ct,
        template="old",
    )
    data = {
        "format_version": 1,
        "dynamic_templates": [
            {
                "label": "Updatable",
                "content_type": f"{ct.app_label}.{ct.model}",
                "template": "new",
                "raw_object": True,
                "context_object": "obj",
            }
        ],
    }
    result = import_payload(data, replace=True)
    assert result["created"] == 0
    assert result["updated"] == 1
    dt = DynamicTemplate.objects.get()
    assert dt.template == "new"
    assert dt.raw_object is True
    assert dt.context_object == "obj"


@pytest.mark.django_db
def test_import_no_replace_skips_existing():
    ct = ContentType.objects.get_for_model(Product)
    DynamicTemplate.objects.create(label="Keep", content_type=ct, template="original")
    data = {
        "format_version": 1,
        "dynamic_templates": [
            {
                "label": "Keep",
                "content_type": f"{ct.app_label}.{ct.model}",
                "template": "replaced",
            }
        ],
    }
    result = import_payload(data, replace=False)
    assert result["created"] == 0
    assert result["updated"] == 0
    assert DynamicTemplate.objects.get().template == "original"


@pytest.mark.django_db
def test_import_with_relation_contexts():
    ct_product = ContentType.objects.get_for_model(Product)
    ct_article = ContentType.objects.get_for_model(Article)
    data = {
        "format_version": 1,
        "dynamic_templates": [
            {
                "label": "With rel",
                "content_type": f"{ct_product.app_label}.{ct_product.model}",
                "template": "x",
                "relation_contexts": [
                    {
                        "content_type": f"{ct_article.app_label}.{ct_article.model}",
                        "manager_method": "objects.all",
                        "filter_spec": {"product_id": "pk"},
                        "name": "articles",
                    }
                ],
            }
        ],
    }
    result = import_payload(data)
    assert result["created"] == 1
    assert result["errors"] == []
    assert DynamicRelationContext.objects.count() == 1
    rc = DynamicRelationContext.objects.get()
    assert rc.name == "articles"
    assert rc.filter_spec == {"product_id": "pk"}


@pytest.mark.django_db
def test_import_reports_errors_for_bad_items():
    data = {
        "format_version": 1,
        "dynamic_templates": [
            {"label": "", "content_type": "app.product"},
            "not-a-dict",
        ],
    }
    result = import_payload(data)
    assert result["created"] == 0
    assert len(result["errors"]) == 2


@pytest.mark.django_db
def test_import_rejects_bad_format_version():
    with pytest.raises(ValueError, match="format_version"):
        import_payload({"format_version": 99, "dynamic_templates": []})


@pytest.mark.django_db
def test_export_import_round_trip():
    """Full export → import round-trip preserves all fields."""
    ct_product = ContentType.objects.get_for_model(Product)
    ct_article = ContentType.objects.get_for_model(Article)
    dt = DynamicTemplate.objects.create(
        label="Round trip",
        content_type=ct_product,
        template="{{ object.name }}",
        model_fields=["name"],
        annotate_fields=["n_art"],
        fields=["toto"],
        raw_object=True,
        context_object="product",
    )
    DynamicRelationContext.objects.create(
        dynamic_template=dt,
        content_type=ct_article,
        manager_method="objects.all",
        filter_spec={"product_id": "pk"},
        filter_literal={"title": "x"},
        model_fields=["title"],
        annotate_fields=[],
        fields=["title_upper"],
        name="articles",
    )
    payload = serialize_export(DynamicTemplate.objects.all())

    DynamicRelationContext.objects.all().delete()
    DynamicTemplate.objects.all().delete()

    result = import_payload(payload)
    assert result["created"] == 1
    assert result["errors"] == []

    dt2 = DynamicTemplate.objects.get()
    assert dt2.label == "Round trip"
    assert dt2.model_fields == ["name"]
    assert dt2.annotate_fields == ["n_art"]
    assert dt2.fields == ["toto"]
    assert dt2.raw_object is True
    assert dt2.context_object == "product"

    rc = DynamicRelationContext.objects.get()
    assert rc.name == "articles"
    assert rc.manager_method == "objects.all"
    assert rc.filter_spec == {"product_id": "pk"}
    assert rc.filter_literal == {"title": "x"}
    assert rc.model_fields == ["title"]
    assert rc.fields == ["title_upper"]


# ---------------------------------------------------------------------------
# raw_object behaviour
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_raw_object_exposes_model_instance():
    ct = ContentType.objects.get_for_model(Product)
    DynamicTemplate.objects.create(
        label="Raw",
        content_type=ct,
        template="{{ object.name }}",
        raw_object=True,
    )
    dt = DynamicTemplate.objects.get()
    product = Product.objects.create(name="RawProd")

    out = Template(
        "{% load dyntpl %}{% dyntpl nid obj=p %}",
    ).render(Context({"nid": dt.named_id, "p": product}))
    assert out.strip() == "RawProd"


@pytest.mark.django_db
def test_raw_object_false_gives_dict():
    """With raw_object=False and model_fields set, object is a dict."""
    ct = ContentType.objects.get_for_model(Product)
    DynamicTemplate.objects.create(
        label="Dict obj",
        content_type=ct,
        template="{{ object.name }}",
        model_fields=["name"],
        raw_object=False,
    )
    dt = DynamicTemplate.objects.get()
    product = Product.objects.create(name="DictProd")

    out = Template(
        "{% load dyntpl %}{% dyntpl nid obj=p %}",
    ).render(Context({"nid": dt.named_id, "p": product}))
    assert out.strip() == "DictProd"


# ---------------------------------------------------------------------------
# context_object behaviour
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_context_object_resolves_from_parent_context():
    ct = ContentType.objects.get_for_model(Product)
    DynamicTemplate.objects.create(
        label="Auto obj",
        content_type=ct,
        template="{{ object.name }}",
        model_fields=["name"],
        context_object="product",
    )
    dt = DynamicTemplate.objects.get()
    product = Product.objects.create(name="AutoProd")

    out = Template(
        "{% load dyntpl %}{% dyntpl nid %}",
    ).render(Context({"nid": dt.named_id, "product": product}))
    assert out.strip() == "AutoProd"


@pytest.mark.django_db
def test_context_object_dotted_path():
    ct = ContentType.objects.get_for_model(Product)
    DynamicTemplate.objects.create(
        label="Dotted obj",
        content_type=ct,
        template="{{ object.name }}",
        model_fields=["name"],
        context_object="article.product",
    )
    dt = DynamicTemplate.objects.get()
    product = Product.objects.create(name="Dotted")
    article = Article.objects.create(title="Art", product=product)

    out = Template(
        "{% load dyntpl %}{% dyntpl nid %}",
    ).render(Context({"nid": dt.named_id, "article": article}))
    assert out.strip() == "Dotted"
