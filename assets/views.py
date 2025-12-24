from django.db.models import Q
from django.http import JsonResponse
from django.views import View
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import ListView, DetailView, DeleteView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django import forms

from .models import Workstation, WorkstationStatus
from locations.models import Location


# =======================
# Form
# =======================

class WorkstationForm(forms.ModelForm):
    class Meta:
        model = Workstation
        fields = [
            "name",
            "category",
            "type_name",
            "manufacturer",
            "model",
            "global_state",
            "status",
            "description",
            "serial_number",
            "location",
            "commissioning_date",
            "warranty_until",
            "responsible",
            "photo",
            "inventory_number",
        ]


# =======================
# List
# =======================

class WorkstationListView(ListView):
    model = Workstation
    template_name = "assets/ws_list.html"
    paginate_by = 20
    ordering = ["name"]

    def get_queryset(self):
        qs = super().get_queryset()

        q = self.request.GET.get("q")
        category = self.request.GET.get("category")
        status = self.request.GET.get("status")
        location = self.request.GET.get("location")

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(type_name__icontains=q) |
                Q(model__icontains=q)
            )

        if category:
            qs = qs.filter(category=category)

        if status:
            qs = qs.filter(status=status)

        if location:
            qs = qs.filter(location_id=location)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["categories"] = (
            Workstation._meta.get_field("category").choices
        )
        ctx["statuses"] = (
            Workstation._meta.get_field("status").choices
        )
        ctx["locations"] = Location.objects.all()

        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["current_category"] = self.request.GET.get("category", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_location"] = self.request.GET.get("location", "")

        return ctx


# =======================
# Detail
# =======================

class WorkstationDetailView(DetailView):
    model = Workstation
    template_name = "assets/ws_detail.html"


# =======================
# Create
# =======================

def ws_create(request):
    if request.method == "POST":
        form = WorkstationForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj._history_user = request.user
            obj._change_reason = build_change_reason(
                "создание оборудования"
            )
            obj.save()
            form.save_m2m()
            messages.success(request, "Оборудование создано.")
            return redirect("assets:asset_detail", pk=obj.pk)
    else:
        form = WorkstationForm()

    return render(request, "assets/ws_form.html", {
        "form": form,
        "create": True,
    })


# =======================
# Update
# =======================

def ws_update(request, pk):
    obj = get_object_or_404(Workstation, pk=pk)

    if request.method == "POST":
        form = WorkstationForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            from core.audit import build_change_reason

            obj = form.save(commit=False)
            obj._history_user = request.user
            obj._change_reason = build_change_reason(
                "редактирование оборудования"
            )
            obj.save()
            form.save_m2m()
            messages.success(request, "Изменения сохранены.")
            return redirect("assets:asset_detail", pk=obj.pk)
    else:
        form = WorkstationForm(instance=obj)

    return render(request, "assets/ws_form.html", {
        "form": form,
        "create": False,
        "object": obj,
    })


# =======================
# Delete
# =======================

class WorkstationDeleteView(View):
    def post(self, request, pk):
        obj = get_object_or_404(Workstation, pk=pk)

        try:
            obj._history_user = request.user
            obj._change_reason = build_change_reason(
                "удаление оборудования"
            )
            obj.delete()
            return JsonResponse({"ok": True})

        except ProtectedError as e:
            return JsonResponse({
                "ok": False,
                "error": "Нельзя удалить: есть связанные объекты",
                "related": [str(o) for o in e.protected_objects],
            }, status=400)


@require_GET
def ajax_get_workstation_status(request):
    ws_id = request.GET.get("id")
    ws = get_object_or_404(Workstation, pk=ws_id)

    return JsonResponse({
        "ok": True,
        "current": ws.status,
        "choices": WorkstationStatus.choices,
    })


from core.audit import build_change_reason


@require_POST
def ajax_update_workstation_status(request):
    ws_id = request.POST.get("id")
    status = request.POST.get("status")

    ws = get_object_or_404(Workstation, pk=ws_id)

    if not request.user.is_staff:
        return JsonResponse({"ok": False}, status=403)

    valid_statuses = {choice[0] for choice in WorkstationStatus.choices}
    if status not in valid_statuses:
        return JsonResponse(
            {"ok": False, "error": "invalid_status"},
            status=400,
        )

    ws.status = status

    # 🔑 AUDIT — ОБЯЗАТЕЛЬНО
    ws._history_user = request.user
    ws._change_reason = build_change_reason(
        "смена статуса оборудования"
    )

    ws.save(update_fields=["status"])

    return JsonResponse({"ok": True})

