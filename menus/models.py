from django.db import models

from core.models import TimeStampedModel


class Menu(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    price = models.PositiveIntegerField()
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "id"]
        verbose_name = "menu"
        verbose_name_plural = "menus"

    def __str__(self) -> str:
        return f"{self.name} ({self.price})"

