from django.db.models import Sum, F, Q
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

        # Подсчитываем статусы - ИСПРАВЛЕННАЯ ЛОГИКА
        # Получаем только активные материалы для статусов
        active_materials = materials.filter(is_active=True)

        # stock_status_counts = {
        #     # "В наличии" - есть в наличии, больше чем минимальный запас и больше чем резерв
        #     # Объединяем все условия для in_stock
        #     'in_stock': active_materials.filter(
        #         Q(qty_available__gt=0) &
        #         Q(qty_available__gt=F('min_stock_level')) &
        #         Q(qty_available__gt=F('qty_reserved'))
        #     ).count(),
        #
        #     # "Низкий запас" - есть в наличии, но меньше или равно минимальному запасу
        #     # И не все зарезервировано (это отдельная категория)
        #     'low_stock': active_materials.filter(
        #         Q(qty_available__gt=0) &
        #         Q(qty_available__lte=F('min_stock_level')) &
        #         Q(qty_available__gt=F('qty_reserved'))  # Не зарезервировано полностью
        #     ).count(),
        #
        #     # "В резерве" - все доступное количество зарезервировано
        #     'reserved': active_materials.filter(
        #         Q(qty_available__gt=0) &
        #         Q(qty_available__lte=F('qty_reserved'))
        #     ).count(),
        #
        #     # "Отсутствует" - нет доступного количества
        #     'out_of_stock': active_materials.filter(qty_available=0).count(),
        #
        #     # "Неактивен"
        #     'inactive': materials.filter(is_active=False).count(),
        # }

        context.update({
            'materials': materials,
            'materials_count': materials.count(),
            'total_qty_available': summary['total_available'] or 0,
            'total_qty_reserved': summary['total_reserved'] or 0,
            'total_qty_all': (summary['total_available'] or 0) + (summary['total_reserved'] or 0),
            # 'stock_status_counts': stock_status_counts,
            # # Для совместимости с вашим шаблоном добавляем отдельные переменные
            # 'active_materials_count': active_materials.count(),
            # 'in_stock_count': stock_status_counts['in_stock'],
            # 'low_stock_count': stock_status_counts['low_stock'],
            # 'out_of_stock_count': stock_status_counts['out_of_stock'],
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