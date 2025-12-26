# inventory/migrations/0002_add_created_updated_fields.py
from django.db import migrations, models
import django.utils.timezone


def set_default_dates(apps, schema_editor):
    """Установить текущую дату для существующих записей"""
    Material = apps.get_model('inventory', 'Material')
    now = django.utils.timezone.now()

    # Обновляем все существующие записи
    Material.objects.all().update(created_at=now, updated_at=now)


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='material',
            name='created_at',
            field=models.DateTimeField(
                null=True,  # Временно nullable
                verbose_name='Дата создания'
            ),
        ),
        migrations.AddField(
            model_name='material',
            name='updated_at',
            field=models.DateTimeField(
                null=True,  # Временно nullable
                verbose_name='Дата обновления'
            ),
        ),

        # Заполняем существующие записи
        migrations.RunPython(set_default_dates, migrations.RunPython.noop),

        # Делаем поля NOT NULL
        migrations.AlterField(
            model_name='material',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                verbose_name='Дата создания'
            ),
        ),
        migrations.AlterField(
            model_name='material',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True,
                verbose_name='Дата обновления'
            ),
        ),
    ]