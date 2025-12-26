from django.db import models
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


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
        from .models import WorkstationStatus, WorkstationGlobalState

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
            'responsible__user',
            'created_by'
        )