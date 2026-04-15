import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template

from dynamic_template.models import DynamicTemplate
from tests.app.models import Article, Product

User = get_user_model()


@pytest.mark.django_db
def test_dyntpl_renders_by_named_id():
    ct = ContentType.objects.get_for_model(User)
    DynamicTemplate.objects.create(
        label="Hello Block",
        content_type=ct,
        template="Hello {{ name }}",
    )
    dt = DynamicTemplate.objects.get()
    assert dt.named_id == "hello-block"

    out = Template(
        "{% load dyntpl %}{% dyntpl tpl_id name=user.username %}",
    ).render(Context({"tpl_id": dt.named_id, "user": User(username="Ada")}))

    assert out.strip() == "Hello Ada"


@pytest.mark.django_db
def test_dyntpl_obj_skips_wrong_content_type():
    ct_user = ContentType.objects.get_for_model(User)
    DynamicTemplate.objects.create(
        label="Only users",
        content_type=ct_user,
        template="OK",
    )
    dt = DynamicTemplate.objects.get()

    class Other:
        pass

    other = Other()
    out = Template(
        "{% load dyntpl %}{% dyntpl nid obj=o %}",
    ).render(Context({"nid": dt.named_id, "o": other}))

    assert out.strip() == ""


@pytest.mark.django_db
def test_dyntpl_obj_renders_when_content_type_matches():
    ct = ContentType.objects.get_for_model(User)
    DynamicTemplate.objects.create(
        label="Greet",
        content_type=ct,
        template="Hi {{ object.username }}",
        model_fields=["username"],
    )
    dt = DynamicTemplate.objects.get()
    user = User(username="bob")

    out = Template(
        "{% load dyntpl %}{% dyntpl nid obj=u %}",
    ).render(Context({"nid": dt.named_id, "u": user}))

    assert out.strip() == "Hi bob"


@pytest.mark.django_db
def test_dyntpl_ctype_disambiguates_same_named_id():
    ct_user = ContentType.objects.get_for_model(User)
    ct_product = ContentType.objects.get_for_model(Product)
    DynamicTemplate.objects.create(
        label="Dup",
        content_type=ct_user,
        template="USER",
    )
    DynamicTemplate.objects.create(
        label="Dup",
        content_type=ct_product,
        template="PRODUCT",
    )
    nid_user = DynamicTemplate.objects.get(content_type=ct_user).named_id
    nid_product = DynamicTemplate.objects.get(content_type=ct_product).named_id
    assert nid_user == nid_product

    ambiguous = Template("{% load dyntpl %}{% dyntpl nid %}").render(Context({"nid": nid_user}))
    assert ambiguous.strip() == ""

    out_user = Template(
        "{% load dyntpl %}{% dyntpl nid ctype=user_model %}",
    ).render(Context({"nid": nid_user, "user_model": User}))
    assert out_user.strip() == "USER"

    out_product = Template(
        "{% load dyntpl %}{% dyntpl nid ctype=product_model %}",
    ).render(Context({"nid": nid_product, "product_model": Product}))
    assert out_product.strip() == "PRODUCT"


@pytest.mark.django_db
def test_dyntpl_obj_empty_model_fields_is_dict_of_all_concrete():
    """``model_fields`` empty → dict of all concrete columns (``{{ object.name }}``)."""
    ct = ContentType.objects.get_for_model(Product)
    DynamicTemplate.objects.create(
        label="Prod tuple",
        content_type=ct,
        template="{{ object.name }}",
    )
    dt = DynamicTemplate.objects.get()
    product = Product.objects.create(name="TupleName")

    out = Template(
        "{% load dyntpl %}{% dyntpl nid obj=p %}",
    ).render(Context({"nid": dt.named_id, "p": product}))

    assert out.strip() == "TupleName"


@pytest.mark.django_db
def test_dyntpl_obj_merges_model_fields_annotate_and_class_attr():
    ct = ContentType.objects.get_for_model(Product)
    DynamicTemplate.objects.create(
        label="Merge attrs",
        content_type=ct,
        template="{{ object.name }}-{{ object.toto }}-{{ object.n_art }}",
        model_fields=["name"],
        annotate_fields=["n_art"],
        fields=["toto"],
    )
    dt = DynamicTemplate.objects.get()
    product = Product.objects.create(name="M")
    Article.objects.create(title="x", product=product)
    p = Product.objects.with_n_art().get(pk=product.pk)

    out = Template(
        "{% load dyntpl %}{% dyntpl nid obj=p %}",
    ).render(Context({"nid": dt.named_id, "p": p}))

    assert out.strip() == "M-2-1"


@pytest.mark.django_db
def test_dyntpl_ctype_string_app_label_model():
    ct = ContentType.objects.get_for_model(Product)
    DynamicTemplate.objects.create(
        label="Sku",
        content_type=ct,
        template="ok",
    )
    dt = DynamicTemplate.objects.get()
    out = Template(
        '{% load dyntpl %}{% dyntpl nid ctype="app.Product" %}',
    ).render(Context({"nid": dt.named_id}))
    assert out.strip() == "ok"


@pytest.mark.django_db
def test_dyntpl_ctype_not_leaked_into_inner_context():
    ct = ContentType.objects.get_for_model(User)
    DynamicTemplate.objects.create(
        label="Inner",
        content_type=ct,
        template="{{ ctype|default:'none' }}",
    )
    dt = DynamicTemplate.objects.get()
    out = Template(
        "{% load dyntpl %}{% dyntpl nid ctype=user_model %}",
    ).render(Context({"nid": dt.named_id, "user_model": User}))
    assert out.strip() == "none"
