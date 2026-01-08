"""
maintenance/views.py

Рефакторинг с использованием базовых классов из core.
"""

from __future__ import annotations

import calendar
from datetime import datetime, time, timedelta
from typing import Any

from dateutil.relativedelta import relativedelta
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.db.models.functions import TruncDate
from django.http import JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST, require_GET
from django.views.generic import DetailView

from assets.models import Workstation, WorkstationStatus, WorkstationGlobalState
from core.audit import build_change_reason
from core.views import BaseListView, BaseDetailView, BaseDeleteView
from hr.models import HumanResource
from locations.models import Location
from .forms import WorkOrderMaterialFormSet, WorkOrderForm, PlannedOrderForm
from .models import (
    WorkOrder, PlannedOrder, WorkOrderStatus, WorkCategory,
    Priority, IntervalUnit, WorkOrderAttachment, File
)


# =============================================================================
# КОНСТАНТЫ И УТИЛИТЫ
# =============================================================================

RUN_TIME = time(0, 0, 1)


def _last_day_of_month(y: int, m: int) -> int:
    """Возвращает последний день месяца."""
    return calendar.monthrange(y, m)[1]


def _clamp_dom(y: int, m: int, dom: int) -> int:
    """Если dom > числа дней в месяце — возвращает последний день месяца."""
    return min(dom, _last_day_of_month(y, m))


def _get_work_order_counts(**filters) -> int:
    """Утилита для подсчета рабочих задач с фильтрами."""
    return WorkOrder.objects.filter(**filters).count()


# =============================================================================
# DASHBOARD
# =============================================================================

def home(request: HttpRequest):
    """Главная страница — дашборд ТОиР."""
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    # KPI: сегодня + дельта
    stats_today = {
        "new": _get_work_order_counts(status=WorkOrderStatus.NEW, created_at__date=today),
        "in_progress": _get_work_order_counts(status=WorkOrderStatus.IN_PROGRESS),
        "done": _get_work_order_counts(status=WorkOrderStatus.DONE, date_finish=today),
        "failed": _get_work_order_counts(status=WorkOrderStatus.FAILED, created_at__date=today),
    }

    stats_yesterday = {
        "new": _get_work_order_counts(status=WorkOrderStatus.NEW, created_at__date=yesterday),
        "done": _get_work_order_counts(status=WorkOrderStatus.DONE, date_finish=yesterday),
    }

    stats = {
        **stats_today,
        "delta_new": stats_today["new"] - stats_yesterday["new"],
        "delta_done": stats_today["done"] - stats_yesterday["done"],
    }

    # Доступность оборудования
    workstations = Workstation.objects.filter(global_state=WorkstationGlobalState.ACTIVE)
    prod = workstations.filter(status=WorkstationStatus.PROD).count()
    maint = workstations.filter(status=WorkstationStatus.MAINT).count()
    setup = workstations.filter(status=WorkstationStatus.SETUP).count()
    problem = workstations.filter(status=WorkstationStatus.PROBLEM).count()
    denominator = prod + maint + setup + problem

    availability = {
        "pct": round((prod / denominator * 100), 1) if denominator else 0.0,
        "in_prod": prod,
        "not_working": maint + setup,
        "emergency": problem,
        "total": denominator,
    }

    # Выполнено сегодня
    done_today = WorkOrder.objects.filter(status=WorkOrderStatus.DONE, date_finish=today)
    done_stats = {
        "pm": done_today.filter(category=WorkCategory.PM).count(),
        "emergency": done_today.filter(category=WorkCategory.EMERGENCY).count(),
    }

    # По ответственным
    done_by_people = (
        done_today.values("responsible__name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    # По категориям (сегодня)
    orders_by_category = (
        WorkOrder.objects.filter(created_at__date=today)
        .values("category")
        .annotate(cnt=Count("id"))
    )

    # За 7 дней (график)
    orders_7d = (
        WorkOrder.objects.filter(created_at__date__gte=today - timedelta(days=6))
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(cnt=Count("id"))
        .order_by("day")
    )

    # Ближайшие плановые работы
    upcoming = (
        PlannedOrder.objects.filter(
            is_active=True,
            next_run__isnull=False,
            next_run__gte=timezone.now()
        )
        .select_related("workstation", "location", "responsible_default")
        .order_by("next_run")[:10]
    )

    return render(request, "maintenance/home.html", {
        "stats": stats,
        "availability": availability,
        "done_stats": done_stats,
        "done_by_people": done_by_people,
        "orders_by_category": orders_by_category,
        "orders_7d": orders_7d,
        "upcoming": upcoming,
    })


# =============================================================================
# WORK ORDERS - LIST
# =============================================================================

class WorkOrderListView(BaseListView):
    """Список рабочих задач."""

    model = WorkOrder
    template_name = "maintenance/wo_list.html"
    context_object_name = "work_orders"
    paginate_by = 20
    ordering = ["-id"]

    search_fields = ['name', 'description']
    select_related = ['responsible', 'workstation', 'location']

    def get_queryset(self):
        """Фильтрация queryset."""
        queryset = super().get_queryset()

        status = self.request.GET.get("status", "")
        if status:
            queryset = queryset.filter(status=status)

        priority = self.request.GET.get("priority", "")
        if priority:
            queryset = queryset.filter(priority=priority)

        category = self.request.GET.get("category", "")
        if category:
            queryset = queryset.filter(category=category)

        responsible = self.request.GET.get("responsible", "")
        if responsible:
            queryset = queryset.filter(responsible_id=responsible)

        return queryset

    def get_context_data(self, **kwargs):
        """Контекст для фильтров."""
        context = super().get_context_data(**kwargs)
        context.update({
            "status_choices": WorkOrderStatus.choices,
            "priority_choices": Priority.choices,
            "category_choices": WorkCategory.choices,
            "responsibles": HumanResource.objects.filter(is_active=True).order_by('name'),
            "filter_params": {
                "q": self.request.GET.get("q", ""),
                "status": self.request.GET.get("status", ""),
                "priority": self.request.GET.get("priority", ""),
                "category": self.request.GET.get("category", ""),
                "responsible": self.request.GET.get("responsible", ""),
            },
            "stats": {
                "total": WorkOrder.objects.count(),
                "new": WorkOrder.objects.filter(status=WorkOrderStatus.NEW).count(),
                "in_progress": WorkOrder.objects.filter(status=WorkOrderStatus.IN_PROGRESS).count(),
                "done": WorkOrder.objects.filter(status=WorkOrderStatus.DONE).count(),
            }
        })
        return context


# =============================================================================
# WORK ORDERS - DETAIL
# =============================================================================

class WorkOrderDetailView(BaseDetailView):
    """Детальная страница рабочей задачи."""

    model = WorkOrder
    template_name = "maintenance/wo_detail.html"
    context_object_name = "object"

    select_related = ['responsible', 'workstation', 'location', 'created_from_plan']

    def get_context_data(self, **kwargs):
        """Дополнительный контекст."""
        context = super().get_context_data(**kwargs)
        work_order = self.object

        context.update({
            "allowed_transitions": work_order.get_allowed_transitions(),
            "attachments": work_order.attachments.select_related("file"),
            "materials": work_order.materials.select_related("material"),
        })

        if work_order.workstation:
            context["workstation_statuses"] = WorkstationStatus.choices

        # История
        if hasattr(work_order, 'history'):
            context['history'] = work_order.history.all()[:10]

        return context


# =============================================================================
# WORK ORDERS - CREATE/UPDATE
# =============================================================================

def workorder_create(request: HttpRequest):
    """Создание новой рабочей задачи."""
    if request.method == "POST":
        form = WorkOrderForm(request.POST, request.FILES)
        formset = WorkOrderMaterialFormSet(request.POST, prefix='materials')

        if form.is_valid() and formset.is_valid():
            work_order = form.save(commit=False)

            # Автозаполнение локации
            if work_order.workstation and not work_order.location:
                work_order.location = work_order.workstation.location

            if request.user.is_authenticated:
                work_order._history_user = request.user
            work_order._change_reason = build_change_reason("создание задачи обслуживания")
            work_order.save()

            _handle_work_order_files(request, work_order)

            formset.instance = work_order
            formset.save()

            messages.success(request, "Задача создана.")
            return redirect("maintenance:wo_detail", pk=work_order.pk)

        messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
    else:
        form = WorkOrderForm()
        formset = WorkOrderMaterialFormSet(prefix='materials')

    all_files = File.objects.order_by("-uploaded_at")

    return render(request, "maintenance/wo_form.html", {
        "form": form,
        "formset": formset,
        "create": True,
        "all_files": all_files,
    })


def workorder_update(request: HttpRequest, pk: int):
    """Редактирование рабочей задачи."""
    work_order = get_object_or_404(WorkOrder, pk=pk)

    if request.method == "POST":
        form = WorkOrderForm(request.POST, request.FILES, instance=work_order)
        formset = WorkOrderMaterialFormSet(request.POST, instance=work_order, prefix='materials')

        if form.is_valid() and formset.is_valid():
            work_order = form.save(commit=False)
            work_order._history_user = request.user
            work_order._change_reason = build_change_reason("редактирование задачи обслуживания")
            work_order.save()

            _handle_work_order_files(request, work_order)

            formset.save()

            messages.success(request, "Изменения сохранены.")
            return redirect("maintenance:wo_detail", pk=work_order.pk)
    else:
        form = WorkOrderForm(instance=work_order)
        formset = WorkOrderMaterialFormSet(instance=work_order, prefix='materials')

    attached_file_ids = work_order.attachments.values_list("file_id", flat=True)
    all_files = File.objects.exclude(id__in=attached_file_ids).order_by("-uploaded_at")

    return render(request, "maintenance/wo_form.html", {
        "form": form,
        "formset": formset,
        "create": False,
        "wo": work_order,
        "object": work_order,
        "all_files": all_files,
    })


# =============================================================================
# WORK ORDERS - DELETE
# =============================================================================

class WorkOrderDeleteView(BaseDeleteView):
    """Удаление рабочей задачи."""

    model = WorkOrder
    success_url = reverse_lazy('maintenance:wo_list')
    audit_action = "удаление задачи обслуживания"

    def delete_object(self, obj):
        """Удаление с очисткой вложений."""
        obj.attachments.all().delete()
        super().delete_object(obj)


# =============================================================================
# WORK ORDERS - STATUS
# =============================================================================

@require_POST
def wo_set_status(request: HttpRequest, pk: int, status: str):
    """Изменение статуса рабочей задачи."""
    work_order = get_object_or_404(WorkOrder, pk=pk)

    try:
        if request.user.is_authenticated:
            work_order._history_user = request.user
        work_order._change_reason = build_change_reason(f"смена статуса задачи → {status}")
        work_order.set_status(status)

        messages.success(request, f"Статус изменён на «{work_order.get_status_display()}».")
    except ValueError:
        messages.error(request, "Недопустимый переход статуса.")

    return redirect("maintenance:wo_detail", pk=pk)


# =============================================================================
# WORK ORDERS - FILES UTILITY
# =============================================================================

def _handle_work_order_files(request: HttpRequest, work_order: WorkOrder) -> None:
    """Обработка файлов для рабочей задачи."""
    existing_file_ids = [int(fid) for fid in request.POST.getlist("existing_files") if fid.isdigit()]

    attachments_qs = WorkOrderAttachment.objects.filter(work_order=work_order)
    if existing_file_ids:
        attachments_qs.exclude(file_id__in=existing_file_ids).delete()
    else:
        attachments_qs.delete()

    for file_id in existing_file_ids:
        WorkOrderAttachment.objects.get_or_create(work_order=work_order, file_id=file_id)

    for uploaded_file in request.FILES.getlist("files"):
        file_obj = File(file=uploaded_file)
        file_obj.save()
        WorkOrderAttachment.objects.create(work_order=work_order, file=file_obj)


# =============================================================================
# PLANNED ORDERS - LIST
# =============================================================================

class PlannedOrderListView(BaseListView):
    """Список плановых работ."""

    model = PlannedOrder
    template_name = "maintenance/plan_list.html"
    context_object_name = "plans"
    paginate_by = 50
    ordering = ["next_run"]

    search_fields = ['name', 'description']
    select_related = ['workstation', 'location', 'responsible_default']

    def get_queryset(self):
        """Фильтрация."""
        queryset = super().get_queryset()

        is_active = self.request.GET.get("is_active", "")
        if is_active == "1":
            queryset = queryset.filter(is_active=True)
        elif is_active == "0":
            queryset = queryset.filter(is_active=False)

        interval_unit = self.request.GET.get("interval_unit", "")
        if interval_unit:
            queryset = queryset.filter(interval_unit=interval_unit)

        return queryset

    def get_context_data(self, **kwargs):
        """Контекст."""
        context = super().get_context_data(**kwargs)
        context.update({
            "interval_units": IntervalUnit.choices,
            "filter_params": {
                "q": self.request.GET.get("q", ""),
                "is_active": self.request.GET.get("is_active", ""),
                "interval_unit": self.request.GET.get("interval_unit", ""),
            },
            "stats": {
                "total": PlannedOrder.objects.count(),
                "active": PlannedOrder.objects.filter(is_active=True).count(),
                "inactive": PlannedOrder.objects.filter(is_active=False).count(),
            }
        })
        return context


# =============================================================================
# PLANNED ORDERS - DETAIL
# =============================================================================

class PlannedOrderDetailView(BaseDetailView):
    """Детальная страница плановой работы."""

    model = PlannedOrder
    template_name = "maintenance/plan_detail.html"
    context_object_name = "object"

    select_related = ['workstation', 'location', 'responsible_default']

    def get_context_data(self, **kwargs):
        """Добавляет связанные рабочие задачи."""
        context = super().get_context_data(**kwargs)
        planned_order = self.object

        context["work_orders"] = (
            planned_order.work_orders
            .select_related("responsible", "workstation")
            .order_by("-created_at")[:10]
        )

        if hasattr(planned_order, 'history'):
            context['history'] = planned_order.history.all()[:10]

        return context


# =============================================================================
# PLANNED ORDERS - CREATE/UPDATE
# =============================================================================

def planned_order_create(request: HttpRequest):
    """Создание плановой работы."""
    if request.method == "POST":
        form = PlannedOrderForm(request.POST)

        if not form.has_changed():
            messages.warning(request, "Форма пуста. Заполните параметры плана.")
        elif form.is_valid():
            planned_order = form.save(commit=False)
            planned_order._history_user = request.user
            planned_order._change_reason = build_change_reason("создание плановых работ")
            planned_order.save()

            messages.success(request, "План создан.")

            if request.POST.get('save_and_add'):
                return redirect('maintenance:plan_new')
            return redirect("maintenance:plan_list")
    else:
        form = PlannedOrderForm()

    context = _get_planned_order_form_context(form, create=True)
    return render(request, "maintenance/plan_form.html", context)


def planned_order_update(request: HttpRequest, pk: int):
    """Редактирование плановой работы."""
    planned_order = get_object_or_404(PlannedOrder, pk=pk)

    if request.method == "POST":
        form = PlannedOrderForm(request.POST, instance=planned_order)

        if form.is_valid():
            planned_order = form.save(commit=False)
            planned_order._history_user = request.user
            planned_order._change_reason = build_change_reason("редактирование плановых работ")
            planned_order.save()

            messages.success(request, "План сохранён.")
            return redirect("maintenance:plan_list")
    else:
        form = PlannedOrderForm(instance=planned_order)

    context = _get_planned_order_form_context(form, create=False, obj=planned_order)
    return render(request, "maintenance/plan_form.html", context)


def _get_planned_order_form_context(form, create=True, obj=None):
    """Общий контекст для формы плановых работ."""
    all_locations = list(Location.objects.all().order_by('name')[:100])
    all_responsibles = list(HumanResource.objects.filter(is_active=True).order_by('name')[:100])
    all_workstations = list(Workstation.objects.all().order_by('name')[:100]) if not create else []

    return {
        "form": form,
        "create": create,
        "object": obj,
        "all_locations": all_locations,
        "all_responsibles": all_responsibles,
        "all_workstations": all_workstations,
        "location_workstations": {
            loc.id: list(Workstation.objects.filter(location=loc).order_by('name').values('id', 'name'))
            for loc in all_locations[:20]
        }
    }


# =============================================================================
# PLANNED ORDERS - DELETE
# =============================================================================

class PlannedOrderDeleteView(BaseDeleteView):
    """Удаление плановой работы."""

    model = PlannedOrder
    success_url = reverse_lazy('maintenance:plan_list')
    audit_action = "удаление плановых работ"


# =============================================================================
# PLANNED ORDERS - RUN NOW
# =============================================================================

def planned_order_run_now(request: HttpRequest, pk: int):
    """Создание рабочей задачи из плана и расчет следующего запуска."""
    planned_order = get_object_or_404(PlannedOrder, pk=pk)

    if request.method == "POST":
        responsible = planned_order.responsible_default or HumanResource.objects.first()

        if responsible:
            work_order = WorkOrder.objects.create(
                name=planned_order.name,
                responsible=responsible,
                workstation=planned_order.workstation,
                location=planned_order.location,
                description=planned_order.description,
                category=planned_order.category or WorkCategory.PM,
                labor_plan_hours=planned_order.labor_plan_hours,
                priority=planned_order.priority or Priority.MED,
                created_from_plan=planned_order,
            )

            work_order._history_user = request.user
            work_order._change_reason = build_change_reason(f"создание задачи из плана #{planned_order.pk}")
            work_order.save()

            next_run = _calculate_next_planned_run(planned_order)

            planned_order._history_user = request.user
            planned_order._change_reason = build_change_reason("ручной запуск плана")
            planned_order.next_run = next_run
            planned_order.save(update_fields=["next_run"])

            messages.success(request, "Задача создана из плана.")

    return redirect("maintenance:plan_list")


def _calculate_next_planned_run(planned_order: PlannedOrder) -> datetime:
    """Расчет даты следующего запуска."""
    now = timezone.now()
    base = planned_order.next_run or now

    unit = planned_order.interval_unit
    val = planned_order.interval_value

    if unit == IntervalUnit.MINUTE:
        return base + timedelta(minutes=val)
    elif unit == IntervalUnit.DAY:
        return base + relativedelta(days=val)
    elif unit == IntervalUnit.WEEK:
        return base + relativedelta(weeks=val)
    elif unit == IntervalUnit.MONTH:
        next_dt = base + relativedelta(months=val)
        day = _clamp_dom(next_dt.year, next_dt.month, base.day)
        return next_dt.replace(day=day)

    return base + timedelta(days=1)


# =============================================================================
# AJAX ENDPOINTS
# =============================================================================

@require_GET
def get_workstations_by_location(request: HttpRequest) -> JsonResponse:
    """AJAX-запрос для получения оборудования по локации."""
    location_id = request.GET.get("location_id", "").strip()

    if not location_id:
        return JsonResponse({"ok": True, "items": []})

    try:
        workstations = Workstation.objects.filter(location_id=location_id).values("id", "name")
        items = [{"id": w["id"], "text": w["name"]} for w in workstations]
        return JsonResponse({"ok": True, "items": items})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


@require_GET
def ajax_locations(request: HttpRequest) -> JsonResponse:
    """AJAX поиск локаций для TomSelect."""
    query = request.GET.get('q', '').strip()

    locations = Location.objects.all().order_by('name')

    if query:
        locations = locations.filter(name__icontains=query)

    results = [{"value": loc.id, "text": loc.name} for loc in locations[:50]]

    return JsonResponse({"results": results})


@require_GET
def ajax_responsibles(request: HttpRequest) -> JsonResponse:
    """AJAX поиск ответственных сотрудников для TomSelect."""
    query = request.GET.get('q', '').strip()

    responsibles = HumanResource.objects.filter(is_active=True).order_by('name')

    if query:
        responsibles = responsibles.filter(name__icontains=query)

    results = [{"value": hr.id, "text": hr.name} for hr in responsibles[:50]]

    return JsonResponse({"results": results})


@require_GET
def ajax_all_job_titles(request: HttpRequest) -> JsonResponse:
    """AJAX получение всех уникальных должностей для автодополнения."""
    job_titles = HumanResource.objects.filter(
        job_title__isnull=False
    ).values_list('job_title', flat=True).distinct().order_by('job_title')

    results = [{"value": title, "text": title} for title in job_titles]

    return JsonResponse({"results": results})


@require_GET
def api_workstations(request: HttpRequest) -> JsonResponse:
    """API endpoint для получения списка оборудования по локации."""
    location_id = request.GET.get('location')

    if not location_id:
        return JsonResponse([], safe=False)

    try:
        location_id = int(location_id)
    except (TypeError, ValueError):
        return JsonResponse([], safe=False)

    workstations = Workstation.objects.filter(
        location_id=location_id
    ).order_by('name').values('id', 'name')

    return JsonResponse(list(workstations), safe=False)


@require_GET
def ajax_material_search(request: HttpRequest) -> JsonResponse:
    """Поиск материалов для Select2."""
    from django.core.paginator import Paginator
    from inventory.models import Material

    query = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)

    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1

    materials = Material.objects.filter(is_active=True).order_by('name')

    if query:
        materials = materials.filter(
            Q(name__icontains=query) |
            Q(article__icontains=query)
        )

    paginator = Paginator(materials, 20)
    try:
        page_obj = paginator.page(page)
    except Exception:
        page_obj = paginator.page(1)

    results = []
    for material in page_obj:
        result = {
            'id': material.id,
            'text': material.name,
            'article': getattr(material, 'article', '') or '',
        }

        if hasattr(material, 'image') and material.image:
            result['image_url'] = material.image.url
        else:
            result['image_url'] = ''

        results.append(result)

    return JsonResponse({
        'results': results,
        'pagination': {'more': page_obj.has_next()}
    })


@require_GET
def planned_order_preview(request: HttpRequest) -> JsonResponse:
    """
    AJAX превью дат запуска плановой работы.
    
    GET-параметры:
        frequency_choice: daily|weekly|monthly|custom
        first_run_date: YYYY-MM-DD
        weekday: 0..6
        day_of_month: 1..31
        interval_value, interval_unit (for custom)
        months_ahead: количество месяцев для превью (default: 6)
    
    Ответ:
        { ok, today, first_run, runs[] }
    """
    frequency_choice = (request.GET.get("frequency_choice") or "").strip().lower()
    valid_frequencies = {"daily", "weekly", "monthly", "custom"}

    if frequency_choice not in valid_frequencies:
        return JsonResponse({"ok": False, "error": "Неверное значение frequency_choice"}, status=400)

    # Создание временного объекта PlannedOrder
    planned_order = PlannedOrder(is_active=True)

    interval_value_raw = (request.GET.get("interval_value") or "").strip()
    interval_unit_raw = (request.GET.get("interval_unit") or "").strip()

    if interval_value_raw:
        try:
            planned_order.interval_value = int(interval_value_raw)
        except ValueError:
            return JsonResponse({"ok": False, "error": "interval_value должен быть целым числом"}, status=400)
    else:
        planned_order.interval_value = 1

    planned_order.interval_unit = interval_unit_raw or IntervalUnit.WEEK

    # Применение правил режимов
    if frequency_choice == "daily":
        first_run_date_str = (request.GET.get("first_run_date") or "").strip()
        if not first_run_date_str:
            return JsonResponse({"ok": False, "error": "Необходимо указать first_run_date"}, status=400)
        try:
            planned_order.first_run_date = datetime.strptime(first_run_date_str, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"ok": False, "error": "Неверный формат first_run_date"}, status=400)
        planned_order.interval_unit = IntervalUnit.DAY
        planned_order.interval_value = 1

    elif frequency_choice == "weekly":
        weekday_str = (request.GET.get("weekday") or "").strip()
        if weekday_str == "":
            return JsonResponse({"ok": False, "error": "Необходимо указать weekday"}, status=400)
        try:
            planned_order.weekday = int(weekday_str)
        except ValueError:
            return JsonResponse({"ok": False, "error": "weekday должен быть целым числом"}, status=400)
        if not (0 <= planned_order.weekday <= 6):
            return JsonResponse({"ok": False, "error": "weekday должен быть в диапазоне 0-6"}, status=400)
        planned_order.interval_unit = IntervalUnit.WEEK
        planned_order.interval_value = 1

    elif frequency_choice == "monthly":
        day_of_month_str = (request.GET.get("day_of_month") or "").strip()
        if day_of_month_str == "":
            return JsonResponse({"ok": False, "error": "Необходимо указать day_of_month"}, status=400)
        try:
            planned_order.day_of_month = int(day_of_month_str)
        except ValueError:
            return JsonResponse({"ok": False, "error": "day_of_month должен быть целым числом"}, status=400)
        if not (1 <= planned_order.day_of_month <= 31):
            return JsonResponse({"ok": False, "error": "day_of_month должен быть в диапазоне 1-31"}, status=400)
        planned_order.interval_unit = IntervalUnit.MONTH
        planned_order.interval_value = 1

    # Расчет дат
    months_ahead = int(request.GET.get("months_ahead", 6))

    try:
        first_run, runs = planned_order.preview_runs(months_ahead=months_ahead)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)

    # Форматирование
    def fmt_dt(dt):
        return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M:%S") if dt else ""
    
    first_run_str = fmt_dt(first_run)
    runs_str = [fmt_dt(r) for r in runs]

    return JsonResponse({
        "ok": True,
        "today": timezone.localdate().isoformat(),
        "first_run": first_run_str,
        "runs": runs_str,
    })
