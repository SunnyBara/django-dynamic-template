"""URL configuration for tests."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
]

try:
    import djrichtextfield  # noqa: F401

    urlpatterns += [
        path("djrichtextfield/", include("djrichtextfield.urls")),
    ]
except ImportError:
    pass
