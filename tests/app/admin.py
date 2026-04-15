from django.contrib import admin

from tests.app.models import Article, Product


class StaffDemoModelAdmin(admin.ModelAdmin):
    """
    Local test app: any staff user can use these models without assigning
    per-app permissions (default Django admin hides apps with no permissions).
    """

    def has_module_permission(self, request):
        return request.user.is_staff

    def has_view_permission(self, request, obj=None):
        return request.user.is_staff

    def has_add_permission(self, request):
        return request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return request.user.is_staff


@admin.register(Product)
class ProductAdmin(StaffDemoModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Article)
class ArticleAdmin(StaffDemoModelAdmin):
    list_display = ("id", "title", "product")
    list_filter = ("product",)
    search_fields = ("title",)
    autocomplete_fields = ("product",)
