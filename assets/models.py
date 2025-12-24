from django.db import models
from simple_history.models import HistoricalRecords

from locations.models import Location
from hr.models import HumanResource

class WorkstationCategory(models.TextChoices):
    MAIN = "main", "Основное"
    AUX  = "aux", "Вспомогательное"
    MEAS = "meas", "Контрольно-измерительное"
    TEST = "test", "Испытательное"
    OTHER = "other", "Другое"

class WorkstationGlobalState(models.TextChoices):
    ACTIVE = "active", "Введено в эксплуатацию"
    ARCHIVED = "arch", "В архиве"

class WorkstationStatus(models.TextChoices):
    PROD = "prod", "Работает"
    PROBLEM = "problem", "Аварийный ремонт"
    MAINT = "maint", "Техническое обслуживание"
    SETUP = "setup", "Пусконаладочные работы"

class Workstation(models.Model):
    history = HistoricalRecords()
    name = models.CharField("Название оборудования", max_length=255)
    category = models.CharField(
        "Категория оборудования",
        max_length=20,
        choices=WorkstationCategory.choices,
        default=WorkstationCategory.MAIN,
    )
    type_name = models.CharField("Тип оборудования", max_length=255)  # пока просто строка
    manufacturer = models.CharField("Производитель", max_length=255, blank=True)
    model = models.CharField("Модель", max_length=255, blank=True)
    global_state = models.CharField(
        "Глобальное состояние",
        max_length=20,
        choices=WorkstationGlobalState.choices,
        default=WorkstationGlobalState.ACTIVE,

    )
    status = models.CharField(
        "Текущее состояние",
        max_length=20,
        choices=WorkstationStatus.choices,
        default=WorkstationStatus.PROD,
    )
    description = models.TextField("Описание", blank=True)
    serial_number = models.CharField("Серийный номер", max_length=255, blank=True)

    # локация обязательна, чтобы всегда понимать «где стоит»
    location = models.ForeignKey(Location, on_delete=models.PROTECT, verbose_name="Локация")

    commissioning_date = models.DateField("Дата ввода в эксплуатацию", null=True, blank=True)
    warranty_until = models.DateField("Гарантия до", null=True, blank=True)
    responsible = models.ForeignKey(
        HumanResource, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Ответственный"
    )

    # если не ставил Pillow — можешь временно закомментировать след. строку
    photo = models.ImageField("Фотография", upload_to="workstations/", blank=True)

    inventory_number = models.CharField("Инвентарный номер", max_length=255, blank=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)

    class Meta:
        verbose_name = "Оборудование"
        verbose_name_plural = "Оборудование"

    def __str__(self):
        return self.name
