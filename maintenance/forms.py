from django import forms
from django.forms import inlineformset_factory

from assets.models import Workstation
from .models import WorkOrder, WorkOrderMaterial


# =====================================================
# Multi-file upload (не модельное поле)
# =====================================================

class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultiFileField(forms.FileField):
    widget = MultiFileInput

    def clean(self, data, initial=None):
        if data is None:
            return []

        if isinstance(data, (list, tuple)):
            return [super().clean(d, initial) for d in data]

        return [super().clean(data, initial)]


# =====================================================
# WorkOrder form
# =====================================================

class WorkOrderForm(forms.ModelForm):
    files = MultiFileField(label="Файлы", required=False)

    class Meta:
        model = WorkOrder
        fields = [
            "name",
            "priority",
            "category",
            "responsible",
            "location",
            "workstation",
            "date_start",
            "date_finish",
            "labor_plan_hours",
            "labor_fact_hours",
            "description",
        ]
        widgets = {
            "date_start": forms.DateInput(attrs={"type": "date"}),
            "date_finish": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # по умолчанию оборудование пустое
        self.fields["workstation"].queryset = Workstation.objects.none()

        # если форма сабмитится и есть location
        if "location" in self.data:
            try:
                location_id = int(self.data.get("location"))
                self.fields["workstation"].queryset = (
                    Workstation.objects.filter(location_id=location_id)
                )
            except (TypeError, ValueError):
                pass

        # если редактирование существующей заявки
        elif self.instance.pk and self.instance.location:
            self.fields["workstation"].queryset = (
                Workstation.objects.filter(location=self.instance.location)
            )


# =====================================================
# Material form (КЛЮЧЕВАЯ ЧАСТЬ)
# =====================================================

class WorkOrderMaterialForm(forms.ModelForm):
    class Meta:
        model = WorkOrderMaterial
        fields = ["material", "qty_planned", "qty_used"]

    def clean(self):
        cleaned = super().clean()

        # 🔑 если строка помечена на удаление —
        # пропускаем любую валидацию
        if self.cleaned_data.get("DELETE"):
            return cleaned

        return cleaned


# =====================================================
# Material formset
# =====================================================

WorkOrderMaterialFormSet = inlineformset_factory(
    WorkOrder,
    WorkOrderMaterial,
    form=WorkOrderMaterialForm,
    extra=0,
    can_delete=True,
    min_num=0,
    validate_min=False,
)
