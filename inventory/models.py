from django.db import models
from django.urls import reverse
from django.core.validators import MinValueValidator
from simple_history.models import HistoricalRecords

from assets.models import Workstation
from hr.models import HumanResource
from locations.models import Location


class BaseInventoryModel(models.Model):
    """Базовая модель для инвентаря"""

    class Meta:
        abstract = True

    def get_absolute_url(self):
        """Абстрактный метод для получения URL"""
        raise NotImplementedError


class Warehouse(BaseInventoryModel):
    history = HistoricalRecords()

    name = models.CharField("Название склада", max_length=255)
    responsible = models.ForeignKey(
        HumanResource,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='Ответственный'
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Локация"
    )

    class Meta:
        verbose_name = "Склад"
        verbose_name_plural = "Склады"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['location']),
        ]

    def __str__(self):
        return self.name

    @property
    def display_location(self):
        """Отформатированное отображение локации"""
        return self.location or "—"

    @property
    def display_responsible(self):
        """Отформатированное отображение ответственного"""
        return self.responsible or "—"

    def get_absolute_url(self):
        return reverse('inventory:warehouse_detail', args=[self.pk])

    @property
    def materials_count(self):
        """Количество материалов на складе"""
        return self.materials.count()  # ИЗМЕНЕНО: materials вместо material_set

    def get_materials_summary(self):
        """Сводная информация по материалам"""
        from django.db.models import Sum
        materials = self.materials.all()  # ИЗМЕНЕНО: materials вместо material_set

        return {
            'total_count': materials.count(),
            'total_available': materials.aggregate(
                total=Sum('qty_available')
            )['total'] or 0,
            'total_reserved': materials.aggregate(
                total=Sum('qty_reserved')
            )['total'] or 0,
        }


class MaterialUoM(models.TextChoices):
    """Единицы измерения материалов"""
    PCS = "pcs", "шт"
    KG = "kg", "кг"
    LTR = "l", "л"
    MTR = "m", "м"
    HRS = "h", "ч"
    SET = "set", "комплект"
    ROLL = "roll", "рулон"
    BOX = "box", "коробка"
    PAL = "pal", "паллет"


class Material(BaseInventoryModel):
    history = HistoricalRecords()

    name = models.CharField("Полное наименование", max_length=255)
    group = models.CharField("Группа", max_length=255, blank=True)
    article = models.CharField("Артикул", max_length=255, blank=True)
    part_number = models.CharField("Номер детали", max_length=255, blank=True)
    uom = models.CharField(
        "Ед. изм.",
        max_length=10,
        choices=MaterialUoM.choices,
        default=MaterialUoM.PCS
    )
    qty_available = models.FloatField(
        "Количество (свободно)",
        default=0,
        validators=[MinValueValidator(0)]
    )
    qty_reserved = models.FloatField(
        "Количество (резерв)",
        default=0,
        validators=[MinValueValidator(0)]
    )
    warehouse = models.ForeignKey(
        Warehouse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Склад",
        related_name="materials"  # УСТАНОВЛЕН related_name
    )
    vendor = models.CharField("Производитель", max_length=255, blank=True)
    suitable_for = models.ManyToManyField(
        Workstation,
        blank=True,
        related_name="compatible_materials",
        verbose_name="Подходит для оборудования",
    )
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    image = models.ImageField(
        "Фото",
        upload_to="materials/%Y/%m/%d/",
        null=True,
        blank=True
    )
    min_stock_level = models.FloatField(
        "Минимальный запас",
        default=0,
        validators=[MinValueValidator(0)]
    )
    notes = models.TextField("Примечания", blank=True)

    class Meta:
        verbose_name = "Номенклатура"
        verbose_name_plural = "Номенклатура"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['article']),
            models.Index(fields=['part_number']),
            models.Index(fields=['is_active']),
            models.Index(fields=['warehouse']),
            models.Index(fields=['group']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('inventory:material_detail', args=[self.pk])

    @property
    def display_name(self):
        """Полное отображаемое имя с артикулом"""
        if self.article:
            return f"{self.name} ({self.article})"
        return self.name

    @property
    def qty_total(self):
        """Общее количество (свободно + в резерве)"""
        return self.qty_available + self.qty_reserved

    @property
    def can_reserve(self):
        """Можно ли зарезервировать дополнительное количество"""
        return self.qty_available > 0

    @property
    def stock_status(self):
        """Статус запаса"""
        if not self.is_active:
            return 'inactive'
        elif self.qty_available == 0:
            return 'out_of_stock'
        elif self.qty_available <= self.min_stock_level:
            return 'low_stock'
        elif self.qty_available <= self.qty_reserved:
            return 'reserved'
        else:
            return 'in_stock'

    @property
    def stock_status_display(self):
        """Отображаемое название статуса"""
        status_map = {
            'inactive': 'Неактивен',
            'out_of_stock': 'Отсутствует',
            'low_stock': 'Низкий запас',
            'reserved': 'В резерве',
            'in_stock': 'В наличии',
        }
        return status_map.get(self.stock_status, '—')

    def clean(self):
        """Валидация на уровне модели"""
        from django.core.exceptions import ValidationError

        # Проверка, что резерв не превышает доступное количество
        if self.qty_reserved > self.qty_total:
            raise ValidationError({
                'qty_reserved': 'Резерв не может превышать общее количество'
            })

        # Проверка минимального запаса
        if self.min_stock_level < 0:
            raise ValidationError({
                'min_stock_level': 'Минимальный запас не может быть отрицательным'
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)