from django.db import models
from django.core.exceptions import ValidationError

class HumanResource(models.Model):
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
        return f"{self.name} ({self.job_title})" if self.job_title else self.name

    def clean(self):
        # запретим назначать себя же начальником
        if self.pk and self.manager_id == self.pk:
            raise ValidationError({"manager": "Сотрудник не может быть своим начальником."})