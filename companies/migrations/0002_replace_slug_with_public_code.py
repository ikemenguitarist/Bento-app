import secrets
import string

from django.db import migrations, models

PUBLIC_CODE_ALPHABET = string.ascii_uppercase + string.digits


def generate_public_code(length=10):
    return "".join(secrets.choice(PUBLIC_CODE_ALPHABET) for _ in range(length))


def populate_public_codes(apps, schema_editor):
    Company = apps.get_model("companies", "Company")
    Department = apps.get_model("companies", "Department")

    used_codes = set(
        Company.objects.exclude(public_code__isnull=True).values_list("public_code", flat=True)
    )
    used_codes.update(
        Department.objects.exclude(public_code__isnull=True).values_list(
            "public_code", flat=True
        )
    )

    def next_code():
        while True:
            candidate = generate_public_code()
            if candidate not in used_codes:
                used_codes.add(candidate)
                return candidate

    for company in Company.objects.filter(public_code__isnull=True):
        company.public_code = next_code()
        company.save(update_fields=["public_code"])

    for department in Department.objects.filter(public_code__isnull=True):
        department.public_code = next_code()
        department.save(update_fields=["public_code"])


class Migration(migrations.Migration):
    dependencies = [
        ("companies", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="public_code",
            field=models.CharField(editable=False, max_length=10, null=True),
        ),
        migrations.AddField(
            model_name="department",
            name="public_code",
            field=models.CharField(editable=False, max_length=10, null=True),
        ),
        migrations.RunPython(populate_public_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="company",
            name="public_code",
            field=models.CharField(editable=False, max_length=10, unique=True),
        ),
        migrations.AlterField(
            model_name="department",
            name="public_code",
            field=models.CharField(editable=False, max_length=10, unique=True),
        ),
        migrations.RemoveConstraint(
            model_name="department",
            name="uniq_department_slug_per_company",
        ),
        migrations.RemoveField(
            model_name="company",
            name="slug",
        ),
        migrations.RemoveField(
            model_name="department",
            name="slug",
        ),
    ]
