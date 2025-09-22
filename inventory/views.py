from django.views.generic import ListView, DetailView, DeleteView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from .models import Warehouse, Material
from .forms import WarehouseForm, MaterialForm


class WarehouseListView(ListView):
    model = Warehouse
    template_name = "inventory/wh_list.html"
    ordering = ["name"]

class WarehouseDetailView(DetailView):
    model = Warehouse
    template_name = "inventory/wh_detail.html"

def warehouse_create(request):
    if request.method == "POST":
        form = WarehouseForm(request.POST)
        if form.is_valid():
            obj = form.save()
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
            obj = form.save()
            messages.success(request, "Изменения сохранены.")
            return redirect("inventory:warehouse_detail", pk=obj.pk)
    else:
        form = WarehouseForm(instance=obj)
    return render(request, "inventory/wh_form.html", {"form": form, "create": False, "obj": obj})

class WarehouseDeleteView(DeleteView):
    model = Warehouse
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("inventory:warehouse_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse("inventory:warehouse_detail", args=[self.object.pk])
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            response = super().post(request, *args, **kwargs)
            messages.success(request, "Склад удалён.")
            return response
        except ProtectedError:
            messages.error(request, "Нельзя удалить: есть связанные объекты.")
            return redirect("inventory:warehouse_detail", pk=self.object.pk)

class MaterialListView(ListView):
    model = Material
    template_name = "inventory/material_list.html"
    paginate_by = 20
    ordering = ["name"]

class MaterialDetailView(DetailView):
    model = Material
    template_name = "inventory/material_detail.html"

def material_create(request):
    if request.method == "POST":
        form = MaterialForm(request.POST)
        if form.is_valid():
            obj = form.save()
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
            obj = form.save()
            messages.success(request, "Изменения сохранены.")
            return redirect("inventory:material_detail", pk=obj.pk)
    else:
        form = MaterialForm(instance=obj)
    return render(request, "inventory/material_form.html", {"form": form, "create": False, "obj": obj})

class MaterialDeleteView(DeleteView):
    model = Material
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("inventory:material_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse("inventory:material_detail", args=[self.object.pk])
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            response = super().post(request, *args, **kwargs)
            messages.success(request, "Материал удалён.")
            return response
        except ProtectedError:
            messages.error(request, "Нельзя удалить: есть связанные объекты.")
            return redirect("inventory:material_detail", pk=self.object.pk)
