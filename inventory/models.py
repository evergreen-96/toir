from django.db import models
from django.urls import reverse
from simple_history.models import HistoricalRecords
from django.core.validators import MinValueValidator

from assets.models import Workstation
from hr.models import HumanResource
from locations.models import Location


class Warehouse(models.Model):
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


class MaterialUoM(models.TextChoices):
    PCS = "pcs", "шт"
    KG = "kg", "кг"
    LTR = "l", "л"
    MTR = "m", "м"
    HRS = "h", "ч"
    SET = "set", "комплект"
    ROLL = "roll", "рулон"


class Material(models.Model):
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
        verbose_name="Склад"
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
        upload_to="materials/",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Номенклатура"
        verbose_name_plural = "Номенклатура"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['article']),
            models.Index(fields=['part_number']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

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

    def get_absolute_url(self):
        return reverse('inventory:material_detail', args=[self.pk])

    def clean(self):
        """Валидация на уровне модели"""
        from django.core.exceptions import ValidationError

        if self.qty_reserved > self.qty_total:
            raise ValidationError({
                'qty_reserved': 'Резерв не может превышать общее количество'
            })

    def save(self, *args, **kwargs):
        self.full_clean()  # Вызов валидации перед сохранением
        super().save(*args, **kwargs)