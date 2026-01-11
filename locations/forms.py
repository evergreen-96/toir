"""
Locations Forms
===============
"""

from django import forms
from hr.models import HumanResource
from .models import Location


class LocationForm(forms.ModelForm):
    """Форма для локации."""

    class Meta:
        model = Location
        fields = ["name", "parent", "responsible"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Название локации",
            }),
            "parent": forms.Select(attrs={
                "class": "form-select js-tom-select-parent",
            }),
            "responsible": forms.Select(attrs={
                "class": "form-select js-tom-select-responsible",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Queryset для связанных полей
        self.fields["parent"].queryset = Location.objects.all().order_by("name")
        self.fields["responsible"].queryset = HumanResource.objects.filter(
            is_active=True
        ).order_by("name")

        # Необязательные поля
        self.fields["parent"].required = False
        self.fields["responsible"].required = False

        # Исключаем текущую локацию из списка родителей (при редактировании)
        if self.instance and self.instance.pk:
            # Исключаем саму себя и всех потомков
            descendants = self._get_descendants(self.instance)
            exclude_ids = [self.instance.pk] + [d.pk for d in descendants]
            self.fields["parent"].queryset = self.fields["parent"].queryset.exclude(
                pk__in=exclude_ids
            )

    def _get_descendants(self, location):
        """Получить всех потомков локации (рекурсивно)."""
        descendants = []
        children = Location.objects.filter(parent=location)
        for child in children:
            descendants.append(child)
            descendants.extend(self._get_descendants(child))
        return descendants

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Название должно содержать минимум 2 символа")
        return name

    def clean(self):
        cleaned_data = super().clean()
        parent = cleaned_data.get("parent")

        # Проверка на циклическую зависимость
        if self.instance and self.instance.pk and parent:
            if parent.pk == self.instance.pk:
                self.add_error("parent", "Локация не может быть родителем самой себя")

            # Проверяем, не является ли parent потомком текущей локации
            descendants = self._get_descendants(self.instance)
            if parent in descendants:
                self.add_error("parent", "Нельзя выбрать потомка в качестве родителя")

        return cleaned_data