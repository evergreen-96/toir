from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Workstation, WorkstationStatus, WorkstationCategory, WorkstationGlobalState


class WorkstationSearchForm(forms.Form):
    """Форма поиска оборудования"""
    q = forms.CharField(
        label=_("Поиск"),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': _("Название, тип, модель..."),
            'class': 'form-control',
        })
    )

    category = forms.ChoiceField(
        label=_("Категория"),
        required=False,
        choices=[('', _("Все категории"))] + list(WorkstationCategory.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    status = forms.ChoiceField(
        label=_("Статус"),
        required=False,
        choices=[('', _("Все статусы"))] + list(WorkstationStatus.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    global_state = forms.ChoiceField(
        label=_("Глобальное состояние"),
        required=False,
        choices=[('', _("Все состояния"))] + list(WorkstationGlobalState.choices),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    location = forms.ModelChoiceField(
        label=_("Локация"),
        required=False,
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    responsible = forms.ModelChoiceField(
        label=_("Ответственный"),
        required=False,
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    warranty = forms.ChoiceField(
        label=_("Гарантия"),
        required=False,
        choices=[
            ('', _("Все")),
            ('active', _("Действует")),
            ('expired', _("Истекла")),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        from locations.models import Location
        from hr.models import HumanResource

        super().__init__(*args, **kwargs)

        self.fields['location'].queryset = Location.objects.all().order_by('name')
        self.fields['responsible'].queryset = HumanResource.objects.filter(
            is_active=True
        ).select_related('user').order_by('user__last_name', 'user__first_name')


class WorkstationBulkUpdateForm(forms.Form):
    """Форма массового обновления оборудования"""
    STATUS_CHOICES = [
                         ('', _("Не изменять")),
                     ] + list(WorkstationStatus.choices)

    GLOBAL_STATE_CHOICES = [
                               ('', _("Не изменять")),
                           ] + list(WorkstationGlobalState.choices)

    status = forms.ChoiceField(
        label=_("Статус"),
        required=False,
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    global_state = forms.ChoiceField(
        label=_("Глобальное состояние"),
        required=False,
        choices=GLOBAL_STATE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    location = forms.ModelChoiceField(
        label=_("Локация"),
        required=False,
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    responsible = forms.ModelChoiceField(
        label=_("Ответственный"),
        required=False,
        queryset=None,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        from locations.models import Location
        from hr.models import HumanResource

        super().__init__(*args, **kwargs)

        self.fields['location'].queryset = Location.objects.all().order_by('name')
        self.fields['responsible'].queryset = HumanResource.objects.filter(
            is_active=True
        ).select_related('user').order_by('user__last_name', 'user__first_name')


class WorkstationImportForm(forms.Form):
    """Форма импорта оборудования из CSV"""
    csv_file = forms.FileField(
        label=_("CSV файл"),
        help_text=_("Файл в формате CSV с данными об оборудовании"),
        widget=forms.FileInput(attrs={
            'accept': '.csv',
            'class': 'form-control',
        })
    )

    encoding = forms.ChoiceField(
        label=_("Кодировка файла"),
        choices=[
            ('utf-8', 'UTF-8'),
            ('windows-1251', 'Windows-1251'),
            ('cp866', 'CP866'),
        ],
        initial='utf-8',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    delimiter = forms.ChoiceField(
        label=_("Разделитель"),
        choices=[
            (';', 'Точка с запятой (;)'),
            (',', 'Запятая (,)'),
            ('\t', 'Табуляция'),
        ],
        initial=';',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    update_existing = forms.BooleanField(
        label=_("Обновлять существующие записи"),
        required=False,
        help_text=_("Обновлять записи с совпадающим инвентарным номером"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )