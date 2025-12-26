from django import forms
from django.utils.translation import gettext_lazy as _
from .models import HumanResource


class HumanResourceForm(forms.ModelForm):
    """Форма для создания/редактирования сотрудника"""

    class Meta:
        model = HumanResource
        fields = ["name", "job_title", "manager", "is_active"]
        widgets = {
            'job_title': forms.TextInput(
                attrs={'class': 'form-control', 'list': 'job-titles-datalist'}
            ),
            'name': forms.TextInput(
                attrs={'class': 'form-control'}
            ),
        }
        help_texts = {
            'manager': _('Выберите руководителя из списка'),
            'job_title': _('Введите должность или выберите из списка'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Оптимизируем queryset для поля manager
        self.fields['manager'].queryset = HumanResource.objects.all().order_by('name')

        if self.instance.pk:
            # Исключаем возможность выбрать самого себя руководителем
            self.fields['manager'].queryset = self.fields['manager'].queryset.exclude(
                pk=self.instance.pk
            )

        # Добавляем CSS классы
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

        # Делаем поле имени обязательным
        self.fields['name'].required = True


class HumanResourceSearchForm(forms.Form):
    """Форма поиска сотрудников"""

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

        self.fields['manager'].queryset = HumanResource.objects.filter(
            is_active=True
        ).order_by('name')


class HumanResourceBulkUpdateForm(forms.Form):
    """Форма массового обновления сотрудников"""

    manager = forms.ModelChoiceField(
        label=_("Руководитель"),
        required=False,
        queryset=None,
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


class HumanResourceImportForm(forms.Form):
    """Форма импорта сотрудников из CSV"""

    csv_file = forms.FileField(
        label=_("CSV файл"),
        help_text=_("Файл в формате CSV с данными о сотрудниках"),
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
        help_text=_("Обновлять записи с совпадающим табельным номером"),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )