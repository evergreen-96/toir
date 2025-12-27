from django.db.models import Sum
from django.views.generic import CreateView, UpdateView
from inventory.forms.warehouse import WarehouseForm, WarehouseFilterForm
from inventory.views.base import BaseListView, BaseDetailView, BaseCreateUpdateView, BaseDeleteView
from inventory.models import Warehouse, Material
import django.db.models as models


class WarehouseListView(BaseListView):
    """Список складов"""
    model = Warehouse
    template_name = "inventory/warehouse/list.html"
    ordering = ["name"]
    filter_form_class = WarehouseFilterForm

    def apply_search(self, qs, search_query):
        return qs.filter(name__icontains=search_query)

    def get_queryset(self):
        qs = super().get_queryset()

        # Применяем фильтры из формы
        if self.filter_form_class:
            form = self.filter_form_class(self.request.GET)
            if form.is_valid():
                location = form.cleaned_data.get('location')
                if location:
                    qs = qs.filter(location=location)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Добавляем статистику по складам
        warehouses = context['object_list']
        for warehouse in warehouses:
            warehouse.materials_summary = warehouse.get_materials_summary()

        return context


class WarehouseDetailView(BaseDetailView):
    """Детальная информация о складе"""
    model = Warehouse
    template_name = "inventory/warehouse/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        warehouse = self.object

        # Получаем материалы на складе
        materials = Material.objects.filter(warehouse=warehouse)

        # Подсчитываем статистику
        summary = materials.aggregate(
            total_available=Sum('qty_available'),
            total_reserved=Sum('qty_reserved'),
        )

        # Подсчитываем статусы
        stock_status_counts = {
            'in_stock': materials.filter(is_active=True, qty_available__gt=0).exclude(
                qty_available__lte=models.F('qty_reserved')
            ).count(),
            'low_stock': materials.filter(
                is_active=True,
                qty_available__gt=0,
                qty_available__lte=models.F('min_stock_level')
            ).count(),
            'reserved': materials.filter(
                is_active=True,
                qty_available__gt=0,
                qty_available__lte=models.F('qty_reserved')
            ).count(),
            'out_of_stock': materials.filter(
                is_active=True,
                qty_available=0
            ).count(),
            'inactive': materials.filter(is_active=False).count(),
        }

        context.update({
            'materials': materials,
            'materials_count': materials.count(),
            'total_qty_available': summary['total_available'] or 0,
            'total_qty_reserved': summary['total_reserved'] or 0,
            'total_qty_all': (summary['total_available'] or 0) + (summary['total_reserved'] or 0),
            'stock_status_counts': stock_status_counts,
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