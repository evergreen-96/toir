from django import forms
from ..models import Warehouse


class WarehouseForm(forms.ModelForm):
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

    def clean_name(self):
        """Валидация названия склада"""
        name = self.cleaned_data.get('name')
        if name and len(name.strip()) < 2:
            raise forms.ValidationError("Название должно содержать минимум 2 символа")
        return name.strip()


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