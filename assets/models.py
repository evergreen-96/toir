from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from django.utils import timezone
from django.db.models import Q, Count  # Добавляем импорт

from locations.models import Location
from hr.models import HumanResource


class WorkstationCategory(models.TextChoices):
    MAIN = "main", _("Основное")
    AUX = "aux", _("Вспомогательное")
    MEAS = "meas", _("Контрольно-измерительное")
    TEST = "test", _("Испытательное")
    OTHER = "other", _("Другое")


class WorkstationGlobalState(models.TextChoices):
    ACTIVE = "active", _("Введено в эксплуатацию")
    ARCHIVED = "arch", _("В архиве")
    RESERVE = "reserve", _("Резерв")
    DECOMMISSIONED = "decommissioned", _("Выведено из эксплуатации")


class WorkstationStatus(models.TextChoices):
    PROD = "prod", _("Работает")
    PROBLEM = "problem", _("Аварийный ремонт")
    MAINT = "maint", _("Техническое обслуживание")
    SETUP = "setup", _("Пусконаладочные работы")
    RESERVED = "reserved", _("В резерве")
    DECOMMISSIONED = "decommissioned", _("Выведено из эксплуатации")


class WorkstationManager(models.Manager):
    """Кастомный менеджер для оборудования"""

    def active(self):
        """Активное оборудование"""
        return self.filter(
            global_state='active',
            status='prod'
        )

    def needs_attention(self):
        """Оборудование, требующее внимания"""
        return self.filter(
            Q(status='problem') |
            Q(status='maint')
        )

    def under_warranty(self):
        """Оборудование на гарантии"""
        return self.filter(
            warranty_until__gte=timezone.now().date()
        )

    def expired_warranty(self):
        """Оборудование с истекшей гарантией"""
        return self.filter(
            warranty_until__lt=timezone.now().date()
        )

    def by_location(self, location_id):
        """Оборудование по локации"""
        return self.filter(location_id=location_id)

    def by_responsible(self, responsible_id):
        """Оборудование по ответственному"""
        return self.filter(responsible_id=responsible_id)

    def get_statistics(self):
        """Статистика по оборудованию"""
        stats = {
            'total': self.count(),
            'by_status': dict(
                self.values_list('status').annotate(count=Count('id'))
            ),
            'by_category': dict(
                self.values_list('category').annotate(count=Count('id'))
            ),
            'by_global_state': dict(
                self.values_list('global_state').annotate(count=Count('id'))
            ),
            'under_warranty': self.under_warranty().count(),
            'needs_attention': self.needs_attention().count(),
        }

        return stats

    def with_related(self):
        """Оптимизация запросов с select_related"""
        return self.select_related(
            'location',
            'responsible',
            'responsible__manager',  # Используем существующие поля
            'created_by'
        )


class Workstation(models.Model):
    history = HistoricalRecords()

    # Основная информация
    name = models.CharField(_("Название оборудования"), max_length=255)
    category = models.CharField(
        _("Категория оборудования"),
        max_length=20,
        choices=WorkstationCategory.choices,
        default=WorkstationCategory.MAIN,
    )
    type_name = models.CharField(_("Тип оборудования"), max_length=255)
    manufacturer = models.CharField(_("Производитель"), max_length=255, blank=True)
    model = models.CharField(_("Модель"), max_length=255, blank=True)

    # Состояния
    global_state = models.CharField(
        _("Глобальное состояние"),
        max_length=20,
        choices=WorkstationGlobalState.choices,
        default=WorkstationGlobalState.ACTIVE,
    )

    status = models.CharField(
        _("Текущее состояние"),
        max_length=20,
        choices=WorkstationStatus.choices,
        default=WorkstationStatus.PROD,
    )

    # Идентификация
    serial_number = models.CharField(
        _("Серийный номер"),
        max_length=255,
        blank=True,
        db_index=True,
    )

    inventory_number = models.CharField(
        _("Инвентарный номер"),
        max_length=255,
        blank=True,
        db_index=True,
        unique=True,
        null=True,
    )

    # Расположение и ответственность
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        verbose_name=_("Локация"),
        related_name="workstations",
    )

    responsible = models.ForeignKey(
        HumanResource,
        on_delete=models.SET_NULL,
        verbose_name=_("Ответственный"),
        null=True,
        blank=True,
        related_name="responsible_workstations",
    )

    # Эксплуатация
    commissioning_date = models.DateField(
        _("Дата ввода в эксплуатацию"),
        null=True,
        blank=True,
    )

    warranty_until = models.DateField(
        _("Гарантия до"),
        null=True,
        blank=True,
    )

    # Дополнительная информация
    description = models.TextField(_("Описание"), blank=True)

    photo = models.ImageField(
        _("Фотография"),
        upload_to="workstations/%Y/%m/%d/",
        blank=True,
        max_length=500,
    )

    # Технические поля
    created_at = models.DateTimeField(_("Создано"), auto_now_add=True)
    updated_at = models.DateTimeField(
        _("Обновлено"),
        auto_now=True,
    )
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        verbose_name=_("Создал"),
        null=True,
        blank=True,
        related_name="created_workstations",
    )

    objects = WorkstationManager()  # Используем кастомный менеджер

    class Meta:
        verbose_name = _("Оборудование")
        verbose_name_plural = _("Оборудование")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["status", "global_state"]),
            models.Index(fields=["location", "category"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["serial_number", "manufacturer"],
                name="unique_serial_manufacturer",
                condition=~models.Q(serial_number=""),
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        """Валидация модели"""
        super().clean()

        # Проверка дат
        if self.commissioning_date and self.warranty_until:
            if self.warranty_until < self.commissioning_date:
                raise ValidationError(
                    _("Дата окончания гарантии не может быть раньше даты ввода в эксплуатацию")
                )

        # Проверка статусов
        if (self.global_state == WorkstationGlobalState.ARCHIVED and
                self.status != WorkstationStatus.DECOMMISSIONED):
            raise ValidationError(
                _("Оборудование в архиве должно иметь статус 'Выведено из эксплуатации'")
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def is_under_warranty(self):
        """Находится ли оборудование на гарантии"""
        from django.utils.timezone import now
        if not self.warranty_until:
            return False
        return self.warranty_until >= now().date()

    @property
    def age_in_years(self):
        """Возраст оборудования в годах"""
        from django.utils.timezone import now

        if not self.commissioning_date:
            return None

        today = now().date()
        years = today.year - self.commissioning_date.year

        # Учитываем месяц и день
        if (today.month, today.day) < (self.commissioning_date.month, self.commissioning_date.day):
            years -= 1

        return years

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("assets:asset_detail", args=[str(self.pk)])