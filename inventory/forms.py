from django import forms
from .models import Warehouse, Material
from assets.models import Workstation

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ["name", "location", "responsible"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "responsible": forms.Select(attrs={"class": "form-select"}),
        }

class MaterialForm(forms.ModelForm):
    class Meta:
        model = Material
        fields = [
            "name",
            "group",
            "article",
            "part_number",
            "vendor",
            "uom",
            "qty_available",
            "qty_reserved",
            "warehouse",
            "suitable_for",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "group": forms.TextInput(attrs={"class": "form-control"}),
            "article": forms.TextInput(attrs={"class": "form-control"}),
            "part_number": forms.TextInput(attrs={"class": "form-control"}),
            "vendor": forms.TextInput(attrs={"class": "form-control"}),
            "uom": forms.Select(attrs={"class": "form-select"}),
            "warehouse": forms.Select(attrs={"class": "form-select"}),
            "suitable_for": forms.SelectMultiple(
                attrs={"class": "form-select", "size": 8}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["suitable_for"].queryset = (
            Workstation.objects.order_by("name")
        )