"""
Views для модуля locations.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView

from core.audit import build_change_reason
from .models import Location
from .forms import LocationForm


# =====================================================
# List (HTML only)
# =====================================================

class LocationListView(LoginRequiredMixin, ListView):
    """
    Отображает страницу со списком локаций.
    Само дерево подгружается через JS (jsTree).
    """
    model = Location
    template_name = "locations/location_list.html"


# =====================================================
# Tree JSON (for jsTree)
# =====================================================

class LocationTreeJsonView(LoginRequiredMixin, View):
    """AJAX: Дерево локаций для jsTree."""

    def get(self, request, *args, **kwargs):
        nodes = []

        qs = (
            Location.objects
            .select_related("parent", "responsible")
            .order_by("name")
        )

        for loc in qs:
            nodes.append({
                "id": str(loc.id),
                "parent": str(loc.parent_id) if loc.parent_id else "#",
                "text": loc.name,
                "data": {
                    "detail_url": reverse(
                        "locations:location_detail",
                        args=[loc.id]
                    ),
                    "meta": str(loc.responsible) if loc.responsible else ""
                }
            })

        return JsonResponse(nodes, safe=False)


# =====================================================
# Detail
# =====================================================

class LocationDetailView(LoginRequiredMixin, DetailView):
    """Детальная страница локации."""

    model = Location
    template_name = "locations/location_detail.html"

    def get_queryset(self):
        """Оптимизация запросов."""
        return super().get_queryset().select_related('parent', 'responsible')


# =====================================================
# Create
# =====================================================

@login_required
def location_create(request):
    """Создание новой локации."""
    if request.method == "POST":
        form = LocationForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj._history_user = request.user
            obj._change_reason = build_change_reason("создание локации")
            obj.save()
            form.save_m2m()

            messages.success(request, "Локация создана.")
            return redirect("locations:location_list")
    else:
        form = LocationForm()

    return render(request, "locations/location_form.html", {
        "form": form,
        "create": True,
    })


# =====================================================
# Update
# =====================================================

@login_required
def location_update(request, pk):
    """Редактирование локации."""
    location = get_object_or_404(Location, pk=pk)

    if request.method == "POST":
        form = LocationForm(request.POST, instance=location)
        if form.is_valid():
            obj = form.save(commit=False)
            obj._history_user = request.user
            obj._change_reason = build_change_reason("редактирование локации")
            obj.save()
            form.save_m2m()

            messages.success(request, "Локация обновлена.")
            return redirect("locations:location_detail", pk=pk)
    else:
        form = LocationForm(instance=location)

    return render(request, "locations/location_form.html", {
        "form": form,
        "create": False,
        "object": location,
    })


# =====================================================
# Delete
# =====================================================

class LocationDeleteView(LoginRequiredMixin, View):
    """Удаление локации."""

    def post(self, request, pk):
        """Обработка POST-запроса на удаление."""
        location = get_object_or_404(Location, pk=pk)

        try:
            location._history_user = request.user
            location._change_reason = build_change_reason("удаление локации")
            location.delete()

            return JsonResponse({"ok": True})

        except ProtectedError as e:
            return JsonResponse({
                "ok": False,
                "error": "Нельзя удалить: есть связанные объекты",
                "related": [str(obj) for obj in e.protected_objects],
            }, status=400)