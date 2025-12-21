from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from maintenance.models import PlannedOrder, IntervalUnit, WorkOrder, Priority, WorkCategory
from hr.models import HumanResource
import logging

CATCH_UP = True

def add_interval(dt, value, unit):
    if unit == IntervalUnit.MINUTE: return dt + timedelta(minutes=value)
    if unit == IntervalUnit.DAY:    return dt + relativedelta(days=value)
    if unit == IntervalUnit.WEEK:   return dt + relativedelta(weeks=value)
    if unit == IntervalUnit.MONTH:  return dt + relativedelta(months=value)
    return dt + timedelta(minutes=value)

def round_to_minute(dt): return dt.replace(second=0, microsecond=0)

class Command(BaseCommand):
    help = "Создаёт рабочие задачи из планов по расписанию"

    logger = logging.getLogger(__name__)
    def handle(self, *args, **opts):
        now = timezone.now()
        now_rounded = round_to_minute(now)
        created = 0

        for p in PlannedOrder.objects.filter(is_active=True):
            if not p.next_run:
                if p.start_from and p.start_from > now:
                    p.next_run = round_to_minute(p.start_from)
                else:
                    first = add_interval(now_rounded, p.interval_value, p.interval_unit)
                    if p.interval_unit == IntervalUnit.MINUTE:
                        first = round_to_minute(first)
                    p.next_run = first
                p.save(update_fields=["next_run"])

            if not p.next_run:
                continue

            while p.next_run <= now:
                resp = p.responsible_default or HumanResource.objects.first()
                if not resp:
                    logger.warning("Plan %s skipped: no responsible", p.id)
                    continue
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

                nxt = add_interval(p.next_run, p.interval_value, p.interval_unit)
                if p.interval_unit == IntervalUnit.MINUTE:
                    nxt = round_to_minute(nxt)
                p.next_run = nxt

                if not CATCH_UP:
                    break

            p.save(update_fields=["next_run"])

        self.stdout.write(self.style.SUCCESS(f"Создано задач: {created}"))
