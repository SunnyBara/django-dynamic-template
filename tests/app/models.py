from django.db import models


class ProductQuerySet(models.QuerySet):
    def with_n_articles(self):
        return self.annotate(n_articles=models.Count("articles"))

    def with_n_art(self):
        return self.annotate(n_art=models.Count("articles"))


class Product(models.Model):
    toto = "2"
    name = models.CharField(max_length=100)

    objects = ProductQuerySet.as_manager()

    def __str__(self) -> str:
        return self.name


class ArticleManager(models.Manager):
    def get_with_tva(self):
        """Example custom manager chain (no-op filter for tests)."""
        return self.get_queryset()


class Article(models.Model):
    title = models.CharField(max_length=100)
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="articles",
    )

    objects = ArticleManager()

    @property
    def title_upper(self) -> str:
        return self.title.upper()

    def __str__(self) -> str:
        return self.title
