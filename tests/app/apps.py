from django.apps import AppConfig


class TestsAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tests.app"
    verbose_name = "Test App"
