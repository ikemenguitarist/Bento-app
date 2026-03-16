from django.core.exceptions import ValidationError
from django.db import models

from companies.models import Company, Department
from core.models import TimeStampedModel
from menus.models import Menu


class OrderStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    DEADLINE_OVER = "deadline_over", "Deadline over"


class Order(TimeStampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="orders",
    )
    order_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.DRAFT,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-order_date", "company__name", "department__name", "id"]
        verbose_name = "order"
        verbose_name_plural = "orders"
        constraints = [
            models.UniqueConstraint(
                fields=["department", "order_date"],
                name="uniq_order_per_department_per_day",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.order_date} {self.department}"

    def clean(self):
        if self.department_id and self.company_id:
            if self.department.company_id != self.company_id:
                raise ValidationError(
                    {"department": "department must belong to the selected company"}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )
    menu = models.ForeignKey(
        Menu,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    quantity = models.PositiveIntegerField()

    class Meta:
        ordering = ["order_id", "menu__display_order", "menu__id", "id"]
        verbose_name = "order item"
        verbose_name_plural = "order items"
        constraints = [
            models.UniqueConstraint(
                fields=["order", "menu"],
                name="uniq_menu_per_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.order} / {self.menu.name} x {self.quantity}"
