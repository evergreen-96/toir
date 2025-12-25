from django import forms
from .models import Warehouse, Material
from assets.models import Workstation
from django.forms import Select


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
            "image",
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

class MaterialSelectWithImage(Select):
    def create_option(
        self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )

        # 🔑 ВАЖНО: value — это ModelChoiceIteratorValue
        if value and hasattr(value, "value"):
            material_id = value.value

            material = self.choices.queryset.filter(pk=material_id).first()
            if material and material.image:
                option["attrs"]["data-image"] = material.image.url

        return option