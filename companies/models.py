from django.db import models
from django.utils.text import slugify

from core.models import TimeStampedModel


class Company(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]
        verbose_name = "company"
        verbose_name_plural = "companies"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Department(TimeStampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="departments",
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["company__name", "name", "id"]
        verbose_name = "department"
        verbose_name_plural = "departments"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="uniq_department_name_per_company",
            ),
            models.UniqueConstraint(
                fields=["company", "slug"],
                name="uniq_department_slug_per_company",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.company.name} / {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
