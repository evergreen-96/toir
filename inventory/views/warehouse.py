from django.db import models
from django.db.models import Sum
from django.views.generic import CreateView, UpdateView
from ..models import Warehouse, Material
from ..forms import WarehouseForm
from .base import BaseListView, BaseDetailView, BaseCreateUpdateView, BaseDeleteView


class WarehouseListView(BaseListView):
    """Список складов"""
    model = Warehouse
    template_name = "inventory/warehouse/list.html"
    ordering = ["name"]

    def apply_search(self, qs, search_query):
        return qs.filter(name__icontains=search_query)


class WarehouseDetailView(BaseDetailView):
    """Детальная информация о складе"""
    model = Warehouse
    template_name = "inventory/warehouse/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        warehouse = self.object

        # Получаем все материалы на складе
        materials = Material.objects.filter(warehouse=warehouse)

        # Подсчитываем статистику
        materials_count = materials.count()

        # Подсчитываем суммы
        total_qty_available = materials.aggregate(
            total=Sum('qty_available')
        )['total'] or 0

        total_qty_reserved = materials.aggregate(
            total=Sum('qty_reserved')
        )['total'] or 0

        # Подсчитываем статусы
        active_materials_count = materials.filter(is_active=True).count()

        in_stock_count = materials.filter(
            is_active=True,
            qty_available__gt=0
        ).count()

        low_stock_count = materials.filter(
            is_active=True,
            qty_available__gt=0,
            qty_available__lte=models.F('qty_reserved')
        ).count()

        out_of_stock_count = materials.filter(
            is_active=True,
            qty_available=0
        ).count()

        context.update({
            'materials': materials,
            'materials_count': materials_count,
            'total_qty_available': total_qty_available,
            'total_qty_reserved': total_qty_reserved,
            'total_qty_all': total_qty_available + total_qty_reserved,
            'active_materials_count': active_materials_count,
            'in_stock_count': in_stock_count,
            'low_stock_count': low_stock_count,
            'out_of_stock_count': out_of_stock_count,
        })

        return context


class WarehouseCreateView(BaseCreateUpdateView, CreateView):
    """Создание склада"""
    model = Warehouse
    form_class = WarehouseForm
    template_name = "inventory/warehouse/form.html"

    def get_action_name(self):
        return "создание склада"

    def get_success_message(self):
        return "Склад успешно создан"

    def get_success_url(self):
        return self.object.get_absolute_url()


class WarehouseUpdateView(BaseCreateUpdateView, UpdateView):
    """Редактирование склада"""
    model = Warehouse
    form_class = WarehouseForm
    template_name = "inventory/warehouse/form.html"

    def get_action_name(self):
        return "редактирование склада"

    def get_success_message(self):
        return "Изменения склада сохранены"

    def get_success_url(self):
        return self.object.get_absolute_url()


class WarehouseDeleteView(BaseDeleteView):
    """Удаление склада"""
    model = Warehouse

    def get_action_name(self):
        return "удаление склада"