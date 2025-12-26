from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from django.utils import timezone


class HumanResourceQuerySet(models.QuerySet):
    """Кастомный QuerySet для сотрудников"""

    def with_subordinates_count(self):
        """Сотрудники с подсчетом подчиненных"""
        return self.annotate(
            subordinates_count=models.Count('subordinates')
        )

    def managers_only(self):
        """Только руководители (имеющие подчиненных)"""
        return self.annotate(
            sub_cnt=models.Count('subordinates')
        ).filter(sub_cnt__gt=0)

    def active(self):
        """Активные сотрудники"""
        return self.filter(is_active=True)

    def by_manager(self, manager_id):
        """Сотрудники по руководителю"""
        return self.filter(manager_id=manager_id)

    def by_job_title(self, job_title):
        """Сотрудники по должности"""
        return self.filter(job_title__icontains=job_title)

    def search(self, query):
        """Поиск по ФИО и должности"""
        return self.filter(
            models.Q(name__icontains=query) |
            models.Q(job_title__icontains=query)
        )


class HumanResourceManager(models.Manager):
    """Кастомный менеджер для сотрудников"""

    def get_queryset(self):
        return HumanResourceQuerySet(self.model, using=self._db)

    def with_subordinates_count(self):
        return self.get_queryset().with_subordinates_count()

    def managers_only(self):
        return self.get_queryset().managers_only()

    def active(self):
        return self.get_queryset().active()

    def by_manager(self, manager_id):
        return self.get_queryset().by_manager(manager_id)

    def by_job_title(self, job_title):
        return self.get_queryset().by_job_title(job_title)

    def search(self, query):
        return self.get_queryset().search(query)

    def get_org_chart(self, root_id=None):
        """Получение организационной структуры"""
        queryset = self.get_queryset()
        if root_id:
            root = queryset.get(pk=root_id)
            return self._get_subtree(root)
        else:
            # Все сотрудники без руководителей (верхний уровень)
            return queryset.filter(manager__isnull=True).prefetch_related('subordinates')

    def _get_subtree(self, employee):
        """Рекурсивное получение поддерева"""
        result = {
            'id': employee.id,
            'name': employee.name,
            'job_title': employee.job_title,
            'subordinates': []
        }

        for sub in employee.subordinates.all():
            result['subordinates'].append(self._get_subtree(sub))

        return result


class HumanResource(models.Model):
    history = HistoricalRecords()

    # Основная информация
    name = models.CharField(_("ФИО"), max_length=255)
    job_title = models.CharField(_("Должность"), max_length=255, blank=True)

    # Подчиненность
    manager = models.ForeignKey(
        "self",
        verbose_name=_("Начальник"),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subordinates",
    )

    # Статус
    is_active = models.BooleanField(
        _("Активен"),
        default=True,
        help_text=_("Сотрудник работает в компании")
    )

    # Технические поля
    created_at = models.DateTimeField(_("Создан"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Обновлен"), auto_now=True)

    class Meta:
        verbose_name = _("Сотрудник")
        verbose_name_plural = _("Сотрудники")
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["job_title"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["manager", "is_active"]),
        ]

    def __str__(self):
        if self.job_title:
            return f"{self.name} — {self.job_title}"
        return self.name

    def clean(self):
        """Валидация модели"""
        super().clean()

        # Проверка циклических ссылок
        if self.pk and self.manager_id == self.pk:
            raise ValidationError({
                "manager": _("Сотрудник не может быть своим руководителем.")
            })

        # Проверка глубоких циклических ссылок (опционально)
        if self.manager:
            current = self.manager
            visited = {self.pk}

            while current:
                if current.pk in visited:
                    raise ValidationError({
                        "manager": _("Обнаружена циклическая ссылка в иерархии подчинения.")
                    })
                visited.add(current.pk)
                current = current.manager

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse("hr:hr_detail", args=[str(self.pk)])