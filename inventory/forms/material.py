from django import forms
from django.core.validators import MinValueValidator

from inventory.models import Material, MaterialUoM  # Абсолютный импорт


class MaterialForm(forms.ModelForm):
    """Форма для материала"""

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
            "is_active",
            "min_stock_level",
            "notes",
        ]

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.request = request

        # Настройка виджетов
        text_fields = ['name', 'group', 'article', 'part_number', 'vendor']
        for field in text_fields:
            self.fields[field].widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Введите {self.fields[field].label.lower()}'
            })

        # Числовые поля
        self.fields['qty_available'].widget.attrs.update({
            'class': 'form-control',
            'step': '0.01',
            'min': '0'
        })
        self.fields['qty_reserved'].widget.attrs.update({
            'class': 'form-control',
            'step': '1',
            'min': '0'
        })
        self.fields['min_stock_level'].widget.attrs.update({
            'class': 'form-control',
            'step': '0.01',
            'min': '0'
        })

        # Выпадающие списки
        self.fields['uom'].widget.attrs.update({
            'class': 'form-select'
        })
        self.fields['warehouse'].widget.attrs.update({
            'class': 'form-select js-select2',
            'data-placeholder': 'Выберите склад'
        })
        self.fields['suitable_for'].widget.attrs.update({
            'class': 'form-select js-select2',
            'data-placeholder': 'Выберите оборудование',
            'multiple': 'multiple'
        })

        # Чекбокс
        self.fields['is_active'].widget.attrs.update({
            'class': 'form-check-input'
        })

        # Текстовое поле
        self.fields['notes'].widget.attrs.update({
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Введите примечания...'
        })

        # Поле изображения
        self.fields['image'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'image/*'
        })

    def clean(self):
        """Валидация взаимоотношений между полями"""
        cleaned_data = super().clean()
        qty_available = cleaned_data.get('qty_available')
        qty_reserved = cleaned_data.get('qty_reserved')

        if qty_reserved and qty_available and qty_reserved > qty_available:
            raise forms.ValidationError({
                'qty_reserved': 'Резерв не может превышать доступное количество'
            })

        return cleaned_data


class MaterialFilterForm(forms.Form):
    """Форма фильтрации материалов"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по названию, артикулу...'
        })
    )

    warehouse = forms.ModelChoiceField(
        queryset=None,  # Будет установлено в __init__
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select js-select2',
            'data-placeholder': 'Все склады'
        })
    )

    is_active = forms.ChoiceField(
        choices=[('', 'Все'), ('1', 'Активные'), ('0', 'Неактивные')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    stock_status = forms.ChoiceField(
        choices=[
            ('', 'Все'),
            ('in_stock', 'В наличии'),
            ('low_stock', 'Низкий запас'),
            ('out_of_stock', 'Отсутствует'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    group = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Группа...'
        })
    )

    def __init__(self, *args, **kwargs):
        from ..models import Warehouse
        super().__init__(*args, **kwargs)
        self.fields['warehouse'].queryset = Warehouse.objects.all()


class MaterialSelectWithImage(forms.Select):
    """Кастомный виджет Select с изображениями материалов"""

    def create_option(
            self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )

        if value and hasattr(value, "value"):
            material_id = value.value
            material = self.choices.queryset.filter(pk=material_id).first()
            if material and material.image:
                option["attrs"]["data-image"] = material.image.url
                option["attrs"]["data-stock"] = material.qty_available
                option["attrs"]["data-uom"] = material.get_uom_display()

        return option