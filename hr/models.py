from django.db import models
from django.core.exceptions import ValidationError
from simple_history.models import HistoricalRecords


class HumanResource(models.Model):
    history = HistoricalRecords()
    name = models.CharField("ФИО", max_length=255)
    job_title = models.CharField("Должность", max_length=255, blank=True)
    manager = models.ForeignKey(
        "self",
        verbose_name="Начальник",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="subordinates",
    )

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

    def __str__(self):
        if self.job_title:
            return f"{self.name} — {self.job_title}"
        return self.name

    def clean(self):
        if self.pk and self.manager_id == self.pk:
            raise ValidationError({
                "manager": "Сотрудник не может быть своим руководителем."
            })