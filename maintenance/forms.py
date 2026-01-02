from django import forms
from django.forms import inlineformset_factory

from assets.models import Workstation
from hr.models import HumanResource
from inventory.forms import MaterialSelectWithImage
from maintenance.models import IntervalUnit, WorkCategory, Priority
from .models import WorkOrder, WorkOrderMaterial, PlannedOrder


# ============================================================================
# КЛАСС ДЛЯ МНОГОФАЙЛОВОЙ ЗАГРУЗКИ
# ============================================================================

class MultiFileInput(forms.ClearableFileInput):
    """
    Виджет для загрузки нескольких файлов одновременно.
    Расширяет стандартный ClearableFileInput.
    """
    allow_multiple_selected = True
    template_name = "django/forms/widgets/clearable_file_input.html"

    def __init__(self, attrs=None):
        default_attrs = {
            "multiple": "multiple",
            "class": "form-control"
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class MultiFileField(forms.FileField):
    """
    Поле формы для загрузки нескольких файлов.
    Возвращает список файлов вместо одного файла.
    """
    widget = MultiFileInput

    def clean(self, data, initial=None):
        """
        Очистка и валидация загруженных файлов.

        Args:
            data: Загруженные файлы (может быть списком или одиночным файлом)
            initial: Начальное значение поля

        Returns:
            list: Список валидированных файлов
        """
        if data is None:
            return []

        # Преобразуем одиночный файл в список для единообразной обработки
        if not isinstance(data, (list, tuple)):
            data = [data]

        cleaned_files = []
        for file_data in data:
            try:
                cleaned_file = super().clean(file_data, initial)
                if cleaned_file:  # Добавляем только если файл валиден
                    cleaned_files.append(cleaned_file)
            except forms.ValidationError:
                # Пропускаем невалидные файлы, продолжаем обработку остальных
                continue

        return cleaned_files


# ============================================================================
# ФОРМА РАБОЧЕЙ ЗАДАЧИ
# ============================================================================

class WorkOrderForm(forms.ModelForm):
    """
    Форма для создания и редактирования рабочих задач.
    """

    files = MultiFileField(
        label="Файлы",
        required=False,
        help_text="Вы можете загрузить несколько файлов одновременно"
    )

    class Meta:
        model = WorkOrder
        fields = [
            "name",
            "priority",
            "category",
            "responsible",
            "location",
            "workstation",
            "date_start",
            "date_finish",
            "labor_plan_hours",
            "labor_fact_hours",
            "description",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Введите название задачи"
            }),
            "priority": forms.Select(attrs={
                "class": "form-select"
            }),
            "category": forms.Select(attrs={
                "class": "form-select"
            }),
            "responsible": forms.Select(attrs={
                "class": "form-select"
            }),
            "location": forms.Select(attrs={
                "class": "form-select",
                "data-action": "change->workorder#onLocationChange"
            }),
            "workstation": forms.Select(attrs={
                "class": "form-select"
            }),
            "date_start": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "date_finish": forms.DateInput(attrs={
                "type": "date",
                "class": "form-control"
            }),
            "labor_plan_hours": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.5",
                "min": "0"
            }),
            "labor_fact_hours": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.5",
                "min": "0"
            }),
            "description": forms.Textarea(attrs={
                "rows": 4,
                "class": "form-control",
                "placeholder": "Подробное описание работ..."
            }),
        }
        labels = {
            "name": "Название задачи",
            "priority": "Приоритет",
            "category": "Категория работ",
            "responsible": "Ответственный",
            "location": "Локация",
            "workstation": "Оборудование",
            "date_start": "Дата начала",
            "date_finish": "Дата окончания",
            "labor_plan_hours": "Трудоёмкость (план), ч",
            "labor_fact_hours": "Трудоёмкость (факт), ч",
            "description": "Описание",
        }
        help_texts = {
            "date_start": "Планируемая дата начала работ",
            "date_finish": "Планируемая дата окончания работ",
            "labor_plan_hours": "Плановые трудозатраты в часах",
            "labor_fact_hours": "Фактические трудозатраты в часах",
        }

    def __init__(self, *args, **kwargs):
        """
        Инициализация формы с динамическим queryset для оборудования.
        """
        super().__init__(*args, **kwargs)

        # Начальное значение - пустой queryset для оборудования
        self.fields["workstation"].queryset = Workstation.objects.none()

        # Динамическая загрузка оборудования при отправке формы
        if "location" in self.data:
            self._load_workstations_from_data()

        # Загрузка оборудования при редактировании существующей задачи
        elif self.instance.pk and self.instance.location:
            self._load_workstations_from_instance()

    def _load_workstations_from_data(self):
        """
        Загружает оборудование на основе данных формы.
        """
        try:
            location_id = int(self.data.get("location"))
            if location_id:
                self.fields["workstation"].queryset = (
                    Workstation.objects
                    .filter(location_id=location_id)
                    .order_by("name")
                )
        except (TypeError, ValueError, AttributeError):
            # Если location_id не валиден, оставляем пустой queryset
            pass

    def _load_workstations_from_instance(self):
        """
        Загружает оборудование на основе существующего экземпляра.
        """
        self.fields["workstation"].queryset = (
            Workstation.objects
            .filter(location=self.instance.location)
            .order_by("name")
        )

    def clean(self):
        """
        Дополнительная валидация формы.
        """
        cleaned_data = super().clean()

        # Проверка дат
        date_start = cleaned_data.get("date_start")
        date_finish = cleaned_data.get("date_finish")

        if date_start and date_finish and date_start > date_finish:
            self.add_error(
                "date_finish",
                "Дата окончания не может быть раньше даты начала"
            )

        # Проверка трудозатрат
        labor_plan = cleaned_data.get("labor_plan_hours")
        labor_fact = cleaned_data.get("labor_fact_hours")

        if labor_plan is not None and labor_plan < 0:
            self.add_error(
                "labor_plan_hours",
                "Трудоёмкость не может быть отрицательной"
            )

        if labor_fact is not None and labor_fact < 0:
            self.add_error(
                "labor_fact_hours",
                "Фактические трудозатраты не могут быть отрицательными"
            )

        return cleaned_data


# ============================================================================
# ФОРМА МАТЕРИАЛА ЗАДАЧИ
# ============================================================================

class WorkOrderMaterialForm(forms.ModelForm):
    """
    Форма для материалов рабочей задачи.
    """

    class Meta:
        model = WorkOrderMaterial
        fields = ["material", "qty_planned", "qty_used"]
        widgets = {
            "material": MaterialSelectWithImage(
                attrs={
                    "class": "form-select js-select2-material",
                    "data-ajax--url": "/api/materials/search/",
                    "data-placeholder": "Выберите материал...",
                    "data-minimum-input-length": 2,
                    "data-allow-clear": "true"
                }
            ),
            "qty_planned": forms.NumberInput(attrs={
                "class": "form-control qty-planned",
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00"
            }),
            "qty_used": forms.NumberInput(attrs={
                "class": "form-control qty-used",
                "step": "0.01",
                "min": "0",
                "placeholder": "0.00"
            }),
        }
        labels = {
            "material": "Материал",
            "qty_planned": "Запланировано",
            "qty_used": "Использовано",
        }
        help_texts = {
            "qty_planned": "Плановое количество материала",
            "qty_used": "Фактически использованное количество",
        }

    def __init__(self, *args, **kwargs):
        """
        Инициализация формы материалов.
        """
        super().__init__(*args, **kwargs)

        # Устанавливаем пустой label для пустого выбора в Select2
        self.fields["material"].empty_label = None

    def clean(self):
        """
        Валидация формы материалов.

        Returns:
            dict: Очищенные данные формы
        """
        cleaned_data = super().clean()

        # Если строка помечена на удаление - пропускаем валидацию
        if cleaned_data.get("DELETE", False):
            return cleaned_data

        # Валидация количеств
        qty_planned = cleaned_data.get("qty_planned")
        qty_used = cleaned_data.get("qty_used")

        if qty_planned is not None and qty_planned < 0:
            self.add_error(
                "qty_planned",
                "Количество не может быть отрицательным"
            )

        if qty_used is not None and qty_used < 0:
            self.add_error(
                "qty_used",
                "Использованное количество не может быть отрицательным"
            )

        # Проверка наличия материала
        material = cleaned_data.get("material")
        if material and not material.is_active:
            self.add_error(
                "material",
                "Выбранный материал неактивен"
            )

        return cleaned_data

    def clean_qty_planned(self):
        """
        Валидация поля запланированного количества.
        """
        qty_planned = self.cleaned_data.get("qty_planned")

        if qty_planned is not None:
            # Округление до 2 знаков после запятой
            qty_planned = round(qty_planned, 2)

            # Проверка максимального значения
            if qty_planned > 999999.99:
                raise forms.ValidationError(
                    "Запланированное количество слишком большое"
                )

        return qty_planned

    def clean_qty_used(self):
        """
        Валидация поля использованного количества.
        """
        qty_used = self.cleaned_data.get("qty_used")

        if qty_used is not None:
            # Округление до 2 знаков после запятой
            qty_used = round(qty_used, 2)

            # Проверка максимального значения
            if qty_used > 999999.99:
                raise forms.ValidationError(
                    "Использованное количество слишком большое"
                )

        return qty_used


# ============================================================================
# ФОРМА ПЛАНОВОЙ РАБОТЫ
# ============================================================================

class PlannedOrderForm(forms.ModelForm):
    """
    Форма для создания и редактирования плановых работ.
    """

    # Поле выбора частоты (не из модели)
    frequency_choice = forms.ChoiceField(
        label="Периодичность работ",
        choices=[
            ("daily", "Ежедневно"),
            ("weekly", "Еженедельно"),
            ("monthly", "Ежемесячно"),
            ("custom", "По заданному интервалу"),
        ],
        widget=forms.RadioSelect(attrs={
            "class": "form-check-input frequency-choice",
        }),
        required=True,
        initial="weekly"
    )
    # Переопределяем поля интервала для скрытого хранения
    interval_value = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.HiddenInput(attrs={
            "class": "interval-value-field"
        }),
        initial=1
    )

    interval_unit = forms.ChoiceField(
        required=False,
        choices=IntervalUnit.choices,
        widget=forms.HiddenInput(attrs={
            "class": "interval-unit-field"
        }),
        initial=IntervalUnit.WEEK
    )

    # Справочник дней недели
    WEEKDAYS = [
        (0, "Понедельник"),
        (1, "Вторник"),
        (2, "Среда"),
        (3, "Четверг"),
        (4, "Пятница"),
        (5, "Суббота"),
        (6, "Воскресенье"),
    ]

    # Поля для специфических режимов
    first_run_date = forms.DateField(
        label="Дата первого обслуживания",
        required=False,
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control first-run-date",
        }),
        help_text="Дата первого запуска ежедневного обслуживания"
    )

    weekday = forms.ChoiceField(
        label="День недели",
        choices=WEEKDAYS,
        required=False,
        widget=forms.Select(attrs={
            "class": "form-select weekday-select",
        }),
        help_text="День недели для еженедельного обслуживания"
    )

    day_of_month = forms.IntegerField(
        label="Число месяца",
        required=False,
        min_value=1,
        max_value=31,
        widget=forms.NumberInput(attrs={
            "class": "form-control day-of-month",
            "min": "1",
            "max": "31"
        }),
        help_text="Число месяца для ежемесячного обслуживания (1-31)"
    )

    class Meta:
        model = PlannedOrder
        fields = [
            "frequency_choice",
            "name",
            "description",
            "workstation",
            "location",
            "responsible_default",
            "category",
            "priority",
            "labor_plan_hours",
            "interval_value",
            "interval_unit",
            "first_run_date",
            "weekday",
            "day_of_month",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Введите название плана"
            }),
            "description": forms.Textarea(attrs={
                "rows": 3,
                "class": "form-control",
                "placeholder": "Описание плановых работ..."
            }),
            "workstation": forms.Select(attrs={
                "class": "form-select js-tom-select-workstation",
                "data-placeholder": "Выберите оборудование..."
            }),
            "location": forms.Select(attrs={
                "class": "form-select js-tom-select-location",
                "data-placeholder": "Выберите локацию..."
            }),
            "responsible_default": forms.Select(attrs={
                "class": "form-select js-tom-select-responsible",
                "data-placeholder": "Выберите ответственного..."
            }),
            "category": forms.Select(attrs={
                "class": "form-select"
            }),
            "priority": forms.Select(attrs={
                "class": "form-select"
            }),
            "labor_plan_hours": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.5",
                "min": "0",
                "placeholder": "0.0"
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input"
            }),
        }
        labels = {
            "name": "Название плана",
            "description": "Описание",
            "workstation": "Оборудование",
            "location": "Локация",
            "responsible_default": "Ответственный по умолчанию",
            "category": "Категория работ",
            "priority": "Приоритет",
            "labor_plan_hours": "Трудоёмкость (план), ч",
            "is_active": "Активно",
        }
        help_texts = {
            "responsible_default": "Ответственный за выполнение плановых работ",
            "labor_plan_hours": "Плановые трудозатраты на одно выполнение",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # ---------- responsible ----------
        self.fields["responsible_default"].required = True
        self.fields["responsible_default"].queryset = (
            HumanResource.objects
            .filter(is_active=True)
            .order_by("name")
        )

        # ---------- category ----------
        self.fields["category"].choices = [
            (v, l)
            for v, l in self.fields["category"].choices
            if v != WorkCategory.EMERGENCY
        ]

        # ---------- workstation queryset (КРИТИЧНО) ----------
        self.fields["workstation"].queryset = Workstation.objects.none()

        # POST → по выбранной локации
        if "location" in self.data:
            try:
                location_id = int(self.data.get("location"))
                self.fields["workstation"].queryset = (
                    Workstation.objects
                    .filter(location_id=location_id)
                    .order_by("name")
                )
            except (TypeError, ValueError):
                pass

        # EDIT → из instance
        elif self.instance.pk and self.instance.location:
            self.fields["workstation"].queryset = (
                Workstation.objects
                .filter(location=self.instance.location)
                .order_by("name")
            )

        # ---------- frequency_choice ----------
        if self.instance.pk:
            self._set_frequency_choice_from_instance()

    def _set_frequency_choice_from_instance(self):
        """
        Восстанавливает frequency_choice при редактировании
        на основе interval_unit / weekday / day_of_month
        """
        if not self.instance.pk:
            return

        # CUSTOM — если интервал > 1
        if self.instance.interval_value and self.instance.interval_value > 1:
            self.initial["frequency_choice"] = "custom"
            return

        unit = self.instance.interval_unit

        if unit == IntervalUnit.DAY:
            self.initial["frequency_choice"] = "daily"
        elif unit == IntervalUnit.WEEK:
            self.initial["frequency_choice"] = "weekly"
        elif unit == IntervalUnit.MONTH:
            self.initial["frequency_choice"] = "monthly"
# ============================================================================
# FORMSET ДЛЯ МАТЕРИАЛОВ
# ============================================================================

WorkOrderMaterialFormSet = inlineformset_factory(
    WorkOrder,
    WorkOrderMaterial,
    form=WorkOrderMaterialForm,
    extra=0,  # Одна пустая строка по умолчанию
    can_delete=True,
    min_num=0,
    validate_min=False,
    can_order=False,
    fields=["material", "qty_planned", "qty_used"],
    widgets={
        "material": MaterialSelectWithImage(
            attrs={
                "class": "form-select js-select2-material",
                "data-ajax--url": "/api/materials/search/",
                "data-placeholder": "Выберите материал...",
                "data-minimum-input-length": 2,
                "data-allow-clear": "true"
            }
        ),
    },
)