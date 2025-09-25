from django.db import models

from assets.models import Workstation
from hr.models import HumanResource
from locations.models import Location


class Warehouse(models.Model):
    name = models.CharField("Название склада", max_length=255)
    responsible = models.ForeignKey(HumanResource, on_delete=models.DO_NOTHING, blank=True, null=True, verbose_name='Ответственный')
    location = models.ForeignKey(Location, on_delete=models.DO_NOTHING, blank=True, null=True, verbose_name='Локация')

    class Meta:
        verbose_name = "Склад"
        verbose_name_plural = "Склады"

    def __str__(self):
        return self.name

class MaterialUoM(models.TextChoices):
    PCS = "pcs", "шт"
    KG  = "kg", "кг"
    LTR = "l",  "л"
    MTR = "m",  "м"
    HRS = "h",  "ч"

class Material(models.Model):
    name = models.CharField("Полное наименование", max_length=255)
    group = models.CharField("Группа", max_length=255, blank=True)
    article = models.CharField("Артикул", max_length=255, blank=True)
    part_number = models.CharField("Номер детали", max_length=255, blank=True)
    uom = models.CharField("Ед. изм.", max_length=10, choices=MaterialUoM.choices, default=MaterialUoM.PCS)
    qty_available = models.FloatField("Количество (свободно)", default=0)
    qty_reserved  = models.FloatField("Количество (резерв)", default=0)
    warehouse = models.ForeignKey(Warehouse, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Склад")
    vendor = models.CharField("Производитель", max_length=255, blank=True)
    suitable_for = models.ManyToManyField(
        Workstation,
        blank=True,
        related_name="compatible_materials",
        verbose_name="Подходит для оборудования",
    )

    class Meta:
        verbose_name = "Номенклатура"
        verbose_name_plural = "Номенклатура"

    def __str__(self):
        return self.name
