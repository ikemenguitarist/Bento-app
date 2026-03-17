from django.contrib import admin

from companies.models import Company, Department


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "public_code", "is_active", "created_at", "updated_at")
    search_fields = ("name", "public_code")
    list_filter = ("is_active",)
    readonly_fields = ("public_code",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "public_code", "is_active", "created_at")
    search_fields = ("name", "public_code", "company__name")
    list_filter = ("company", "is_active")
    autocomplete_fields = ("company",)
    readonly_fields = ("public_code",)
