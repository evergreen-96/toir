from django import forms
from django.forms import inlineformset_factory

from assets.models import Workstation
from .models import WorkOrder, WorkOrderMaterial

class WorkOrderForm(forms.ModelForm):
    class Meta:
        model = WorkOrder
        fields = [
            "name", "status", "priority", "category",
            "responsible", "workstation", "location",
            "date_start", "date_finish",
            "labor_plan_hours", "labor_fact_hours",
            "files", "description",
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
