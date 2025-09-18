from django.db import models

class HumanResource(models.Model):
    name = models.CharField("ФИО", max_length=255)
    job_title = models.CharField("Должность", max_length=255, blank=True)

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"

    def __str__(self):
        return f"{self.name} ({self.job_title})" if self.job_title else self.name