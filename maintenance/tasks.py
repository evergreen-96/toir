from celery import shared_task
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from .models import PlannedOrder, WorkOrder, WorkCategory, Priority, IntervalUnit
from hr.models import HumanResource


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


@shared_task(name="maintenance.tasks.generate_planned_orders_task")
def generate_planned_orders_task():
    """
    Раз в минуту:
    - берём активные планы с next_run <= now
    - создаём WorkOrder
    - двигаем next_run ровно на один интервал ОТ предыдущего next_run
      (не «догоняем» пропуски, не привязываемся к now)
    """
    now = timezone.now()
    qs = (PlannedOrder.objects
          .select_related("workstation", "location", "responsible_default")
          .filter(is_active=True, next_run__isnull=False, next_run__lte=now))

    created = 0
    for p in qs:
        with transaction.atomic():
            resp = p.responsible_default or HumanResource.objects.first()
            if resp:
                WorkOrder.objects.create(
                    name=p.name,
                    responsible=resp,
                    workstation=p.workstation,
                    location=p.location,
                    description=p.description,
                    category=p.category or WorkCategory.PM,
                    labor_plan_hours=p.labor_plan_hours,
                    priority=p.priority or Priority.MED,
                )
                created += 1

            # сдвиг на ОДИН интервал от предыдущего времени срабатывания
            next_due = _add_interval(p.next_run, p.interval_value, p.interval_unit)
            if p.interval_unit == IntervalUnit.MINUTE:
                next_due = next_due.replace(second=0, microsecond=0)
            p.next_run = next_due
            p.save(update_fields=["next_run"])

    return created
