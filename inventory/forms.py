"""
Inventory Forms - Склады и Материалы
====================================
"""

from django import forms
from django.forms import ClearableFileInput

from hr.models import HumanResource
from locations.models import Location
from .models import Warehouse, Material


# =============================================================================
# ВИДЖЕТЫ
# =============================================================================

class ImagePreviewInput(ClearableFileInput):
    """Виджет загрузки изображения без лишнего Django UI."""
    initial_text = ""
    input_text = ""
    clear_checkbox_label = ""
    template_name = "django/forms/widgets/clearable_file_input.html"


class MaterialSelectWithImage(forms.Select):
    """
    Кастомный виджет Select с data-атрибутами для изображений материалов.
    Используется с Tom Select для отображения превью.
    """
    
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )
        
        if value and hasattr(value, "value"):
            material_id = value.value
            material = self.choices.queryset.filter(pk=material_id).first()
            
            if material:
                if material.image:
                    option["attrs"]["data-image"] = material.image.url
                option["attrs"]["data-stock"] = str(material.qty_available)
                option["attrs"]["data-uom"] = material.get_uom_display()
        
        return option


# =============================================================================
# WAREHOUSE FORM
# =============================================================================

class WarehouseForm(forms.ModelForm):
    """Форма для склада."""
    
    class Meta:
        model = Warehouse
        fields = ["name", "location", "responsible"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Введите название склада",
            }),
            "location": forms.Select(attrs={
                "class": "form-select js-tom-select-location",
            }),
            "responsible": forms.Select(attrs={
                "class": "form-select js-tom-select-responsible",
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Queryset для связанных полей
        self.fields["location"].queryset = Location.objects.all().order_by("name")
        self.fields["responsible"].queryset = HumanResource.objects.filter(
            is_active=True
        ).order_by("name")
        
        # Необязательные поля
        self.fields["location"].required = False
        self.fields["responsible"].required = False
    
    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Название должно содержать минимум 2 символа")
        return name


# =============================================================================
# MATERIAL FORM
# =============================================================================

class MaterialForm(forms.ModelForm):
    """Форма для материала."""
    
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
            "min_stock_level",
            "warehouse",
            "suitable_for",
            "image",
            # "is_active",
            "notes",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Полное наименование материала",
            }),
            "group": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Группа материалов",
            }),
            "article": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Артикул",
            }),
            "part_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Номер детали / OEM",
            }),
            "vendor": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Производитель",
            }),
            "uom": forms.Select(attrs={
                "class": "form-select",
            }),
            "qty_available": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
            }),
            "qty_reserved": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
            }),
            "min_stock_level": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
                "placeholder": "Мин. запас для уведомлений",
            }),
            "warehouse": forms.Select(attrs={
                "class": "form-select js-tom-select-warehouse",
            }),
            "suitable_for": forms.SelectMultiple(attrs={
                "class": "form-select js-tom-select-workstations",
            }),
            "image": ImagePreviewInput(attrs={
                "class": "form-control",
                "accept": "image/*",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Дополнительные примечания...",
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Queryset для связанных полей
        self.fields["warehouse"].queryset = Warehouse.objects.all().order_by("name")
        
        from assets.models import Workstation
        self.fields["suitable_for"].queryset = Workstation.objects.all().order_by("name")
        
        # обязательные поля
        req_fields = [
            "group", "article", "part_number", "vendor",
            "warehouse", "suitable_for", "image", "notes",
            "min_stock_level", 'qty_available', 'qty_reserved',
        ]
        for field in req_fields:
            self.fields[field].required = False

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if len(name) < 2:
            raise forms.ValidationError("Название должно содержать минимум 2 символа")
        return name
    
    # def clean(self):
    #     cleaned_data = super().clean()
    #     qty_available = cleaned_data.get("qty_available")
    #     qty_reserved = cleaned_data.get("qty_reserved")
    #
        # if qty_reserved and qty_available and qty_reserved > qty_available:
        #     self.add_error(
        #         "qty_reserved",
        #         "Резерв не может превышать доступное количество"
        #     )
    #
    #     return cleaned_data
