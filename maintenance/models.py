from django.db import models
from hr.models import HumanResource
from locations.models import Location
from assets.models import Workstation
from inventory.models import Material

class Priority(models.TextChoices):
    LOW = "low", "Низкий"
    MED = "med", "Средний"
    HIGH = "high", "Высокий"

class WorkCategory(models.TextChoices):
    INSPECTION   = "inspection",    "Осмотр"
    PM           = "pm",            "Техническое обслуживание"
    REPAIR_MINOR = "repair_minor",  "Текущий ремонт"
    REPAIR_MAJOR = "repair_major",  "Капитальный ремонт"
    EMERGENCY    = "emergency",     "Аварийный ремонт"

class WorkOrderStatus(models.TextChoices):
    NEW        = "new",         "Новое"
    IN_PROGRESS= "in_progress", "В работе"
    DONE       = "done",        "Выполнено"
    FAILED     = "failed",      "Не выполнено"
    CANCELED   = "canceled",    "Отмена"

class WorkOrder(models.Model):
    name = models.CharField("Название задачи", max_length=255)
    status = models.CharField("Статус", max_length=20, choices=WorkOrderStatus.choices, default=WorkOrderStatus.NEW)
    responsible = models.ForeignKey(HumanResource, on_delete=models.PROTECT, verbose_name="Ответственный")
    workstation = models.ForeignKey(Workstation, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Оборудование")
    location = models.ForeignKey(Location, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Локация")
    description = models.TextField("Описание", blank=True)
    category = models.CharField("Категория работ", max_length=20, choices=WorkCategory.choices, default=WorkCategory.PM)
    date_start = models.DateField("Дата начала работ", null=True, blank=True)
    date_finish = models.DateField("Дата окончания работ", null=True, blank=True)
    files = models.FileField("Файлы", upload_to="workorders/", blank=True)
    labor_plan_hours = models.FloatField("Трудоёмкость (план), ч", default=0)
    labor_fact_hours = models.FloatField("Трудоёмкость (факт), ч", default=0)
    priority = models.CharField("Приоритет", max_length=10, choices=Priority.choices, default=Priority.MED)

    class Meta:
        verbose_name = "Рабочая задача"
        verbose_name_plural = "Рабочие задачи"

    def __str__(self):
        return self.name

class WorkOrderMaterial(models.Model):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="materials", verbose_name="Задача")
    material   = models.ForeignKey(Material, on_delete=models.PROTECT, verbose_name="Материал")
    qty_planned = models.FloatField("Запланировано", default=0)
    qty_used    = models.FloatField("Использовано", default=0)

    class Meta:
        verbose_name = "Материал задачи"
        verbose_name_plural = "Материалы задач"
        unique_together = ("work_order", "material")

class PlannedFrequency(models.TextChoices):
    DAILY = "daily", "Ежедневно"
    WEEKLY = "weekly", "Еженедельно"
    MONTHLY = "monthly", "Ежемесячно"

class PlannedOrder(models.Model):
    name = models.CharField("Название планового обслуживания", max_length=255)
    responsible_default = models.ForeignKey(
        HumanResource, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name="Ответственный по умолчанию"
    )
    workstation = models.ForeignKey(Workstation, on_delete=models.PROTECT, verbose_name="Оборудование")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, verbose_name="Локация")
    description = models.TextField("Описание", blank=True)
    category = models.CharField("Категория работ", max_length=20, choices=WorkCategory.choices, default=WorkCategory.PM)
    frequency = models.CharField("Периодичность", max_length=20, choices=PlannedFrequency.choices, default=PlannedFrequency.WEEKLY)
    labor_plan_hours = models.FloatField("Трудоёмкость (план), ч", default=1.0)
    priority = models.CharField("Приоритет", max_length=10, choices=Priority.choices, default=Priority.MED)
    start_from = models.DateField("Старт планирования", null=True, blank=True)
    next_run = models.DateField("Следующий запуск", null=True, blank=True)
    is_active = models.BooleanField("Активно", default=True)

    class Meta:
        verbose_name = "Плановое обслуживание"
        verbose_name_plural = "Плановые обслуживания"

    def __str__(self):
        return self.name