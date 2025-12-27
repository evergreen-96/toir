from django.db.models import Q, Sum
from django.views.generic import CreateView, UpdateView
from inventory.forms.material import MaterialForm, MaterialFilterForm
from inventory.views.base import BaseListView, BaseDetailView, BaseCreateUpdateView, BaseDeleteView
from inventory.models import Material, Warehouse
import django.db.models as models


class MaterialListView(BaseListView):
    """Список материалов"""
    model = Material
    template_name = "inventory/material/list.html"
    ordering = ["name"]
    filter_form_class = MaterialFilterForm

    def apply_search(self, qs, search_query):
        return qs.filter(
            Q(name__icontains=search_query) |
            Q(group__icontains=search_query) |
            Q(article__icontains=search_query) |
            Q(part_number__icontains=search_query) |
            Q(vendor__icontains=search_query)
        )

    def get_queryset(self):
        qs = super().get_queryset()

        # Применяем фильтры из формы
        if self.filter_form_class:
            form = self.filter_form_class(self.request.GET)
            if form.is_valid():
                warehouse = form.cleaned_data.get('warehouse')
                is_active = form.cleaned_data.get('is_active')
                stock_status = form.cleaned_data.get('stock_status')
                group = form.cleaned_data.get('group')

                if warehouse:
                    qs = qs.filter(warehouse=warehouse)

                if is_active:
                    qs = qs.filter(is_active=(is_active == '1'))

                if group:
                    qs = qs.filter(group__icontains=group)

                if stock_status:
                    if stock_status == 'in_stock':
                        qs = qs.filter(is_active=True, qty_available__gt=0).exclude(
                            qty_available__lte=models.F('qty_reserved')
                        )
                    elif stock_status == 'low_stock':
                        qs = qs.filter(
                            is_active=True,
                            qty_available__gt=0,
                            qty_available__lte=models.F('min_stock_level')
                        )
                    elif stock_status == 'out_of_stock':
                        qs = qs.filter(is_active=True, qty_available=0)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Добавляем статистику по материалам
        materials = context['object_list']
        summary = materials.aggregate(
            total_available=Sum('qty_available'),
            total_reserved=Sum('qty_reserved'),
        )

        context.update({
            'total_qty_available': summary['total_available'] or 0,
            'total_qty_reserved': summary['total_reserved'] or 0,
            'total_qty_all': (summary['total_available'] or 0) + (summary['total_reserved'] or 0),
            'materials_count': materials.count(),
        })

        return context


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

        # Если есть параметр warehouse в GET, устанавливаем его по умолчанию
        warehouse_id = self.request.GET.get('warehouse')
        if warehouse_id and not self.object:
            try:
                warehouse = Warehouse.objects.get(pk=warehouse_id)
                kwargs['initial'] = {'warehouse': warehouse}
            except Warehouse.DoesNotExist:
                pass

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