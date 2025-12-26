from django.db.models.signals import post_save, pre_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Workstation
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Workstation)
def workstation_pre_save(sender, instance, **kwargs):
    """Перед сохранением оборудования"""

    # Логирование изменений
    if instance.pk:
        try:
            old_instance = Workstation.objects.get(pk=instance.pk)

            # Логируем изменение статуса
            if old_instance.status != instance.status:
                logger.info(
                    f"Статус оборудования '{instance.name}' изменен: "
                    f"{old_instance.get_status_display()} → {instance.get_status_display()}"
                )

            # Логируем изменение локации
            if old_instance.location_id != instance.location_id:
                logger.info(
                    f"Локация оборудования '{instance.name}' изменена: "
                    f"{old_instance.location} → {instance.location}"
                )

        except Workstation.DoesNotExist:
            pass

    # Автоматическая установка глобального состояния при изменении статуса
    if instance.status == 'decommissioned' and instance.global_state == 'active':
        instance.global_state = 'decommissioned'


@receiver(post_save, sender=Workstation)
def workstation_post_save(sender, instance, created, **kwargs):
    """После сохранения оборудования"""

    if created:
        logger.info(f"Создано новое оборудование: {instance.name} (ID: {instance.pk})")
    else:
        logger.info(f"Обновлено оборудование: {instance.name} (ID: {instance.pk})")


@receiver(pre_delete, sender=Workstation)
def workstation_pre_delete(sender, instance, **kwargs):
    """Перед удалением оборудования"""
    logger.warning(f"Удаление оборудования: {instance.name} (ID: {instance.pk})")