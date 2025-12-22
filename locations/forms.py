from django import forms
from .models import Location
from hr.models import HumanResource


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ["name", "parent", "responsible"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Например: Цех №1"
            }),
            "parent": forms.Select(attrs={
                "class": "form-select js-select2",
                "data-placeholder": "Без родителя"
            }),
            "responsible": forms.Select(attrs={
                "class": "form-select js-select2",
                "data-placeholder": "Не назначен"
            }),
        }

    def clean_parent(self):
        parent = self.cleaned_data.get("parent")
        obj = self.instance

        while parent:
            if parent == obj:
                raise forms.ValidationError("Циклическая иерархия локаций запрещена.")
            parent = parent.parent

        return self.cleaned_data.get("parent")
