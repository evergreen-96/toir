from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db.models.deletion import ProtectedError

from core.audit import build_change_reason
from .models import Warehouse, Material
from .forms import WarehouseForm, MaterialForm
from django.views.generic import ListView, DetailView

class WarehouseListView(ListView):
    model = Warehouse
    template_name = "inventory/wh_list.html"
    ordering = ["name"]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(name__icontains=q)
        return qs

class WarehouseDetailView(DetailView):
    model = Warehouse
    template_name = "inventory/wh_detail.html"

def warehouse_create(request):
    if request.method == "POST":
        form = WarehouseForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj._history_user = request.user
            obj._change_reason = build_change_reason(
                "создание склада"
            )
            obj.save()
            form.save_m2m()

            messages.success(request, "Склад создан.")
            return redirect("inventory:warehouse_detail", pk=obj.pk)
    else:
        form = WarehouseForm()
    return render(request, "inventory/wh_form.html", {"form": form, "create": True})

def warehouse_update(request, pk):
    obj = get_object_or_404(Warehouse, pk=pk)
    if request.method == "POST":
        form = WarehouseForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj._history_user = request.user
            obj._change_reason = build_change_reason(
                "редактирование склада"
            )
            obj.save()
            form.save_m2m()

            messages.success(request, "Изменения сохранены.")
            return redirect("inventory:warehouse_detail", pk=obj.pk)
    else:
        form = WarehouseForm(instance=obj)
    return render(request, "inventory/wh_form.html", {"form": form, "create": False, "obj": obj})

class WarehouseDeleteView(View):
    def post(self, request, pk):
        warehouse = get_object_or_404(Warehouse, pk=pk)

        try:
            warehouse._history_user = request.user
            warehouse._change_reason = build_change_reason(
                "удаление склада"
            )
            warehouse.delete()
            return JsonResponse({"ok": True})

        except ProtectedError as e:
            related = [str(obj) for obj in e.protected_objects]
            return JsonResponse({
                "ok": False,
                "error": "Нельзя удалить: есть связанные объекты",
                "related": related,
            }, status=400)

class MaterialListView(ListView):
    model = Material
    template_name = "inventory/material_list.html"
    paginate_by = 20
    ordering = ["name"]

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.GET.get("q")
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(group__icontains=q) |
                Q(article__icontains=q) |
                Q(part_number__icontains=q)
            )
        return qs

class MaterialDetailView(DetailView):
    model = Material
    template_name = "inventory/material_detail.html"

def material_create(request):
    if request.method == "POST":
        form = MaterialForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj._history_user = request.user
            obj._change_reason = build_change_reason(
                "создание материала"
            )
            obj.save()
            form.save_m2m()

            messages.success(request, "Материал создан.")
            return redirect("inventory:material_detail", pk=obj.pk)
    else:
        form = MaterialForm()
    return render(request, "inventory/material_form.html", {"form": form, "create": True})

def material_update(request, pk):
    obj = get_object_or_404(Material, pk=pk)
    if request.method == "POST":
        form = MaterialForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj._history_user = request.user
            obj._change_reason = build_change_reason(
                "редактирование материала"
            )
            obj.save()
            form.save_m2m()

            messages.success(request, "Изменения сохранены.")
            return redirect("inventory:material_detail", pk=obj.pk)
    else:
        form = MaterialForm(instance=obj)
    return render(request, "inventory/material_form.html", {"form": form, "create": False, "obj": obj})

class MaterialDeleteView(View):
    def post(self, request, pk):
        material = get_object_or_404(Material, pk=pk)

        try:
            material._history_user = request.user
            material._change_reason = build_change_reason(
                "удаление материала"
            )
            material.delete()
            return JsonResponse({"ok": True})

        except ProtectedError as e:
            related = [str(obj) for obj in e.protected_objects]
            return JsonResponse({
                "ok": False,
                "error": "Нельзя удалить: есть связанные объекты",
                "related": related,
            }, status=400)
