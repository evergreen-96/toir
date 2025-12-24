from django.db import models
from simple_history.models import HistoricalRecords

from hr.models import HumanResource

class Location(models.Model):
    history = HistoricalRecords()
    name = models.CharField("Название локации", max_length=255)
    parent = models.ForeignKey(
        "self",
        verbose_name="Родительская локация",
        null=True, blank=True,
        on_delete=models.SET_NULL
    )
    responsible = models.ForeignKey(
        HumanResource,
        verbose_name="Ответственный",
        null=True, blank=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = "Локация"
        verbose_name_plural = "Локации"

    def __str__(self):
        return self.name

    @property
    def level(self):
        lvl = 0
        parent = self.parent
        while parent:
            lvl += 1
            parent = parent.parent
        return lvl