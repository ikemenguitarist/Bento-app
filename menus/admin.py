from django.contrib import admin

from menus.models import Menu


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "display_order", "is_active", "updated_at")
    search_fields = ("name",)
    list_filter = ("is_active",)
    ordering = ("display_order", "id")

