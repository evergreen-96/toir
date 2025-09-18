from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import WorkOrder

@receiver(pre_save, sender=WorkOrder)
def autofill_location_from_ws(sender, instance: WorkOrder, **kwargs):
    if instance.workstation and not instance.location:
        instance.location = instance.workstation.location
