"""
hr/forms.py

Рефакторинг с использованием базовых классов из core.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from core.forms import BaseModelForm, BaseFilterForm
from .models import HumanResource


class HumanResourceForm(BaseModelForm):
    """
    Форма для создания/редактирования сотрудника.
    
    Наследует от BaseModelForm:
    - Автоматическая Bootstrap стилизация
    - Доступ к request
    - Методы валидации
    """

    class Meta:
        model = HumanResource
        fields = ["name", "job_title", "manager", "is_active"]
        widgets = {
            'manager': forms.Select(attrs={
                'class': 'form-select js-tom-select-manager',
                'data-placeholder': _('Выберите руководителя...')
            }),
        }
        help_texts = {
            'manager': _('Выберите руководителя из списка'),
            'job_title': _('Введите должность или выберите из списка'),
        }

    # Не стилизовать автоматически (стили заданы явно)
    exclude_fields = ['manager', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Queryset для руководителей
        self.fields['manager'].queryset = HumanResource.objects.filter(
            is_active=True
        ).order_by('name')

        # Исключаем себя из списка руководителей при редактировании
        if self.instance.pk:
            self.fields['manager'].queryset = self.fields['manager'].queryset.exclude(
                pk=self.instance.pk
            )

        # Должность — текстовое поле с TomSelect
        self.fields['job_title'] = forms.CharField(
            label=_("Должность"),
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-control js-tom-select-job',
                'data-placeholder': _('Выберите или введите должность...'),
            })
        )

        # Имя обязательное
        self.fields['name'].required = True
        self.fields['name'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Введите ФИО'),
            'autofocus': True,
        })

        # Чекбокс активности
        self.fields['is_active'].widget.attrs.update({
            'class': 'form-check-input',
        })

    def clean_name(self):
        """Валидация имени."""
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise forms.ValidationError(_("ФИО должно содержать минимум 2 символа"))
        return name

    def clean_manager(self):
        """Проверка на циклическую иерархию."""
        manager = self.cleaned_data.get('manager')

        if manager and self.instance.pk:
            # Проверяем, что не назначаем себя руководителем
            if manager.pk == self.instance.pk:
                raise forms.ValidationError(_("Сотрудник не может быть руководителем самого себя"))

            # Проверяем циклическую зависимость
            current = manager
            visited = {self.instance.pk}
            while current:
                if current.pk in visited:
                    raise forms.ValidationError(_("Обнаружена циклическая иерархия"))
                visited.add(current.pk)
                current = current.manager

        return manager


class HumanResourceSearchForm(BaseFilterForm):
    """
    Форма поиска/фильтрации сотрудников.
    Все поля автоматически необязательные (BaseFilterForm).
    """

    q = forms.CharField(
        label=_("Поиск"),
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': _("ФИО, должность..."),
            'class': 'form-control',
        })
    )

    manager = forms.ModelChoiceField(
        label=_("Руководитель"),
        required=False,
        queryset=None,
        empty_label=_("Все руководители"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    job_title = forms.ChoiceField(
        label=_("Должность"),
        required=False,
        choices=[('', _("Все должности"))],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    only_managers = forms.BooleanField(
        label=_("Только руководители"),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    is_active = forms.ChoiceField(
        label=_("Статус"),
        required=False,
        choices=[
            ('', _("Все")),
            ('true', _("Активен")),
            ('false', _("Неактивен")),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Динамические choices для должностей
        job_titles = HumanResource.objects.exclude(
            job_title=""
        ).values_list('job_title', flat=True).distinct()

        self.fields['job_title'].choices = [
            ('', _("Все должности"))
        ] + [(title, title) for title in job_titles]

        # Queryset для руководителей
        self.fields['manager'].queryset = HumanResource.objects.filter(
            is_active=True
        ).order_by('name')


class HumanResourceBulkUpdateForm(BaseFilterForm):
    """Форма массового обновления сотрудников."""

    manager = forms.ModelChoiceField(
        label=_("Руководитель"),
        required=False,
        queryset=None,
        empty_label=_("Не изменять"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    is_active = forms.ChoiceField(
        label=_("Активность"),
        required=False,
        choices=[
            ('', _("Не изменять")),
            ('active', _("Активен")),
            ('inactive', _("Неактивен")),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['manager'].queryset = HumanResource.objects.filter(
            is_active=True
        ).order_by('name')


class HumanResourceImportForm(BaseFilterForm):
    """Форма импорта сотрудников из CSV."""

    csv_file = forms.FileField(
        label=_("CSV файл"),
        help_text=_("Файл в формате CSV с данными о сотрудниках"),
        widget=forms.FileInput(attrs={
            'accept': '.csv',
            'class': 'form-control',
        })
    )

    encoding = forms.ChoiceField(
        label=_("Кодировка"),
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
        label=_("Обновлять существующие"),
        required=False,
        help_text=_("Обновлять записи с совпадающим именем"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # csv_file обязательное
        self.fields['csv_file'].required = True
