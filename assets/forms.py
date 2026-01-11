"""
assets/forms.py

Формы для приложения assets.
Рефакторинг: форма вынесена из views.py, наследуется от BaseModelForm.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from core.forms import BaseModelForm, BaseFilterForm
from .models import Workstation, WorkstationStatus, WorkstationCategory, WorkstationGlobalState
from locations.models import Location
from hr.models import HumanResource


class WorkstationForm(BaseModelForm):
    """Форма для создания/редактирования оборудования."""

    class Meta:
        model = Workstation
        fields = [
            "name",
            "category",
            "type_name",
            "manufacturer",
            "model",
            "global_state",
            "status",
            "description",
            "serial_number",
            "location",
            "commissioning_date",
            "warranty_until",
            "responsible",
            "photo",
            "inventory_number",
        ]
        widgets = {
            'commissioning_date': forms.DateInput(attrs={'type': 'date'}),
            'warranty_until': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'photo': forms.FileInput(attrs={'accept': 'image/*'}),
        }
        help_texts = {
            'inventory_number': _('Уникальный инвентарный номер'),
            'serial_number': _('Серийный номер от производителя'),
            'photo': _('Рекомендуемый размер: 800x600px'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['location'].queryset = Location.objects.all().order_by('name')
        self.fields['responsible'].queryset = HumanResource.objects.filter(is_active=True).order_by('name')

        # Тип оборудования — текстовое поле с TomSelect (с возможностью создания)
        self.fields['type_name'] = forms.CharField(
            label=_("Тип оборудования"),
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control js-tom-select-type',
                'data-placeholder': _('Выберите или введите тип...'),
            })
        )

    def clean_inventory_number(self):
        """Проверка уникальности инвентарного номера."""
        inventory_number = self.cleaned_data.get('inventory_number')
        if inventory_number:
            qs = Workstation.objects.filter(inventory_number=inventory_number)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(_('Оборудование с таким инвентарным номером уже существует'))
        return inventory_number

    def clean_serial_number(self):
        """Валидация серийного номера."""
        serial_number = self.cleaned_data.get('serial_number')
        if serial_number:
            qs = Workstation.objects.filter(serial_number=serial_number)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(_('Оборудование с таким серийным номером уже существует'))
        return serial_number

    def clean(self):
        """Дополнительная валидация формы."""
        cleaned_data = super().clean()

        commissioning_date = cleaned_data.get('commissioning_date')
        warranty_until = cleaned_data.get('warranty_until')

        if commissioning_date and warranty_until:
            if warranty_until < commissioning_date:
                self.add_error('warranty_until',
                               _('Дата окончания гарантии не может быть раньше даты ввода в эксплуатацию'))

        global_state = cleaned_data.get('global_state')
        status = cleaned_data.get('status')

        if global_state == WorkstationGlobalState.ARCHIVED and status != WorkstationStatus.DECOMMISSIONED:
            self.add_error('status', _('Оборудование в архиве должно иметь статус "Выведено из эксплуатации"'))

        return cleaned_data


class WorkstationSearchForm(BaseFilterForm):
    """Форма поиска оборудования."""

    q = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'placeholder': _('Название, тип, серийный номер...'), 'autofocus': True}))
    category = forms.ChoiceField(required=False, choices=[('', _('Все категории'))] + list(WorkstationCategory.choices))
    status = forms.ChoiceField(required=False, choices=[('', _('Все статусы'))] + list(WorkstationStatus.choices))
    global_state = forms.ChoiceField(required=False,
                                     choices=[('', _('Все состояния'))] + list(WorkstationGlobalState.choices))
    location = forms.ModelChoiceField(required=False, queryset=Location.objects.all(), empty_label=_('Все локации'))
    responsible = forms.ModelChoiceField(required=False, queryset=HumanResource.objects.filter(is_active=True),
                                         empty_label=_('Все ответственные'))
    warranty = forms.ChoiceField(required=False, choices=[('', _('Любая гарантия')), ('active', _('На гарантии')),
                                                          ('expired', _('Гарантия истекла'))])