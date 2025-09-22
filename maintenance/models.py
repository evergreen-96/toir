from django.db import models
from django.utils import timezone
from datetime import datetime, time, timedelta
from dateutil.relativedelta import relativedelta

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
    NEW         = "new",         "Новое"
    IN_PROGRESS = "in_progress", "В работе"
    DONE        = "done",        "Выполнено"
    FAILED      = "failed",      "Не выполнено"
    CANCELED    = "canceled",    "Отмена"


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
    DAILY   = "daily",   "Ежедневно"
    WEEKLY  = "weekly",  "Еженедельно"
    MONTHLY = "monthly", "Ежемесячно"


class IntervalUnit(models.TextChoices):
    MINUTE = "minute", "Минуты"
    DAY    = "day",    "Дни"
    WEEK   = "week",   "Недели"
    MONTH  = "month",  "Месяцы"


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

    # «для справки», основная логика — через interval_value/unit
    frequency = models.CharField("Периодичность", max_length=20,
                                 choices=PlannedFrequency.choices, default=PlannedFrequency.WEEKLY)

    labor_plan_hours = models.FloatField("Трудоёмкость (план), ч", default=1.0)
    priority = models.CharField("Приоритет", max_length=10, choices=Priority.choices, default=Priority.MED)

    start_from = models.DateTimeField("Старт планирования (дата и время)", null=True, blank=True)
    next_run   = models.DateTimeField("Следующий запуск (дата и время)", null=True, blank=True)
    is_active  = models.BooleanField("Активно", default=True)

    interval_value = models.PositiveIntegerField(
        "Интервал (N)", default=1,
        help_text="Например, 3 = каждые 3 единицы времени."
    )
    interval_unit = models.CharField(
        "Единица интервала", max_length=10,
        choices=IntervalUnit.choices, default=IntervalUnit.WEEK,
        help_text="Минуты / Дни / Недели / Месяцы"
    )

    # ---------- утилиты ----------
    @staticmethod
    def _to_dt(val):
        """date|datetime -> aware datetime (локальная TZ), без микросекунд."""
        tz = timezone.get_default_timezone()
        if isinstance(val, datetime):
            dt = val if timezone.is_aware(val) else timezone.make_aware(val, tz)
        else:
            dt = timezone.make_aware(datetime.combine(val, time.min), tz)
        return dt.replace(microsecond=0)

    @staticmethod
    def _add_interval(dt, val, unit):
        if unit == IntervalUnit.MINUTE:
            return dt + timedelta(minutes=val)
        if unit == IntervalUnit.DAY:
            return dt + relativedelta(days=val)
        if unit == IntervalUnit.WEEK:
            return dt + relativedelta(weeks=val)
        if unit == IntervalUnit.MONTH:
            return dt + relativedelta(months=val)
        return dt

    def compute_initial_next_run(self):
        """
        Первый расчёт next_run при создании:
        - если start_from задан → next_run = start_from + interval
        - иначе next_run = округлённый now + interval
        Для минут выравниваем секунды до :00.
        """
        base = self._to_dt(self.start_from or timezone.now())
        if self.interval_unit == IntervalUnit.MINUTE:
            base = base.replace(second=0, microsecond=0)
        return self._add_interval(base, self.interval_value, self.interval_unit)

    # ---------- валидация/сохранение ----------
    def clean(self):
        from django.core.exceptions import ValidationError
        if self.interval_value < 1:
            raise ValidationError({"interval_value": "Интервал должен быть ≥ 1"})

    class Meta:
        verbose_name = "Плановое обслуживание"
        verbose_name_plural = "Плановые обслуживания"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        При первом сохранении активного плана проставляем next_run,
        если пользователь его не указал: next_run = base + interval.
        (Дальше это поле двигает только планировщик: +interval от предыдущего next_run.)
        """
        if self.is_active and not self.next_run:
            self.next_run = self.compute_initial_next_run()
        super().save(*args, **kwargs)
