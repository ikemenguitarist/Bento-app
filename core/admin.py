from django.contrib import admin

from core.models import OrderDeadlineSetting, ShopHoliday


@admin.register(OrderDeadlineSetting)
class OrderDeadlineSettingAdmin(admin.ModelAdmin):
    list_display = ("applies_from", "order_deadline_time", "is_active", "updated_at")
    list_filter = ("is_active",)
    ordering = ("-applies_from", "-id")


@admin.register(ShopHoliday)
class ShopHolidayAdmin(admin.ModelAdmin):
    list_display = ("holiday_date", "name", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name",)
    ordering = ("holiday_date", "id")
