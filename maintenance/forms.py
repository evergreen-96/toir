from django import forms
from django.forms import inlineformset_factory

from assets.models import Workstation
from .models import WorkOrder, WorkOrderMaterial

from django import forms

class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultiFileField(forms.FileField):
    widget = MultiFileInput

    def clean(self, data, initial=None):
        # data может быть списком UploadedFile
        if data is None:
            return []
        if isinstance(data, (list, tuple)):
            return [super().clean(d, initial) for d in data]
        return [super().clean(data, initial)]

class WorkOrderForm(forms.ModelForm):
    files = MultiFileField(label="Файлы", required=False)

    class Meta:
        model = WorkOrder
        fields = [
            "name", "priority", "category", "responsible",
            "workstation", "location",
            "date_start", "date_finish",
            "labor_plan_hours", "labor_fact_hours",
            "description",
            # ⚠️ НЕ включай "files" в Meta.fields, это не поле модели
        ]
        widgets = {
            "date_start": forms.DateInput(attrs={"type": "date"}),
            "date_finish": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Изначально оборудование — пустой список (или можно оставить все, но лучше пустой)
        self.fields['workstation'].queryset = Workstation.objects.none()

        # Если форма редактируется и у задачи уже есть локация — покажем оборудование для неё
        if 'location' in self.data:
            try:
                location_id = int(self.data.get('location'))
                self.fields['workstation'].queryset = Workstation.objects.filter(location_id=location_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.location:
            self.fields['workstation'].queryset = Workstation.objects.filter(location=self.instance.location)

WorkOrderMaterialFormSet = inlineformset_factory(
    WorkOrder,
    WorkOrderMaterial,
    fields=["material", "qty_planned", "qty_used"],
    extra=0,
    can_delete=True,
)
