from django.db import models

from assets.models import Workstation


class Warehouse(models.Model):
    name = models.CharField("Название склада", max_length=255)

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
    suitable = models.ManyToManyRel()

    class Meta:
        verbose_name = "Номенклатура"
        verbose_name_plural = "Номенклатура"

    def __str__(self):
        return self.name
