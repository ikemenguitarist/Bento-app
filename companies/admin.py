from django.contrib import admin

from companies.models import Company, Department


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "created_at", "updated_at")
    search_fields = ("name", "slug")
    list_filter = ("is_active",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "slug", "is_active", "created_at")
    search_fields = ("name", "slug", "company__name")
    list_filter = ("company", "is_active")
    autocomplete_fields = ("company",)
    prepopulated_fields = {"slug": ("name",)}

