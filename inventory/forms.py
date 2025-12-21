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
            "warehouse": forms.Select(attrs={"class": "form-select js-select2"}),

            "qty_available": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "qty_reserved": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "1",
                    "min": "0",
                }
            ),

            "suitable_for": forms.SelectMultiple(
                attrs={
                    "class": "form-select js-select2",
                    "data-placeholder": "Выберите оборудование",
                }
            ),
        }
