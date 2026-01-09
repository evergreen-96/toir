"""
Inventory Views - Склады и Материалы
====================================
Единый модуль представлений для управления складами и номенклатурой.
"""

from django.db.models import Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET

from core.audit import build_change_reason
from core.views import BaseListView, BaseDetailView, BaseDeleteView
from .models import Warehouse, Material
from .forms import WarehouseForm, MaterialForm


# =============================================================================
# WAREHOUSE - VIEWS
# =============================================================================

class WarehouseListView(BaseListView):
    """Список складов."""
    
    model = Warehouse
    template_name = "inventory/warehouse/list.html"
    context_object_name = "warehouses"
    ordering = ["name"]
    paginate_by = 20
    
    search_fields = ["name", "location__name", "responsible__name"]
    
    def get_queryset(self):
        qs = super().get_queryset().select_related("location", "responsible")
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Статистика по складам
        for warehouse in context.get("warehouses", []):
            warehouse.summary = warehouse.get_materials_summary()
        
        return context


class WarehouseDetailView(BaseDetailView):
    """Детальная страница склада."""
    
    model = Warehouse
    template_name = "inventory/warehouse/detail.html"
    context_object_name = "warehouse"
    
    select_related = ["location", "responsible"]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        warehouse = self.object
        
        # Материалы на складе
        materials = Material.objects.filter(warehouse=warehouse).order_by("name")
        
        # Статистика
        summary = materials.aggregate(
            total_available=Sum("qty_available"),
            total_reserved=Sum("qty_reserved"),
        )
        
        context.update({
            "materials": materials[:50],
            "materials_count": materials.count(),
            "total_available": summary["total_available"] or 0,
            "total_reserved": summary["total_reserved"] or 0,
        })
        
        return context


def warehouse_create(request):
    """Создание склада."""
    if request.method == "POST":
        form = WarehouseForm(request.POST)
        
        if form.is_valid():
            warehouse = form.save(commit=False)
            warehouse._history_user = request.user
            warehouse._change_reason = build_change_reason("создание склада")
            warehouse.save()
            
            messages.success(request, "Склад создан.")
            return redirect("inventory:warehouse_detail", pk=warehouse.pk)
    else:
        form = WarehouseForm()
    
    return render(request, "inventory/warehouse/form.html", {
        "form": form,
        "create": True,
    })


def warehouse_update(request, pk):
    """Редактирование склада."""
    warehouse = get_object_or_404(Warehouse, pk=pk)
    
    if request.method == "POST":
        form = WarehouseForm(request.POST, instance=warehouse)
        
        if form.is_valid():
            warehouse = form.save(commit=False)
            warehouse._history_user = request.user
            warehouse._change_reason = build_change_reason("редактирование склада")
            warehouse.save()
            
            messages.success(request, "Изменения сохранены.")
            return redirect("inventory:warehouse_detail", pk=warehouse.pk)
    else:
        form = WarehouseForm(instance=warehouse)
    
    return render(request, "inventory/warehouse/form.html", {
        "form": form,
        "create": False,
        "object": warehouse,
    })


class WarehouseDeleteView(BaseDeleteView):
    """Удаление склада."""
    
    model = Warehouse
    success_url = reverse_lazy("inventory:warehouse_list")
    audit_action = "удаление склада"


# =============================================================================
# MATERIAL - VIEWS
# =============================================================================

class MaterialListView(BaseListView):
    """Список материалов."""
    
    model = Material
    template_name = "inventory/material/list.html"
    context_object_name = "materials"
    ordering = ["name"]
    paginate_by = 20
    
    search_fields = ["name", "article", "part_number", "group", "vendor"]
    
    def get_queryset(self):
        qs = super().get_queryset().select_related("warehouse")
        
        # Фильтр по складу
        warehouse_id = self.request.GET.get("warehouse")
        if warehouse_id:
            qs = qs.filter(warehouse_id=warehouse_id)
        
        # Фильтр по статусу
        is_active = self.request.GET.get("is_active")
        if is_active == "1":
            qs = qs.filter(is_active=True)
        elif is_active == "0":
            qs = qs.filter(is_active=False)
        
        # Фильтр по статусу запаса
        stock_status = self.request.GET.get("stock_status")
        if stock_status == "in_stock":
            qs = qs.filter(is_active=True, qty_available__gt=0)
        elif stock_status == "low_stock":
            from django.db.models import F
            qs = qs.filter(is_active=True, qty_available__gt=0, qty_available__lte=F("min_stock_level"))
        elif stock_status == "out_of_stock":
            qs = qs.filter(is_active=True, qty_available=0)
        
        # Фильтр по группе
        group = self.request.GET.get("group")
        if group:
            qs = qs.filter(group__icontains=group)
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Статистика
        materials = self.get_queryset()
        summary = materials.aggregate(
            total_available=Sum("qty_available"),
            total_reserved=Sum("qty_reserved"),
        )
        
        context.update({
            "total_available": summary["total_available"] or 0,
            "total_reserved": summary["total_reserved"] or 0,
            "warehouses": Warehouse.objects.all().order_by("name"),
        })
        
        return context


class MaterialDetailView(BaseDetailView):
    """Детальная страница материала."""
    
    model = Material
    template_name = "inventory/material/detail.html"
    context_object_name = "material"
    
    select_related = ["warehouse"]
    prefetch_related = ["suitable_for"]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # История
        if hasattr(self.object, "history"):
            context["history"] = self.object.history.all()[:10]
        
        return context


def material_create(request):
    """Создание материала."""
    if request.method == "POST":
        form = MaterialForm(request.POST, request.FILES)
        
        if form.is_valid():
            material = form.save(commit=False)
            material._history_user = request.user
            material._change_reason = build_change_reason("создание материала")
            material.save()
            form.save_m2m()
            
            messages.success(request, "Материал создан.")
            return redirect("inventory:material_detail", pk=material.pk)
    else:
        initial = {}
        warehouse_id = request.GET.get("warehouse")
        if warehouse_id:
            initial["warehouse"] = warehouse_id
        
        form = MaterialForm(initial=initial)
    
    return render(request, "inventory/material/form.html", {
        "form": form,
        "create": True,
        "warehouses": Warehouse.objects.all().order_by("name"),
    })


def material_update(request, pk):
    """Редактирование материала."""
    material = get_object_or_404(Material, pk=pk)
    
    if request.method == "POST":
        form = MaterialForm(request.POST, request.FILES, instance=material)
        
        if form.is_valid():
            material = form.save(commit=False)
            material._history_user = request.user
            material._change_reason = build_change_reason("редактирование материала")
            material.save()
            form.save_m2m()
            
            messages.success(request, "Изменения сохранены.")
            return redirect("inventory:material_detail", pk=material.pk)
    else:
        form = MaterialForm(instance=material)
    
    return render(request, "inventory/material/form.html", {
        "form": form,
        "create": False,
        "object": material,
        "warehouses": Warehouse.objects.all().order_by("name"),
    })


class MaterialDeleteView(BaseDeleteView):
    """Удаление материала."""
    
    model = Material
    success_url = reverse_lazy("inventory:material_list")
    audit_action = "удаление материала"


# =============================================================================
# AJAX ENDPOINTS
# =============================================================================

@require_GET
def ajax_material_search(request):
    """AJAX поиск материалов для Tom Select."""
    q = request.GET.get("q", "").strip()
    limit = int(request.GET.get("limit", 20))
    
    qs = Material.objects.filter(is_active=True)
    
    if q:
        qs = qs.filter(
            Q(name__icontains=q) |
            Q(article__icontains=q) |
            Q(part_number__icontains=q)
        )
    
    qs = qs.select_related("warehouse")[:limit]
    
    results = []
    for m in qs:
        results.append({
            "id": m.pk,
            "text": m.name,
            "article": m.article,
            "warehouse": m.warehouse.name if m.warehouse else None,
            "qty_available": float(m.qty_available),
            "uom": m.get_uom_display(),
            "image": m.image.url if m.image else None,
        })
    
    return JsonResponse({"results": results})


@require_GET
def ajax_warehouse_search(request):
    """AJAX поиск складов для Tom Select."""
    q = request.GET.get("q", "").strip()
    limit = int(request.GET.get("limit", 20))
    
    qs = Warehouse.objects.all()
    
    if q:
        qs = qs.filter(name__icontains=q)
    
    qs = qs.select_related("location")[:limit]
    
    results = []
    for w in qs:
        results.append({
            "id": w.pk,
            "text": w.name,
            "location": w.location.name if w.location else None,
        })
    
    return JsonResponse({"results": results})
