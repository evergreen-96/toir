from django import forms
from django.core.validators import MinValueValidator
from django.forms import ClearableFileInput

from .models import Warehouse, Material
from assets.models import Workstation


class BaseInventoryForm(forms.ModelForm):
    """Базовая форма для инвентаря"""

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean_name(self):
        """Базовая валидация названия"""
        name = self.cleaned_data.get('name')
        if name and len(name.strip()) < 2:
            raise forms.ValidationError("Название должно содержать минимум 2 символа")
        return name.strip()


class WarehouseForm(BaseInventoryForm):
    """Форма для склада"""

    class Meta:
        model = Warehouse
        fields = ["name", "location", "responsible"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Применение CSS классов
        self.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Введите название склада'
        })
        self.fields['location'].widget.attrs.update({
            'class': 'form-select js-select2',
            'data-placeholder': 'Выберите локацию'
        })
        self.fields['responsible'].widget.attrs.update({
            'class': 'form-select js-select2',
            'data-placeholder': 'Выберите ответственного'
        })



class ImageOnlyFileInput(ClearableFileInput):
    """
    Убираем дефолтный Django UI:
    - 'На данный момент'
    - 'Очистить [ ]'
    """
    initial_text = ''
    input_text = ''
    clear_checkbox_label = ''

class MaterialForm(BaseInventoryForm):
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
        ]
        widgets = {
            'image': ImageOnlyFileInput(),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

        # Выпадающие списки и множественный выбор
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


class MaterialSelectWithImage(forms.Select):
    """Кастомный виджет Select с изображениями материалов"""

    def create_option(
            self, name, value, label, selected, index, subindex=None, attrs=None
    ):
        option = super().create_option(
            name, value, label, selected, index, subindex=subindex, attrs=attrs
        )

        # 🔑 ВАЖНО: value — это ModelChoiceIteratorValue
        if value and hasattr(value, "value"):
            material_id = value.value

            # Получаем материал из кеша или запроса
            material = self.choices.queryset.filter(pk=material_id).first()
            if material and material.image:
                option["attrs"]["data-image"] = material.image.url
                # Добавляем класс для стилизации
                if 'class' in option["attrs"]:
                    option["attrs"]["class"] += " has-image"
                else:
                    option["attrs"]["class"] = "has-image"

        return option

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # Добавляем дополнительные данные в контекст
        context['widget']['attrs']['data-select2-images'] = 'true'
        return context


class MaterialChoiceField(forms.ModelChoiceField):
    """Кастомное поле выбора материала с виджетом изображений"""
    widget = MaterialSelectWithImage

    def __init__(self, *args, **kwargs):
        # Убедимся, что queryset включает материалы с изображениями
        if 'queryset' not in kwargs:
            from .models import Material
            kwargs['queryset'] = Material.objects.filter(is_active=True).select_related('warehouse')

        # Настройки виджета
        widget_attrs = kwargs.pop('widget_attrs', {})
        widget_attrs.update({
            'class': 'form-select js-select2-material',
            'data-placeholder': 'Выберите материал',
            'data-allow-clear': 'true',
        })

        super().__init__(*args, **kwargs)
        self.widget.attrs.update(widget_attrs)


# Формы фильтрации
class WarehouseFilterForm(forms.Form):
    """Форма фильтрации складов"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по названию склада...'
        })
    )

    location = forms.ModelChoiceField(
        queryset=None,  # Будет установлено в __init__
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select js-select2',
            'data-placeholder': 'Все локации'
        })
    )

    def __init__(self, *args, **kwargs):
        from locations.models import Location
        super().__init__(*args, **kwargs)
        self.fields['location'].queryset = Location.objects.all()


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
        queryset=Warehouse.objects.all(),
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

    group = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Группа...'
        })
    )