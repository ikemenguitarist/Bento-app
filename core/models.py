from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class OrderDeadlineSetting(TimeStampedModel):
    order_deadline_time = models.TimeField(verbose_name="order deadline time")
    applies_from = models.DateField(verbose_name="applies from")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-applies_from", "-id"]
        verbose_name = "order deadline setting"
        verbose_name_plural = "order deadline settings"

    def __str__(self) -> str:
        return f"{self.applies_from} {self.order_deadline_time}"


class ShopHoliday(TimeStampedModel):
    holiday_date = models.DateField(unique=True)
    name = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["holiday_date", "id"]
        verbose_name = "shop holiday"
        verbose_name_plural = "shop holidays"

    def __str__(self) -> str:
        if self.name:
            return f"{self.holiday_date} {self.name}"
        return str(self.holiday_date)
