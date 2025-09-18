from datetime import date, timedelta
from django.core.management.base import BaseCommand
from maintenance.models import PlannedOrder, PlannedFrequency, WorkOrder, WorkCategory, Priority
from hr.models import HumanResource

def next_date(freq: str, current: date) -> date:
    if freq == PlannedFrequency.DAILY:
        return current + timedelta(days=1)
    if freq == PlannedFrequency.WEEKLY:
        return current + timedelta(weeks=1)
    if freq == PlannedFrequency.MONTHLY:
        return current + timedelta(days=30)  # упрощённо
    return current + timedelta(weeks=1)

class Command(BaseCommand):
    help = "Создаёт рабочие задачи из плановых обслуживаний, если настал срок"

    def handle(self, *args, **options):
        today = date.today()
        created = 0
        qs = PlannedOrder.objects.filter(is_active=True)
        for p in qs:
            if not p.next_run:
                p.next_run = p.start_from or today

            if p.next_run and p.next_run <= today:
                responsible = p.responsible_default or HumanResource.objects.first()
                if not responsible:
                    # нет ответственного — пропускаем
                    continue

                WorkOrder.objects.create(
                    name=p.name,
                    status="new",
                    responsible=responsible,
                    workstation=p.workstation,
                    location=p.location,
                    description=p.description,
                    category=p.category or WorkCategory.PM,
                    labor_plan_hours=p.labor_plan_hours,
                    priority=p.priority or Priority.MED,
                )
                p.next_run = next_date(p.frequency, today)
                p.save(update_fields=["next_run"])
                created += 1

        self.stdout.write(self.style.SUCCESS(f"Создано задач: {created}"))
