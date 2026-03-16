from django.contrib import admin

from orders.models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_date",
        "company",
        "department",
        "status",
        "submitted_at",
        "updated_at",
    )
    search_fields = ("company__name", "department__name")
    list_filter = ("status", "order_date", "company")
    autocomplete_fields = ("company", "department")
    inlines = (OrderItemInline,)
    date_hierarchy = "order_date"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("order", "menu", "quantity", "updated_at")
    search_fields = ("order__department__name", "order__company__name", "menu__name")
    list_filter = ("menu", "order__company")
    autocomplete_fields = ("order", "menu")

