"""
Celery tasks для модуля maintenance.
"""

import logging
from datetime import timedelta

from celery import shared_task
from dateutil.relativedelta import relativedelta
from django.db import transaction
from django.utils import timezone

from .models import (
    PlannedOrder,
    WorkOrder,
    IntervalUnit,
)

logger = logging.getLogger(__name__)


def _add_interval(dt, val, unit):
    """
    Добавляет интервал к дате.

    Args:
        dt: Исходная дата
        val: Значение интервала
        unit: Единица измерения (IntervalUnit)

    Returns:
        Новая дата с добавленным интервалом
    """
    if unit == IntervalUnit.MINUTE:
        return dt + timedelta(minutes=val)
    if unit == IntervalUnit.DAY:
        return dt + relativedelta(days=val)
    if unit == IntervalUnit.WEEK:
        return dt + relativedelta(weeks=val)
    if unit == IntervalUnit.MONTH:
        return dt + relativedelta(months=val)
    return dt


@shared_task(
    bind=True,
    name="maintenance.tasks.generate_planned_orders_task",
    autoretry_for=(Exception,),
    retry_backoff=60,
    max_retries=3,
)
def generate_planned_orders_task(self):
    """
    Периодическая задача для создания WorkOrder из PlannedOrder.

    Раз в минуту:
    - Берёт активные планы с next_run <= now
    - Создаёт WorkOrder
    - Двигает next_run на один интервал от предыдущего next_run
    """
    logger.info("Starting planned orders generation task")

    now = timezone.now()

    qs = (
        PlannedOrder.objects
        .select_related("workstation", "location", "responsible_default")
        .filter(is_active=True, next_run__isnull=False, next_run__lte=now)
    )

    plans_count = qs.count()
    logger.info("Found %d plans ready to execute", plans_count)

    if plans_count == 0:
        return {"created": 0, "skipped": 0}

    created = 0
    skipped = 0

    for plan in qs:
        logger.debug(
            "Processing plan id=%s, next_run=%s, interval=%s %s",
            plan.id,
            plan.next_run,
            plan.interval_value,
            plan.interval_unit,
        )

        # Проверяем наличие ответственного
        if not plan.responsible_default:
            logger.warning(
                "Plan id=%s skipped: no responsible_default assigned",
                plan.id
            )
            skipped += 1
            continue

        try:
            with transaction.atomic():
                # Создаём рабочую задачу
                today = timezone.localdate()

                work_order = WorkOrder.objects.create(
                    name=plan.name,
                    responsible=plan.responsible_default,
                    workstation=plan.workstation,
                    location=plan.location,
                    category=plan.category,
                    priority=plan.priority,
                    description=plan.description,
                    labor_plan_hours=plan.labor_plan_hours,
                    date_start=today,
                    created_from_plan=plan,
                )

                logger.info(
                    "Created WorkOrder id=%s from plan id=%s",
                    work_order.id,
                    plan.id
                )

                # Вычисляем следующий запуск
                plan.next_run = _add_interval(
                    plan.next_run,
                    plan.interval_value,
                    plan.interval_unit
                )
                plan.save(update_fields=["next_run"])

                logger.debug(
                    "Plan id=%s next_run updated to %s",
                    plan.id,
                    plan.next_run
                )

                created += 1

        except Exception as e:
            logger.exception(
                "Error processing plan id=%s: %s",
                plan.id,
                str(e)
            )
            skipped += 1
            # Транзакция откатится автоматически

    logger.info(
        "Planned orders task completed: created=%d, skipped=%d",
        created,
        skipped
    )

    return {"created": created, "skipped": skipped}