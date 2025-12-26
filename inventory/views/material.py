from django.db.models import Q
from django.views.generic import CreateView, UpdateView
from ..models import Material
from ..forms import MaterialForm
from .base import BaseListView, BaseDetailView, BaseCreateUpdateView, BaseDeleteView


class MaterialListView(BaseListView):
    """Список материалов"""
    model = Material
    template_name = "inventory/material/list.html"
    ordering = ["name"]

    def apply_search(self, qs, search_query):
        return qs.filter(
            Q(name__icontains=search_query) |
            Q(group__icontains=search_query) |
            Q(article__icontains=search_query) |
            Q(part_number__icontains=search_query)
        )


class MaterialDetailView(BaseDetailView):
    """Детальная информация о материале"""
    model = Material
    template_name = "inventory/material/detail.html"


class MaterialCreateView(BaseCreateUpdateView, CreateView):
    """Создание материала"""
    model = Material
    form_class = MaterialForm
    template_name = "inventory/material/form.html"

    def get_action_name(self):
        return "создание материала"

    def get_success_message(self):
        return "Материал успешно создан"

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if hasattr(self, 'request'):
            kwargs['request'] = self.request
        return kwargs


class MaterialUpdateView(BaseCreateUpdateView, UpdateView):
    """Редактирование материала"""
    model = Material
    form_class = MaterialForm
    template_name = "inventory/material/form.html"

    def get_action_name(self):
        return "редактирование материала"

    def get_success_message(self):
        return "Изменения материала сохранены"

    def get_success_url(self):
        return self.object.get_absolute_url()

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if hasattr(self, 'request'):
            kwargs['request'] = self.request
        return kwargs


class MaterialDeleteView(BaseDeleteView):
    """Удаление материала"""
    model = Material

    def get_action_name(self):
        return "удаление материала"