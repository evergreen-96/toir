from django import forms


class BaseInventoryForm(forms.ModelForm):
    """Базовая форма для инвентаря"""

    def __init__(self, *args, **kwargs):
        # Попытаемся получить request из kwargs
        self.request = kwargs.pop('request', None)
        # Вызовем родительский __init__
        super().__init__(*args, **kwargs)

    def clean_name(self):
        """Базовая валидация названия"""
        name = self.cleaned_data.get('name')
        if name and len(name.strip()) < 2:
            raise forms.ValidationError("Название должно содержать минимум 2 символа")
        return name.strip()