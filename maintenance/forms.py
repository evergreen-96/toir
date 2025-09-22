from django import forms
from django.forms import inlineformset_factory
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

WorkOrderMaterialFormSet = inlineformset_factory(
    WorkOrder,
    WorkOrderMaterial,
    fields=["material", "qty_planned", "qty_used"],
    extra=1,
    can_delete=True,
)
