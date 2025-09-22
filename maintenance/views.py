from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView, DetailView, DeleteView
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from datetime import timedelta
from dateutil.relativedelta import relativedelta

from .models import WorkOrder, WorkOrderStatus, Priority, WorkCategory, PlannedOrder, IntervalUnit
from .forms import WorkOrderForm, WorkOrderMaterialFormSet
from hr.models import HumanResource

# ---------- HOME как был ----------
def home(request):
    stats = {
        "total": WorkOrder.objects.count(),
        "new": WorkOrder.objects.filter(status=WorkOrderStatus.NEW).count(),
        "in_progress": WorkOrder.objects.filter(status=WorkOrderStatus.IN_PROGRESS).count(),
        "done": WorkOrder.objects.filter(status=WorkOrderStatus.DONE).count(),
        "failed": WorkOrder.objects.filter(status=WorkOrderStatus.FAILED).count(),
    }
    upcoming = PlannedOrder.objects.filter(is_active=True, next_run__isnull=False).order_by("next_run")[:10]
    return render(request, "maintenance/home.html", {"stats": stats, "upcoming": upcoming})

# ---------- WORK ORDERS ----------
class WorkOrderListView(ListView):
    model = WorkOrder
    template_name = "maintenance/wo_list.html"
    paginate_by = 20
    ordering = ["-id"]

    def get_queryset(self):
        qs = WorkOrder.objects.select_related("responsible", "workstation", "location").order_by("-id")
        q = self.request.GET.get("q") or ""
        status = self.request.GET.get("status") or ""
        prio = self.request.GET.get("priority") or ""
        cat = self.request.GET.get("category") or ""
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        if status:
            qs = qs.filter(status=status)
        if prio:
            qs = qs.filter(priority=prio)
        if cat:
            qs = qs.filter(category=cat)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["q"] = self.request.GET.get("q", "")
        ctx["status_choices"] = WorkOrderStatus.choices
        ctx["priority_choices"] = Priority.choices
        ctx["category_choices"] = WorkCategory.choices
        ctx["current"] = {
            "status": self.request.GET.get("status", ""),
            "priority": self.request.GET.get("priority", ""),
            "category": self.request.GET.get("category", ""),
        }
        return ctx

class WorkOrderDetailView(DetailView):
    model = WorkOrder
    template_name = "maintenance/wo_detail.html"

def workorder_create(request):
    if request.method == "POST":
        form = WorkOrderForm(request.POST, request.FILES)
        formset = WorkOrderMaterialFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            wo = form.save()
            if wo.workstation and not wo.location:
                wo.location = wo.workstation.location
                wo.save(update_fields=["location"])
            formset.instance = wo
            formset.save()
            messages.success(request, "Задача создана.")
            return redirect("maintenance:wo_detail", pk=wo.pk)
    else:
        form = WorkOrderForm()
        formset = WorkOrderMaterialFormSet()
    return render(request, "maintenance/wo_form.html", {"form": form, "formset": formset, "create": True})

def workorder_update(request, pk:int):
    wo = get_object_or_404(WorkOrder, pk=pk)
    if request.method == "POST":
        form = WorkOrderForm(request.POST, request.FILES, instance=wo)
        formset = WorkOrderMaterialFormSet(request.POST, instance=wo)
        if form.is_valid() and formset.is_valid():
            wo = form.save()
            if wo.workstation and not wo.location:
                wo.location = wo.workstation.location
                wo.save(update_fields=["location"])
            formset.save()
            messages.success(request, "Изменения сохранены.")
            return redirect("maintenance:wo_detail", pk=wo.pk)
    else:
        form = WorkOrderForm(instance=wo)
        formset = WorkOrderMaterialFormSet(instance=wo)
    return render(request, "maintenance/wo_form.html", {"form": form, "formset": formset, "create": False, "wo": wo})

class WorkOrderDeleteView(DeleteView):
    model = WorkOrder
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("maintenance:wo_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_url"] = reverse("maintenance:wo_detail", args=[self.object.pk])
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            response = super().post(request, *args, **kwargs)
            messages.success(request, "Задача удалена.")
            return response
        except ProtectedError:
            messages.error(request, "Нельзя удалить: есть связанные объекты.")
            return redirect("maintenance:wo_detail", pk=self.object.pk)

# ---------- PLANNED ORDERS ----------
from django import forms
class PlannedOrderForm(forms.ModelForm):
    class Meta:
        model = PlannedOrder
        fields = [
            "name","description","workstation","location","responsible_default",
            "category","priority","labor_plan_hours",
            "start_from","next_run","interval_value","interval_unit","is_active"
        ]
        widgets = {
            "start_from": forms.DateTimeInput(attrs={"type":"datetime-local"}),
            "next_run": forms.DateTimeInput(attrs={"type":"datetime-local"}),
            "description": forms.Textarea(attrs={"rows":3}),
        }

class PlannedOrderListView(ListView):
    model = PlannedOrder
    template_name = "maintenance/plan_list.html"
    ordering = ["next_run"]
    paginate_by = 50

def planned_order_create(request):
    if request.method == "POST":
        form = PlannedOrderForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "План создан.")
            return redirect("maintenance:plan_list")
    else:
        form = PlannedOrderForm()
    return render(request, "maintenance/plan_form.html", {"form": form, "create": True})

def planned_order_update(request, pk:int):
    obj = get_object_or_404(PlannedOrder, pk=pk)
    if request.method == "POST":
        form = PlannedOrderForm(request.POST, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "План сохранён.")
            return redirect("maintenance:plan_list")
    else:
        form = PlannedOrderForm(instance=obj)
    return render(request, "maintenance/plan_form.html", {"form": form, "create": False, "obj": obj})

class PlannedOrderDeleteView(DeleteView):
    model = PlannedOrder
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("maintenance:plan_list")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # у нас нет отдельной карточки плана — вернёмся к списку
        ctx["cancel_url"] = reverse("maintenance:plan_list")
        return ctx

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        try:
            response = super().post(request, *args, **kwargs)
            messages.success(request, "План удалён.")
            return response
        except ProtectedError:
            messages.error(request, "Нельзя удалить: есть связанные объекты.")
            return redirect("maintenance:plan_list")

def planned_order_run_now(request, pk:int):
    obj = get_object_or_404(PlannedOrder, pk=pk)
    if request.method == "POST":
        resp = obj.responsible_default or HumanResource.objects.first()
        if resp:
            WorkOrder.objects.create(
                name=obj.name,
                responsible=resp,
                workstation=obj.workstation,
                location=obj.location,
                description=obj.description,
                category=obj.category or WorkCategory.PM,
                labor_plan_hours=obj.labor_plan_hours,
                priority=obj.priority or Priority.MED,
            )
            base = obj.next_run or timezone.now()
            def add_interval(dt, val, unit):
                if unit == IntervalUnit.MINUTE: return dt + timedelta(minutes=val)
                if unit == IntervalUnit.DAY:    return dt + relativedelta(days=val)
                if unit == IntervalUnit.WEEK:   return dt + relativedelta(weeks=val)
                if unit == IntervalUnit.MONTH:  return dt + relativedelta(months=val)
                return dt + timedelta(minutes=val)
            nxt = add_interval(base, obj.interval_value, obj.interval_unit)
            if obj.interval_unit == IntervalUnit.MINUTE:
                nxt = nxt.replace(second=0, microsecond=0)
            obj.next_run = nxt
            obj.save(update_fields=["next_run"])
            messages.success(request, "Задача создана из плана.")
    return redirect("maintenance:plan_list")
