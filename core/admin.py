from django.contrib import admin

from core.models import OrderDeadlineSetting


@admin.register(OrderDeadlineSetting)
class OrderDeadlineSettingAdmin(admin.ModelAdmin):
    list_display = ("applies_from", "order_deadline_time", "is_active", "updated_at")
    list_filter = ("is_active",)
    ordering = ("-applies_from", "-id")

