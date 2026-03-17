import secrets
import string

from django.db import models

from core.models import TimeStampedModel

PUBLIC_CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_public_code(length=10):
    return "".join(secrets.choice(PUBLIC_CODE_ALPHABET) for _ in range(length))


class Company(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    public_code = models.CharField(max_length=10, unique=True, editable=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name", "id"]
        verbose_name = "company"
        verbose_name_plural = "companies"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.public_code:
            self.public_code = self._generate_unique_public_code()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_unique_public_code(cls):
        while True:
            candidate = generate_public_code()
            if not cls.objects.filter(public_code=candidate).exists():
                return candidate


class Department(TimeStampedModel):
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="departments",
    )
    name = models.CharField(max_length=255)
    public_code = models.CharField(max_length=10, unique=True, editable=False)
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
        ]

    def __str__(self) -> str:
        return f"{self.company.name} / {self.name}"

    def save(self, *args, **kwargs):
        if not self.public_code:
            self.public_code = self._generate_unique_public_code()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_unique_public_code(cls):
        while True:
            candidate = generate_public_code()
            if not cls.objects.filter(public_code=candidate).exists():
                return candidate
