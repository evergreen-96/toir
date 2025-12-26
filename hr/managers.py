from django.db import models
from django.db.models import Count, Q
from django.utils import timezone


class HumanResourceManager(models.Manager):
    """Кастомный менеджер для сотрудников"""

    def with_subordinates_count(self):
        """Сотрудники с подсчетом подчиненных"""
        return self.annotate(
            subordinates_count=Count('subordinates')
        )

    def managers_only(self):
        """Только руководители (имеющие подчиненных)"""
        return self.annotate(
            sub_cnt=Count('subordinates')
        ).filter(sub_cnt__gt=0)

    def active(self):
        """Активные сотрудники"""
        return self.filter(is_active=True)

    def by_department(self, department_id):
        """Сотрудники по отделу (если будет добавлено поле department)"""
        return self.filter(department_id=department_id)

    def by_job_title(self, job_title):
        """Сотрудники по должности"""
        return self.filter(job_title=job_title)

    def get_org_chart(self, root_id=None):
        """Получение организационной структуры"""
        if root_id:
            root = self.get(pk=root_id)
            return self._get_subtree(root)
        else:
            # Все сотрудники без руководителей (верхний уровень)
            return self.filter(manager__isnull=True).prefetch_related('subordinates')

    def _get_subtree(self, employee):
        """Рекурсивное получение поддерева"""
        result = {
            'employee': employee,
            'subordinates': []
        }

        for sub in employee.subordinates.all():
            result['subordinates'].append(self._get_subtree(sub))

        return result