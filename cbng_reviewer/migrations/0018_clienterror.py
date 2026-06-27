import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cbng_reviewer", "0017_edit_cbng_review_is_dele_b35f1f_idx"),
    ]

    operations = [
        migrations.CreateModel(
            name="ClientError",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("message", models.TextField()),
                ("source", models.CharField(blank=True, max_length=2048, null=True)),
                ("lineno", models.IntegerField(blank=True, null=True)),
                ("colno", models.IntegerField(blank=True, null=True)),
                ("stack", models.TextField(blank=True, null=True)),
                ("page_url", models.CharField(blank=True, max_length=2048, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["user"], name="cbng_review_user_id_clienterror_idx"),
                    models.Index(fields=["created"], name="cbng_review_created_clienterror_idx"),
                ],
            },
        ),
    ]
