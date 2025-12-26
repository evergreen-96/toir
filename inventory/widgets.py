# inventory/widgets.py
from django import forms


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


class Select2Widget(forms.Select):
    """Базовый виджет Select2"""

    def __init__(self, attrs=None, choices=(), **kwargs):
        default_attrs = {
            'class': 'form-select js-select2',
            'data-placeholder': 'Выберите...',
            'data-allow-clear': 'true',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs, choices, **kwargs)


class ImagePreviewWidget(forms.ClearableFileInput):
    """Виджет для загрузки изображений с превью"""

    template_name = 'inventory/widgets/image_preview.html'

    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'form-control image-preview-input',
            'accept': 'image/*',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)