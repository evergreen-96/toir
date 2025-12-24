from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("maintenance", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WorkOrderFile",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("file", models.FileField(upload_to="workorders/")),
                ("is_active", models.BooleanField(default=True)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                (
                    "work_order",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attachments",
                        to="maintenance.workorder",
                    ),
                ),
            ],
        ),
    ]