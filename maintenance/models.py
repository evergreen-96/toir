from django.db import models
from django.utils import timezone

import calendar
from datetime import datetime, time, timedelta, date
from dateutil.relativedelta import relativedelta
from simple_history.models import HistoricalRecords

from hr.models import HumanResource
from locations.models import Location
from assets.models import Workstation, WorkstationStatus
from inventory.models import Material

# Плановые работы всегда стартуют в 00:00:01 выбранной даты
RUN_TIME = time(0, 0, 1)


# ---------- справочные утилиты для месячных дат ----------
def _last_day_of_month(y: int, m: int) -> int:
    return calendar.monthrange(y, m)[1]


def _clamp_dom(y: int, m: int, dom: int) -> int:
    """Если dom > числа дней в месяце — вернём последний день месяца."""
    return min(dom, _last_day_of_month(y, m))


class Priority(models.TextChoices):
    LOW = "low", "Низкий"
    MED = "med", "Средний"
    HIGH = "high", "Высокий"


class WorkCategory(models.TextChoices):
    INSPECTION = "inspection", "Осмотр"
    PM = "pm", "Техническое обслуживание"
    REPAIR_MINOR = "repair_minor", "Текущий ремонт"
    REPAIR_MAJOR = "repair_major", "Капитальный ремонт"
    EMERGENCY = "emergency", "Аварийный ремонт"


class WorkOrderStatus(models.TextChoices):
    NEW = "new", "Новое"
    IN_PROGRESS = "in_progress", "В работе"
    DONE = "done", "Выполнено"
    FAILED = "failed", "Не выполнено"
    CANCELED = "canceled", "Отмена"


class PlannedFrequency(models.TextChoices):
    DAILY = "daily", "Ежедневно"
    WEEKLY = "weekly", "Еженедельно"
    MONTHLY = "monthly", "Ежемесячно"


class IntervalUnit(models.TextChoices):
    MINUTE = "minute", "Минуты"
    DAY = "day", "Дни"
    WEEK = "week", "Недели"
    MONTH = "month", "Месяцы"


class PlannedOrder(models.Model):
    history = HistoricalRecords()
    name = models.CharField("Название планового обслуживания", max_length=255)
    responsible_default = models.ForeignKey(
        HumanResource,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Ответственный по умолчанию"
    )
    workstation = models.ForeignKey(Workstation, on_delete=models.PROTECT, verbose_name="Оборудование")
    location = models.ForeignKey(Location, on_delete=models.PROTECT, verbose_name="Локация")
    description = models.TextField("Описание", blank=True)
    category = models.CharField(
        "Категория работ",
        max_length=20,
        choices=WorkCategory.choices,
        default=WorkCategory.PM
    )

    # «для справки», основная логика — через interval_value/unit
    frequency = models.CharField(
        "Периодичность",
        max_length=20,
        choices=PlannedFrequency.choices,
        default=PlannedFrequency.WEEKLY
    )

    labor_plan_hours = models.FloatField("Трудоёмкость (план), ч", default=1.0)
    priority = models.CharField("Приоритет", max_length=10, choices=Priority.choices, default=Priority.MED)

    start_from = models.DateTimeField("Старт планирования (дата и время)", null=True, blank=True)
    next_run = models.DateTimeField("Следующий запуск (дата и время)", null=True, blank=True)
    is_active = models.BooleanField("Активно", default=True)

    interval_value = models.PositiveIntegerField(
        "Интервал (N)",
        default=1,
        help_text="Например, 3 = каждые 3 единицы времени."
    )
    interval_unit = models.CharField(
        "Единица интервала",
        max_length=10,
        choices=IntervalUnit.choices,
        default=IntervalUnit.WEEK,
        help_text="Минуты / Дни / Недели / Месяцы"
    )

    first_run_date = models.DateField("Дата первого обслуживания", null=True, blank=True)

    weekday = models.PositiveSmallIntegerField(
        "День недели",
        null=True,
        blank=True,
        help_text="0=Пн … 6=Вс"
    )

    day_of_month = models.PositiveSmallIntegerField(
        "День месяца",
        null=True,
        blank=True,
        help_text="1–31"
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

    # ---------- core: initial next_run ----------
    def compute_initial_next_run(self):
        tz = timezone.get_default_timezone()

        # --- Ежедневно ---
        # next_run = 00:00:01 выбранной даты
        if self.interval_unit == IntervalUnit.DAY and self.first_run_date:
            return timezone.make_aware(
                datetime.combine(self.first_run_date, RUN_TIME),
                tz
            )

        # --- Еженедельно ---
        # next_run = ближайший выбранный день недели (строго "следующий")
        if self.interval_unit == IntervalUnit.WEEK and self.weekday is not None:
            now = timezone.localtime()
            target_weekday = int(self.weekday)

            days_ahead = (target_weekday - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # строго "следующий", не "сегодня"

            next_date = now.date() + timedelta(days=days_ahead)
            return timezone.make_aware(
                datetime.combine(next_date, RUN_TIME),
                tz
            )

        # --- Ежемесячно ---
        # next_run = ближайшее "число месяца" (если числа нет — последний день месяца)
        if self.interval_unit == IntervalUnit.MONTH and self.day_of_month:
            now = timezone.localtime()
            y, m = now.year, now.month
            dom = int(self.day_of_month)

            d1 = _clamp_dom(y, m, dom)
            candidate = date(y, m, d1)

            if candidate <= now.date():
                nxt = now.date() + relativedelta(months=1)
                y2, m2 = nxt.year, nxt.month
                d2 = _clamp_dom(y2, m2, dom)
                candidate = date(y2, m2, d2)

            return timezone.make_aware(
                datetime.combine(candidate, RUN_TIME),
                tz
            )

        # --- fallback: текущая логика ---
        base = self._to_dt(self.start_from or timezone.now())
        dt = self._add_interval(base, self.interval_value, self.interval_unit)

        if self.interval_unit == IntervalUnit.MINUTE:
            dt = dt.replace(second=0, microsecond=0)

        return dt

    # ---------- preview (2 months forward) ----------
    def preview_runs(self, months_ahead: int = 2):
        """
        Превью дат на months_ahead месяцев вперёд.
        Возвращает (first_run_dt, runs_dt_list).
        runs_dt_list включает только те срабатывания, которые попадают в [today .. today+months_ahead].
        """
        tz = timezone.get_default_timezone()
        today = timezone.localdate()
        end = today + relativedelta(months=months_ahead)

        first_run = self.compute_initial_next_run()
        first_day = timezone.localtime(first_run).date()

        runs = []

        # Daily
        if self.interval_unit == IntervalUnit.DAY and self.first_run_date:
            cur = self.first_run_date
            while cur <= end:
                if cur >= today:
                    runs.append(timezone.make_aware(datetime.combine(cur, RUN_TIME), tz))
                cur += timedelta(days=1)
            return first_run, runs

        # Weekly
        if self.interval_unit == IntervalUnit.WEEK and self.weekday is not None:
            cur = first_day
            while cur <= end:
                runs.append(timezone.make_aware(datetime.combine(cur, RUN_TIME), tz))
                cur += timedelta(weeks=1)
            return first_run, runs

        # Monthly (с clamp на последний день месяца)
        if self.interval_unit == IntervalUnit.MONTH and self.day_of_month:
            dom = int(self.day_of_month)
            cur = first_day
            while cur <= end:
                runs.append(timezone.make_aware(datetime.combine(cur, RUN_TIME), tz))
                nxt = cur + relativedelta(months=1)
                y2, m2 = nxt.year, nxt.month
                d2 = _clamp_dom(y2, m2, dom)
                cur = date(y2, m2, d2)
            return first_run, runs

        # Custom: считаем от first_run с шагом interval_value/unit
        base = timezone.localtime(first_run)
        cur_dt = base
        safety = 0
        while timezone.localdate(cur_dt) <= end:
            if timezone.localdate(cur_dt) >= today:
                runs.append(cur_dt)
            cur_dt = self._add_interval(cur_dt, self.interval_value, self.interval_unit)
            safety += 1
            if safety > 5000:  # защита от бесконечных циклов на странных данных
                break

        return first_run, runs

    # ---------- валидация/сохранение ----------
    def clean(self):
        from django.core.exceptions import ValidationError

        # interval_value может быть None на этапе form.is_valid()
        if self.interval_value is None:
            return

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
        если пользователь его не указал: next_run = compute_initial_next_run().
        (Дальше next_run двигает планировщик / ручной run_now.)
        """
        if self.is_active and not self.next_run:
            self.next_run = self.compute_initial_next_run()
        super().save(*args, **kwargs)


class WorkOrder(models.Model):
    history = HistoricalRecords()
    name = models.CharField("Название задачи", max_length=255)

    status = models.CharField(
        "Статус",
        max_length=20,
        choices=WorkOrderStatus.choices,
        default=WorkOrderStatus.NEW
    )

    responsible = models.ForeignKey(
        HumanResource,
        on_delete=models.PROTECT,
        verbose_name="Ответственный"
    )

    workstation = models.ForeignKey(
        Workstation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Оборудование"
    )

    location = models.ForeignKey(
        Location,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="Локация"
    )

    description = models.TextField("Описание", blank=True)

    category = models.CharField(
        "Категория работ",
        max_length=20,
        choices=WorkCategory.choices,
        default=WorkCategory.PM
    )

    date_start = models.DateField("Дата начала работ", null=True, blank=True)
    date_finish = models.DateField("Дата окончания работ", null=True, blank=True)

    labor_plan_hours = models.FloatField("Трудоёмкость (план), ч", default=0)
    labor_fact_hours = models.FloatField("Трудоёмкость (факт), ч", default=0)

    priority = models.CharField(
        "Приоритет",
        max_length=10,
        choices=Priority.choices,
        default=Priority.MED
    )

    created_at = models.DateTimeField("Создано", default=timezone.now)

    createrd_from_plan = models.ForeignKey(
        PlannedOrder,
        on_delete=models.PROTECT,
        related_name="work_orders",
        null=True,
        blank=True,
        verbose_name="Плановое обслуживание",
    )

    # ===== допустимые переходы статусов =====
    ALLOWED_TRANSITIONS = {
        WorkOrderStatus.NEW: {
            WorkOrderStatus.IN_PROGRESS: "В работе",
        },
        WorkOrderStatus.IN_PROGRESS: {
            WorkOrderStatus.DONE: "Выполнено",
            WorkOrderStatus.FAILED: "Не выполнено",
            WorkOrderStatus.CANCELED: "Отмена",
        },
    }

    def set_status(self, new_status: str):
        allowed = self.get_allowed_transitions()
        if new_status not in allowed:
            raise ValueError("Недопустимый переход статуса")

        prev_status = self.status
        self.status = new_status

        if new_status == WorkOrderStatus.IN_PROGRESS and not self.date_start:
            self.date_start = timezone.localdate()

        if new_status == WorkOrderStatus.DONE and not self.date_finish:
            self.date_finish = timezone.localdate()

        # ===== УПРАВЛЕНИЕ ОБОРУДОВАНИЕМ =====
        if (
                self.workstation
                and self.category == WorkCategory.EMERGENCY
                and prev_status == WorkOrderStatus.NEW
                and new_status == WorkOrderStatus.IN_PROGRESS
        ):
            # аварийные работы стартовали → оборудование аварийное
            self.workstation.status = WorkstationStatus.PROBLEM
            self.workstation.save(update_fields=["status"])

        self.save(update_fields=["status", "date_start", "date_finish"])

    def get_allowed_transitions(self) -> dict:
        """
        Возвращает {status: label} для доступных переходов.
        Финальные статусы вернут {}.
        """
        return self.ALLOWED_TRANSITIONS.get(self.status, {})

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        super().save(*args, **kwargs)

        # ==========================================
        # БИЗНЕС-ПРАВИЛО: ТОЛЬКО ПРИ СОЗДАНИИ
        # ==========================================
        if (
                is_new
                and self.category == WorkCategory.EMERGENCY
                and self.workstation
                and self.workstation.status != WorkstationStatus.PROBLEM
        ):
            self.workstation.status = WorkstationStatus.PROBLEM
            self.workstation.save(update_fields=["status"])

    class Meta:
        verbose_name = "Рабочая задача"
        verbose_name_plural = "Рабочие задачи"

    def __str__(self):
        return self.name


class WorkOrderMaterial(models.Model):
    history = HistoricalRecords()
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="materials",
        verbose_name="Задача"
    )
    material = models.ForeignKey(Material, on_delete=models.PROTECT, verbose_name="Материал")
    qty_planned = models.FloatField("Запланировано", default=0)
    qty_used = models.FloatField("Использовано", default=0)

    class Meta:
        verbose_name = "Материал задачи"
        verbose_name_plural = "Материалы задач"
        unique_together = ("work_order", "material")


class File(models.Model):
    history = HistoricalRecords()
    file = models.FileField(upload_to="workorders/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)


class WorkOrderAttachment(models.Model):
    history = HistoricalRecords()
    work_order = models.ForeignKey(
        WorkOrder,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file = models.ForeignKey(
        File,
        on_delete=models.CASCADE,
        related_name="work_orders",
    )
    attached_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("work_order", "file")
