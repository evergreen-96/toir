from celery import shared_task
from django.utils import timezone
from maintenance.models import PlannedOrder, PlannedFrequency, WorkOrder, Priority, WorkCategory
from hr.models import HumanResource
from datetime import timedelta

def _next_date(freq, current):
    if freq == PlannedFrequency.DAILY: return current + timedelta(days=1)
    if freq == PlannedFrequency.WEEKLY: return current + timedelta(weeks=1)
    if freq == PlannedFrequency.MONTHLY: return current + timedelta(days=30)
    return current + timedelta(weeks=1)

@shared_task
def generate_planned_orders_task():
    today = timezone.localdate()
    created = 0
    for p in PlannedOrder.objects.filter(is_active=True):
        if not p.next_run:
            p.next_run = p.start_from or today
        # одна задача в день на план — защита от дублей
        if p.next_run and p.next_run <= today:
            resp = p.responsible_default or HumanResource.objects.first()
            if not resp:
                continue
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
            p.next_run = _next_date(p.frequency, today)
            p.save(update_fields=["next_run"])
            created += 1
    return created
