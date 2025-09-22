from django.views.generic import ListView, DetailView, DeleteView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django import forms
from .models import Location

class LocationForm(forms.ModelForm):
    class Meta:
        model = Location
        fields = ["name", "level", "parent", "responsible"]

class LocationListView(ListView):
    model = Location
    template_name = "locations/location_list.html"
    paginate_by = 20
    ordering = ["level", "name"]

class LocationDetailView(DetailView):
    model = Location
    template_name = "locations/location_detail.html"

def location_create(request):
    if request.method == "POST":
        form = LocationForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Локация создана.")
            return redirect("locations:location_detail", pk=obj.pk)
    else:
        form = LocationForm()
    return render(request, "locations/location_form.html", {"form": form, "create": True})

def location_update(request, pk):
    obj = get_object_or_404(Location, pk=pk)
    if request.method == "POST":
        form = LocationForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save()
            messages.success(request, "Изменения сохранены.")
            return redirect("locations:location_detail", pk=obj.pk)
    else:
        form = LocationForm(instance=obj)
    return render(request, "locations/location_form.html", {"form": form, "create": False, "obj": obj})

class LocationDeleteView(DeleteView):
    model = Location
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("locations:location_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse("locations:location_detail", args=[self.object.pk])
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            response = super().post(request, *args, **kwargs)
            messages.success(request, "Локация удалена.")
            return response
        except ProtectedError:
            messages.error(request, "Нельзя удалить: есть связанные объекты.")
            return redirect("locations:location_detail", pk=self.object.pk)
