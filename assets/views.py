from django.views.generic import ListView, DetailView, DeleteView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django import forms
from .models import Workstation

class WorkstationForm(forms.ModelForm):
    class Meta:
        model = Workstation
        fields = [
            "name","category","type_name","manufacturer","model",
            "global_state","status","description","serial_number",
            "location","commissioning_date","warranty_until",
            "responsible","photo","inventory_number",
        ]

class WorkstationListView(ListView):
    model = Workstation
    template_name = "assets/ws_list.html"
    paginate_by = 20
    ordering = ["name"]

class WorkstationDetailView(DetailView):
    model = Workstation
    template_name = "assets/ws_detail.html"

def ws_create(request):
    if request.method == "POST":
        form = WorkstationForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Оборудование создано.")
            return redirect("assets:asset_detail", pk=obj.pk)
    else:
        form = WorkstationForm()
    return render(request, "assets/ws_form.html", {"form": form, "create": True})

def ws_update(request, pk):
    obj = get_object_or_404(Workstation, pk=pk)
    if request.method == "POST":
        form = WorkstationForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Изменения сохранены.")
            return redirect("assets:asset_detail", pk=obj.pk)
    else:
        form = WorkstationForm(instance=obj)
    return render(request, "assets/ws_form.html", {"form": form, "create": False, "obj": obj})

class WorkstationDeleteView(DeleteView):
    model = Workstation
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("assets:asset_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse("assets:asset_detail", args=[self.object.pk])
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            response = super().post(request, *args, **kwargs)
            messages.success(request, "Оборудование удалено.")
            return response
        except ProtectedError:
            messages.error(request, "Нельзя удалить: есть связанные объекты.")
            return redirect("assets:asset_detail", pk=self.object.pk)
