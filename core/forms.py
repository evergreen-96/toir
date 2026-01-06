"""
core/forms.py

Базовые классы для форм с автоматической Bootstrap-стилизацией.
Устраняет дублирование кода стилизации виджетов во всех приложениях.
"""

from django import forms


class BootstrapFormMixin:
    """
    Миксин для автоматической стилизации форм под Bootstrap 5.
    
    Автоматически добавляет CSS-классы:
    - form-control для текстовых полей
    - form-select для select
    - form-check-input для checkbox/radio
    - form-control для textarea
    
    Использование:
        class MyForm(BootstrapFormMixin, forms.ModelForm):
            class Meta:
                model = MyModel
                fields = '__all__'
    """
    
    # Классы для разных типов виджетов
    widget_css_classes = {
        'text': 'form-control',
        'textarea': 'form-control',
        'select': 'form-select',
        'selectmultiple': 'form-select',
        'checkbox': 'form-check-input',
        'radio': 'form-check-input',
        'file': 'form-control',
        'date': 'form-control',
        'datetime': 'form-control',
        'time': 'form-control',
        'number': 'form-control',
        'email': 'form-control',
        'url': 'form-control',
        'password': 'form-control',
        'hidden': '',
    }
    
    # Поля, которые не нужно стилизовать
    exclude_fields = []
    
    # Дополнительные атрибуты для конкретных полей
    field_attrs = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_bootstrap_styles()
    
    def _apply_bootstrap_styles(self):
        """Применяет Bootstrap классы ко всем полям."""
        for field_name, field in self.fields.items():
            if field_name in self.exclude_fields:
                continue
            
            widget = field.widget
            widget_type = self._get_widget_type(widget)
            css_class = self.widget_css_classes.get(widget_type, 'form-control')
            
            if css_class:
                existing_class = widget.attrs.get('class', '')
                if css_class not in existing_class:
                    widget.attrs['class'] = f"{existing_class} {css_class}".strip()
            
            # Добавляем placeholder из label если не задан
            if widget_type in ('text', 'textarea', 'email', 'url', 'number', 'password'):
                if 'placeholder' not in widget.attrs:
                    widget.attrs['placeholder'] = field.label or field_name.replace('_', ' ').title()
            
            # Применяем дополнительные атрибуты
            if field_name in self.field_attrs:
                widget.attrs.update(self.field_attrs[field_name])
    
    def _get_widget_type(self, widget):
        """Определяет тип виджета."""
        widget_class = widget.__class__.__name__.lower()
        
        mapping = {
            'textinput': 'text',
            'textarea': 'textarea',
            'select': 'select',
            'selectmultiple': 'selectmultiple',
            'checkboxinput': 'checkbox',
            'radioinput': 'radio',
            'radioselect': 'radio',
            'checkboxselectmultiple': 'checkbox',
            'fileinput': 'file',
            'clearablefileinput': 'file',
            'dateinput': 'date',
            'datetimeinput': 'datetime',
            'timeinput': 'time',
            'numberinput': 'number',
            'emailinput': 'email',
            'urlinput': 'url',
            'passwordinput': 'password',
            'hiddeninput': 'hidden',
        }
        
        return mapping.get(widget_class, 'text')


class TomSelectMixin:
    """
    Миксин для полей с TomSelect (замена Select2).
    
    Использование:
        class MyForm(TomSelectMixin, BootstrapFormMixin, forms.ModelForm):
            tom_select_fields = ['location', 'responsible']
            tom_select_config = {
                'location': {'placeholder': 'Выберите локацию...'},
            }
    """
    
    tom_select_fields = []
    tom_select_config = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_tom_select()
    
    def _apply_tom_select(self):
        """Применяет настройки TomSelect к указанным полям."""
        for field_name in self.tom_select_fields:
            if field_name not in self.fields:
                continue
            
            field = self.fields[field_name]
            widget = field.widget
            
            # Добавляем CSS класс для JS-инициализации
            existing_class = widget.attrs.get('class', '')
            widget.attrs['class'] = f"{existing_class} js-tom-select".strip()
            
            # Применяем конфигурацию
            config = self.tom_select_config.get(field_name, {})
            
            if 'placeholder' in config:
                widget.attrs['data-placeholder'] = config['placeholder']
            
            if config.get('allow_create'):
                widget.attrs['data-create'] = 'true'
            
            if config.get('ajax_url'):
                widget.attrs['data-ajax-url'] = config['ajax_url']


class FormValidationMixin:
    """
    Миксин с общими методами валидации.
    """
    
    def clean_positive_number(self, field_name, allow_zero=True):
        """Проверяет, что число положительное."""
        value = self.cleaned_data.get(field_name)
        if value is not None:
            if allow_zero and value < 0:
                raise forms.ValidationError(f"{field_name} не может быть отрицательным")
            if not allow_zero and value <= 0:
                raise forms.ValidationError(f"{field_name} должен быть больше нуля")
        return value
    
    def clean_date_range(self, start_field, end_field):
        """Проверяет, что дата начала не позже даты окончания."""
        start = self.cleaned_data.get(start_field)
        end = self.cleaned_data.get(end_field)
        
        if start and end and start > end:
            raise forms.ValidationError({
                end_field: f"Дата окончания не может быть раньше даты начала"
            })
        
        return start, end


class RequestFormMixin:
    """
    Миксин для форм, которым нужен доступ к request.
    
    Использование:
        # В view:
        form = MyForm(request=request)
        
        # В форме:
        class MyForm(RequestFormMixin, forms.ModelForm):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                if self.request:
                    # Используем self.request
                    pass
    """
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)


# =============================================================================
# ГОТОВЫЕ БАЗОВЫЕ КЛАССЫ
# =============================================================================

class BaseModelForm(BootstrapFormMixin, FormValidationMixin, RequestFormMixin, forms.ModelForm):
    """
    Базовый класс для ModelForm с полной функциональностью:
    - Bootstrap стилизация
    - Методы валидации
    - Доступ к request
    
    Использование:
        class MyForm(BaseModelForm):
            class Meta:
                model = MyModel
                fields = '__all__'
    """
    pass


class BaseForm(BootstrapFormMixin, FormValidationMixin, RequestFormMixin, forms.Form):
    """
    Базовый класс для обычных форм.
    """
    pass


class BaseFilterForm(BootstrapFormMixin, forms.Form):
    """
    Базовый класс для форм фильтрации.
    Все поля необязательные по умолчанию.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Делаем все поля необязательными
        for field in self.fields.values():
            field.required = False


# =============================================================================
# ВИДЖЕТЫ
# =============================================================================

class DatePickerWidget(forms.DateInput):
    """Виджет выбора даты с datepicker."""
    
    input_type = 'date'
    
    def __init__(self, attrs=None):
        default_attrs = {'class': 'form-control'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs, format='%Y-%m-%d')


class DateTimePickerWidget(forms.DateTimeInput):
    """Виджет выбора даты и времени."""
    
    input_type = 'datetime-local'
    
    def __init__(self, attrs=None):
        default_attrs = {'class': 'form-control'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs, format='%Y-%m-%dT%H:%M')


class TimePickerWidget(forms.TimeInput):
    """Виджет выбора времени."""
    
    input_type = 'time'
    
    def __init__(self, attrs=None):
        default_attrs = {'class': 'form-control'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs, format='%H:%M')


class MultiFileInput(forms.ClearableFileInput):
    """Виджет для загрузки нескольких файлов."""
    
    allow_multiple_selected = True
    
    def __init__(self, attrs=None):
        default_attrs = {'class': 'form-control', 'multiple': 'multiple'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class MultiFileField(forms.FileField):
    """Поле для загрузки нескольких файлов."""
    
    widget = MultiFileInput
    
    def clean(self, data, initial=None):
        """Очищает и валидирует загруженные файлы."""
        if data is None:
            return []
        
        if not isinstance(data, (list, tuple)):
            data = [data]
        
        cleaned_files = []
        for file_data in data:
            try:
                cleaned_file = super().clean(file_data, initial)
                if cleaned_file:
                    cleaned_files.append(cleaned_file)
            except forms.ValidationError:
                continue
        
        return cleaned_files
