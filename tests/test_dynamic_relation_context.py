import pytest
from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template

from dynamic_template.models import DynamicRelationContext, DynamicTemplate
from tests.app.models import Article, Product


@pytest.mark.django_db
def test_relation_context_uses_manager_and_filter_on_object():
    product = Product.objects.create(name="P1")
    Article.objects.create(title="A1", product=product)
    Article.objects.create(title="A2", product=product)

    ct_product = ContentType.objects.get_for_model(Product)
    ct_article = ContentType.objects.get_for_model(Article)

    dt = DynamicTemplate.objects.create(
        label="Product block",
        content_type=ct_product,
        template="{% for row in article %}{{ row.title }},{% endfor %}",
    )
    DynamicRelationContext.objects.create(
        dynamic_template=dt,
        content_type=ct_article,
        manager_method="objects.get_with_tva",
        filter_spec={"product_id": "pk"},
    )

    out = Template(
        "{% load dyntpl %}{% dyntpl tid obj=p %}",
    ).render(Context({"tid": dt.named_id, "p": product}))

    assert "A1" in out and "A2" in out


@pytest.mark.django_db
def test_relation_context_resolves_filter_from_article_in_context():
    product = Product.objects.create(name="P2")
    article = Article.objects.create(title="FromArticle", product=product)

    ct_product = ContentType.objects.get_for_model(Product)
    ct_article = ContentType.objects.get_for_model(Article)

    dt = DynamicTemplate.objects.create(
        label="Tpl2",
        content_type=ct_product,
        template="{% for row in arts %}{{ row.title }}{% endfor %}",
    )
    DynamicRelationContext.objects.create(
        dynamic_template=dt,
        content_type=ct_article,
        manager_method="objects.all",
        filter_spec={"product_id": "pk"},
        name="arts",
    )

    out = Template(
        "{% load dyntpl %}{% dyntpl tid obj=p %}",
    ).render(
        Context(
            {
                "tid": dt.named_id,
                "p": product,
            }
        )
    )

    assert out.strip() == "FromArticle"


@pytest.mark.django_db
def test_relation_context_legacy_bare_method_on_default_manager():
    """Single token still means `_default_manager.<name>()`."""
    product = Product.objects.create(name="P3")
    Article.objects.create(title="Legacy", product=product)

    ct_product = ContentType.objects.get_for_model(Product)
    ct_article = ContentType.objects.get_for_model(Article)

    dt = DynamicTemplate.objects.create(
        label="Tpl legacy",
        content_type=ct_product,
        template="{{ arts|length }}",
    )
    DynamicRelationContext.objects.create(
        dynamic_template=dt,
        content_type=ct_article,
        manager_method="all",
        filter_spec={"product_id": "pk"},
        name="arts",
    )

    out = Template(
        "{% load dyntpl %}{% dyntpl tid obj=p %}",
    ).render(Context({"tid": dt.named_id, "p": product}))

    assert out.strip() == "1"


@pytest.mark.django_db
def test_relation_context_values_list_single_field_flat():
    product = Product.objects.create(name="OnlyName")
    article = Article.objects.create(title="A", product=product)

    ct_product = ContentType.objects.get_for_model(Product)
    ct_article = ContentType.objects.get_for_model(Article)

    dt = DynamicTemplate.objects.create(
        label="Tpl vl flat",
        content_type=ct_article,
        template="{% for row in products %}{{ row.name }}{% endfor %}",
    )
    DynamicRelationContext.objects.create(
        dynamic_template=dt,
        content_type=ct_product,
        manager_method="objects.all",
        filter_spec={"pk": "product.pk"},
        model_fields=["name"],
        name="products",
    )

    out = Template(
        "{% load dyntpl %}{% dyntpl tid obj=article %}",
    ).render(Context({"tid": dt.named_id, "article": article}))

    assert out.strip() == "OnlyName"


@pytest.mark.django_db
def test_relation_context_values_list_multiple_columns():
    product = Product.objects.create(name="Multi")
    article = Article.objects.create(title="A", product=product)

    ct_product = ContentType.objects.get_for_model(Product)
    ct_article = ContentType.objects.get_for_model(Article)

    dt = DynamicTemplate.objects.create(
        label="Tpl vl multi",
        content_type=ct_article,
        template=(
            "{% for row in products %}{{ row.id }}|{{ row.name }}{% endfor %}"
        ),
    )
    DynamicRelationContext.objects.create(
        dynamic_template=dt,
        content_type=ct_product,
        manager_method="objects.all",
        filter_spec={"pk": "product.pk"},
        model_fields=["id", "name"],
        name="products",
    )

    out = Template(
        "{% load dyntpl %}{% dyntpl tid obj=article %}",
    ).render(Context({"tid": dt.named_id, "article": article}))

    assert f"{product.pk}|Multi" == out.strip()


@pytest.mark.django_db
def test_relation_context_literal_filter_merged_with_object_filter():
    product = Product.objects.create(name="P-lit")
    Article.objects.create(title="Keep", product=product)
    Article.objects.create(title="Drop", product=product)

    ct_product = ContentType.objects.get_for_model(Product)
    ct_article = ContentType.objects.get_for_model(Article)

    dt = DynamicTemplate.objects.create(
        label="Tpl literal merge",
        content_type=ct_product,
        template="{% for row in article %}{{ row.title }}{% endfor %}",
    )
    DynamicRelationContext.objects.create(
        dynamic_template=dt,
        content_type=ct_article,
        manager_method="objects.all",
        filter_spec={"product_id": "pk"},
        filter_literal={"title": "Keep"},
    )

    out = Template(
        "{% load dyntpl %}{% dyntpl tid obj=p %}",
    ).render(Context({"tid": dt.named_id, "p": product}))

    assert out.strip() == "Keep"


@pytest.mark.django_db
def test_relation_context_dotted_path_from_object_fk():
    """Filter values use attributes of the bound ``object`` (e.g. article → product)."""
    product = Product.objects.create(name="P-fk")
    article = Article.objects.create(title="Art-fk", product=product)

    ct_product = ContentType.objects.get_for_model(Product)
    ct_article = ContentType.objects.get_for_model(Article)

    dt = DynamicTemplate.objects.create(
        label="Tpl fk",
        content_type=ct_article,
        template="{{ products.0.name }}",
    )
    DynamicRelationContext.objects.create(
        dynamic_template=dt,
        content_type=ct_product,
        manager_method="objects.all",
        filter_spec={"id": "product.pk"},
        name="products",
    )

    out = Template(
        "{% load dyntpl %}{% dyntpl tid obj=article %}",
    ).render(Context({"tid": dt.named_id, "article": article}))

    assert out.strip() == "P-fk"


@pytest.mark.django_db
def test_relation_context_annotate_count_on_queryset():
    product = Product.objects.create(name="PC")
    Article.objects.create(title="a1", product=product)
    Article.objects.create(title="a2", product=product)

    ct_product = ContentType.objects.get_for_model(Product)

    dt = DynamicTemplate.objects.create(
        label="Tpl ann",
        content_type=ct_product,
        template="{% for row in product %}{{ row.n_articles }}{% endfor %}",
    )
    DynamicRelationContext.objects.create(
        dynamic_template=dt,
        content_type=ct_product,
        manager_method="objects.with_n_articles",
        filter_spec={"pk": "pk"},
        annotate_fields=["n_articles"],
        model_fields=["name"],
    )

    out = Template(
        "{% load dyntpl %}{% dyntpl tid obj=p %}",
    ).render(Context({"tid": dt.named_id, "p": product}))

    assert out.strip() == "2"


@pytest.mark.django_db
def test_relation_context_python_property_on_row():
    product = Product.objects.create(name="P")
    article = Article.objects.create(title="hello", product=product)

    ct_product = ContentType.objects.get_for_model(Product)
    ct_article = ContentType.objects.get_for_model(Article)

    dt = DynamicTemplate.objects.create(
        label="Tpl prop",
        content_type=ct_product,
        template="{% for row in arts %}{{ row.title_upper }}{% endfor %}",
    )
    DynamicRelationContext.objects.create(
        dynamic_template=dt,
        content_type=ct_article,
        manager_method="objects.all",
        filter_spec={"product_id": "pk"},
        model_fields=["title"],
        fields=["title_upper"],
        name="arts",
    )

    out = Template(
        "{% load dyntpl %}{% dyntpl tid obj=p %}",
    ).render(Context({"tid": dt.named_id, "p": product}))

    assert out.strip() == "HELLO"


@pytest.mark.django_db
def test_dynamic_template_manager_with_relation_context_count():
    ct = ContentType.objects.get_for_model(Product)
    dt = DynamicTemplate.objects.create(
        label="Counted",
        content_type=ct,
        template="x",
    )
    ct_article = ContentType.objects.get_for_model(Article)
    DynamicRelationContext.objects.create(
        dynamic_template=dt,
        content_type=ct_article,
    )
    DynamicRelationContext.objects.create(
        dynamic_template=dt,
        content_type=ct_article,
        name="second",
    )

    row = DynamicTemplate.objects.with_relation_context_count().get(pk=dt.pk)
    assert row.relation_context_count == 2

    bare = DynamicTemplate.objects.get(pk=dt.pk)
    assert not hasattr(bare, "relation_context_count")
