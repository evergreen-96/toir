from __future__ import annotations

from datetime import datetime, time, timedelta, date
import calendar
from typing import Any

from dateutil.relativedelta import relativedelta
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.db.models.functions import TruncDate
from django.http import JsonResponse, HttpRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.contrib import messages
from django.views import View
from django.views.decorators.http import require_POST, require_GET
from django.views.generic import ListView, DetailView

from assets.models import Workstation, WorkstationStatus, WorkstationGlobalState
from core.audit import build_change_reason
from hr.models import HumanResource
from inventory.models import Material
from locations.models import Location
from maintenance.forms import WorkOrderMaterialFormSet, WorkOrderForm, PlannedOrderForm
from maintenance.models import (
    WorkOrder, PlannedOrder, WorkOrderStatus, WorkCategory,
    Priority, IntervalUnit, WorkOrderMaterial, WorkOrderAttachment, File
)

# ============================================================================
# УТИЛИТЫ
# ============================================================================

RUN_TIME = time(0, 0, 1)  # Плановые работы всегда в 00:00:01


def _last_day_of_month(y: int, m: int) -> int:
    """Возвращает последний день месяца."""
    return calendar.monthrange(y, m)[1]


def _clamp_dom(y: int, m: int, dom: int) -> int:
    """Если dom > числа дней в месяце — возвращает последний день месяца."""
    return min(dom, _last_day_of_month(y, m))


def _fmt_local(dt: datetime) -> str:
    """aware dt -> 'YYYY-MM-DD HH:MM:SS' (local tz)."""
    return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M:%S")


def _get_work_order_counts(**filters) -> int:
    """Утилита для подсчета рабочих задач с фильтрами."""
    return WorkOrder.objects.filter(**filters).count()


# ============================================================================
# ГЛАВНАЯ СТРАНИЦА (DASHBOARD)
# ============================================================================

def home(request: HttpRequest):
    """Главная страница системы технического обслуживания."""
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    # =====================
    # KPI: сегодня + дельта
    # =====================
    stats_today = {
        "new": _get_work_order_counts(
            status=WorkOrderStatus.NEW,
            created_at__date=today
        ),
        "in_progress": _get_work_order_counts(
            status=WorkOrderStatus.IN_PROGRESS
        ),
        "done": _get_work_order_counts(
            status=WorkOrderStatus.DONE,
            date_finish=today
        ),
        "failed": _get_work_order_counts(
            status=WorkOrderStatus.FAILED,
            created_at__date=today
        ),
    }

    stats_yesterday = {
        "new": _get_work_order_counts(
            status=WorkOrderStatus.NEW,
            created_at__date=yesterday
        ),
        "done": _get_work_order_counts(
            status=WorkOrderStatus.DONE,
            date_finish=yesterday
        ),
    }

    stats = {
        **stats_today,
        "delta_new": stats_today["new"] - stats_yesterday["new"],
        "delta_done": stats_today["done"] - stats_yesterday["done"],
    }

    # =====================
    # ДОСТУПНОСТЬ ОБОРУДОВАНИЯ
    # =====================
    workstations = Workstation.objects.filter(
        global_state=WorkstationGlobalState.ACTIVE
    )

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

    # =====================
    # ВЫПОЛНЕНО СЕГОДНЯ
    # =====================
    done_today = WorkOrder.objects.filter(
        status=WorkOrderStatus.DONE,
        date_finish=today
    )

    done_stats = {
        "pm": done_today.filter(category=WorkCategory.PM).count(),
        "emergency": done_today.filter(category=WorkCategory.EMERGENCY).count(),
    }

    # =====================
    # ВЫПОЛНЕНО ПО ОТВЕТСТВЕННЫМ
    # =====================
    done_by_people = (
        done_today
        .values("responsible__name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    # =====================
    # ЗАЯВКИ ПО КАТЕГОРИЯМ (СЕГОДНЯ)
    # =====================
    orders_by_category = (
        WorkOrder.objects
        .filter(created_at__date=today)
        .values("category")
        .annotate(cnt=Count("id"))
    )

    # =====================
    # ЗАЯВКИ ЗА 7 ДНЕЙ (ГРАФИК)
    # =====================
    orders_7d = (
        WorkOrder.objects
        .filter(created_at__date__gte=today - timedelta(days=6))
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(cnt=Count("id"))
        .order_by("day")
    )

    # =====================
    # БЛИЖАЙШИЕ ПЛАНОВЫЕ РАБОТЫ
    # =====================
    upcoming = (
        PlannedOrder.objects
        .filter(
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


# ============================================================================
# РАБОЧИЕ ЗАДАЧИ (WORK ORDERS)
# ============================================================================

class WorkOrderListView(ListView):
    """Список рабочих задач."""

    model = WorkOrder
    template_name = "maintenance/wo_list.html"
    paginate_by = 20
    ordering = ["-id"]

    def get_queryset(self):
        """Возвращает отфильтрованный queryset рабочих задач."""
        qs = (
            super()
            .get_queryset()
            .select_related("responsible", "workstation", "location")
            .order_by('-id')
        )

        # Фильтрация по параметрам GET
        filters = Q()

        query = self.request.GET.get("q", "").strip()
        if query:
            filters &= (Q(name__icontains=query) | Q(description__icontains=query))

        status = self.request.GET.get("status", "")
        if status:
            filters &= Q(status=status)

        priority = self.request.GET.get("priority", "")
        if priority:
            filters &= Q(priority=priority)

        category = self.request.GET.get("category", "")
        if category:
            filters &= Q(category=category)

        return qs.filter(filters)

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Добавляет контекстные данные для фильтров."""
        context = super().get_context_data(**kwargs)

        context.update({
            "q": self.request.GET.get("q", ""),
            "status_choices": WorkOrderStatus.choices,
            "priority_choices": Priority.choices,
            "category_choices": WorkCategory.choices,
            "current": {
                "status": self.request.GET.get("status", ""),
                "priority": self.request.GET.get("priority", ""),
                "category": self.request.GET.get("category", ""),
            }
        })

        return context


class WorkOrderDetailView(DetailView):
    """Детальная страница рабочей задачи."""

    model = WorkOrder
    template_name = "maintenance/wo_detail.html"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Добавляет дополнительные контекстные данные."""
        context = super().get_context_data(**kwargs)
        work_order = self.object

        context.update({
            "allowed_transitions": work_order.get_allowed_transitions(),
            "attachments": work_order.attachments.select_related("file"),
        })

        if work_order.workstation:
            context["workstation_statuses"] = (
                work_order.workstation._meta
                .get_field("status")
                .choices
            )

        return context


def workorder_update(request: HttpRequest, pk: int):
    """Редактирование существующей рабочей задачи."""
    work_order = get_object_or_404(WorkOrder, pk=pk)

    if request.method == "POST":
        form = WorkOrderForm(request.POST, request.FILES, instance=work_order)
        formset = WorkOrderMaterialFormSet(request.POST, instance=work_order)

        if form.is_valid() and formset.is_valid():
            # Сохранение рабочей задачи
            work_order = form.save(commit=False)
            work_order._history_user = request.user
            work_order._change_reason = build_change_reason(
                "редактирование задачи обслуживания"
            )
            work_order.save()

            # Обработка файлов
            _handle_work_order_files(request, work_order)

            # Сохранение материалов
            formset.instance = work_order
            formset.save()

            messages.success(request, "Изменения сохранены.")
            return redirect("maintenance:wo_detail", pk=work_order.pk)
    else:
        form = WorkOrderForm(instance=work_order)
        formset = WorkOrderMaterialFormSet(instance=work_order)

    # Получение доступных файлов
    attached_file_ids = work_order.attachments.values_list("file_id", flat=True)
    all_files = (
        File.objects
        .exclude(id__in=attached_file_ids)
        .order_by("-uploaded_at")
    )

    return render(
        request,
        "maintenance/wo_form.html",
        {
            "form": form,
            "formset": formset,
            "create": False,
            "wo": work_order,
            "all_files": all_files,
        },
    )


def workorder_create(request: HttpRequest):
    """Создание новой рабочей задачи."""
    if request.method == "POST":
        form = WorkOrderForm(request.POST, request.FILES)
        formset = WorkOrderMaterialFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            # Создание рабочей задачи
            work_order = form.save(commit=False)

            # Автоматическое заполнение локации из оборудования
            if work_order.workstation and not work_order.location:
                work_order.location = work_order.workstation.location

            # Аудит - только для аутентифицированных пользователей
            if request.user.is_authenticated:
                work_order._history_user = request.user
            work_order._change_reason = build_change_reason(
                "создание задачи обслуживания"
            )
            work_order.save()

            # Обработка файлов
            _handle_work_order_files(request, work_order)

            # Сохранение материалов
            formset.instance = work_order
            formset.save()

            messages.success(request, "Задача создана.")
            return redirect("maintenance:wo_detail", pk=work_order.pk)

        # Обработка ошибок валидации
        messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
    else:
        form = WorkOrderForm()
        formset = WorkOrderMaterialFormSet()

    # Получение всех файлов для библиотеки
    all_files = File.objects.order_by("-uploaded_at")

    return render(
        request,
        "maintenance/wo_form.html",
        {
            "form": form,
            "formset": formset,
            "create": True,
            "all_files": all_files,
        },
    )


class WorkOrderDeleteView(View):
    """Удаление рабочей задачи."""

    def post(self, request: HttpRequest, pk: int):
        """Обработка POST-запроса на удаление."""
        work_order = get_object_or_404(WorkOrder, pk=pk)

        try:
            # Удаляем связи с файлами
            work_order.attachments.all().delete()

            # Аудит и удаление - только для аутентифицированных пользователей
            if request.user.is_authenticated:
                work_order._history_user = request.user
            work_order._change_reason = build_change_reason(
                "удаление задачи обслуживания"
            )
            work_order.delete()

            return JsonResponse({"ok": True})

        except ProtectedError as e:
            return JsonResponse({
                "ok": False,
                "error": "Нельзя удалить: есть связанные объекты",
                "related": [str(obj) for obj in e.protected_objects],
            }, status=400)


@require_POST
def wo_set_status(request: HttpRequest, pk: int, status: str):
    """Изменение статуса рабочей задачи."""
    work_order = get_object_or_404(WorkOrder, pk=pk)

    try:
        # Аудит и изменение статуса - только для аутентифицированных пользователей
        if request.user.is_authenticated:
            work_order._history_user = request.user
        work_order._change_reason = build_change_reason(
            f"смена статуса задачи → {status}"
        )
        work_order.set_status(status)

        messages.success(
            request,
            f"Статус изменён на «{work_order.get_status_display()}»."
        )
    except ValueError:
        messages.error(request, "Недопустимый переход статуса.")

    return redirect("maintenance:wo_detail", pk=pk)


# ============================================================================
# УТИЛИТЫ ДЛЯ РАБОЧИХ ЗАДАЧ
# ============================================================================

def _handle_work_order_files(request: HttpRequest, work_order: WorkOrder) -> None:
    """Обработка файлов для рабочей задачи."""

    # Существующие файлы из библиотеки
    existing_file_ids = [
        int(fid) for fid in request.POST.getlist("existing_files") if fid.isdigit()
    ]

    # Удаляем старые связи, если не выбраны
    attachments_qs = WorkOrderAttachment.objects.filter(work_order=work_order)

    if existing_file_ids:
        attachments_qs.exclude(file_id__in=existing_file_ids).delete()
    else:
        attachments_qs.delete()

    # Создаем связи с выбранными файлами
    for file_id in existing_file_ids:
        WorkOrderAttachment.objects.get_or_create(
            work_order=work_order,
            file_id=file_id,
        )

    # Новые загруженные файлы
    for uploaded_file in request.FILES.getlist("files"):
        file_obj = File(file=uploaded_file)
        file_obj.save()

        WorkOrderAttachment.objects.create(
            work_order=work_order,
            file=file_obj,
        )


def get_workstations_by_location(request: HttpRequest) -> JsonResponse:
    """AJAX-запрос для получения оборудования по локации."""
    location_id = request.GET.get("location_id", "").strip()

    if not location_id:
        return JsonResponse({"ok": True, "items": []})

    try:
        workstations = Workstation.objects.filter(
            location_id=location_id
        ).values("id", "name")

        items = [{"id": w["id"], "text": w["name"]} for w in workstations]
        return JsonResponse({"ok": True, "items": items})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


# ============================================================================
# ПЛАНОВЫЕ РАБОТЫ (PLANNED ORDERS)
# ============================================================================

class PlannedOrderListView(ListView):
    """Список плановых работ."""

    model = PlannedOrder
    template_name = "maintenance/plan_list.html"
    ordering = ["next_run"]
    paginate_by = 50

    def get_queryset(self):
        """Возвращает queryset с предзагруженными связями."""
        return (
            super()
            .get_queryset()
            .select_related("workstation", "location", "responsible_default")
        )


def planned_order_create(request: HttpRequest):
    """Создание новой плановой работы."""
    if request.method == "POST":
        form = PlannedOrderForm(request.POST)

        if not form.has_changed():
            messages.warning(
                request,
                "Форма пуста. Заполните основные параметры плана."
            )
        elif form.is_valid():
            planned_order = form.save(commit=False)
            planned_order._history_user = request.user
            planned_order._change_reason = build_change_reason(
                "создание плановых работ"
            )
            planned_order.save()

            messages.success(request, "План создан.")

            # Обработка "Сохранить и добавить еще"
            save_and_add = request.POST.get('save_and_add')
            if save_and_add:
                return redirect('maintenance:plan_new')
            else:
                return redirect("maintenance:plan_list")
    else:
        form = PlannedOrderForm()

    # Получение ВСЕХ данных для предзагрузки
    all_locations = list(Location.objects.all().order_by('name')[:100])
    all_responsibles = list(HumanResource.objects.filter(is_active=True)
                            .order_by('name')[:100])
    all_workstations = list()

    return render(
        request,
        "maintenance/plan_form.html",
        {
            "form": form,
            "create": True,
            "all_locations": all_locations,  # ВСЕ локации для select
            "all_responsibles": all_responsibles,  # ВСЕ ответственные
            "all_workstations": all_workstations,  # ВСЕ оборудование
            # Для фильтрации оборудования по локации на клиенте
            "location_workstations": {
                loc.id: list(Workstation.objects.filter(location=loc)
                             .order_by('name')
                             .values('id', 'name'))
                for loc in all_locations[:20]  # Ограничим для производительности
            }
        },
    )


def planned_order_update(request: HttpRequest, pk: int):
    """Редактирование существующей плановой работы."""
    planned_order = get_object_or_404(PlannedOrder, pk=pk)

    if request.method == "POST":
        form = PlannedOrderForm(request.POST, instance=planned_order)

        if not form.has_changed():
            messages.warning(request, "Нет изменений для сохранения.")
        elif form.is_valid():
            planned_order = form.save(commit=False)
            planned_order._history_user = request.user
            planned_order._change_reason = build_change_reason(
                "редактирование плановых работ"
            )
            planned_order.save()

            messages.success(request, "План сохранён.")
            return redirect("maintenance:plan_list")
    else:
        form = PlannedOrderForm(instance=planned_order)

    # Получение ВСЕХ данных для предзагрузки
    all_locations = list(Location.objects.all().order_by('name')[:100])
    all_responsibles = list(HumanResource.objects.filter(is_active=True)
                            .order_by('name')[:100])
    all_workstations = list(Workstation.objects.all()
                            .order_by('name')[:100])

    return render(
        request,
        "maintenance/plan_form.html",
        {
            "form": form,
            "create": False,
            "object": planned_order,
            "all_locations": all_locations,
            "all_responsibles": all_responsibles,
            "all_workstations": all_workstations,
            "location_workstations": {
                loc.id: list(Workstation.objects.filter(location=loc)
                             .order_by('name')
                             .values('id', 'name'))
                for loc in all_locations[:20]
            }
        },
    )


class PlannedOrderDeleteView(View):
    """Удаление плановой работы."""

    def post(self, request: HttpRequest, pk: int):
        """Обработка POST-запроса на удаление."""
        planned_order = get_object_or_404(PlannedOrder, pk=pk)

        try:
            # Аудит и удаление
            planned_order._history_user = request.user
            planned_order._change_reason = build_change_reason(
                "удаление плановых работ"
            )
            planned_order.delete()

            return JsonResponse({"ok": True})

        except ProtectedError as e:
            return JsonResponse({
                "ok": False,
                "error": "Нельзя удалить: есть связанные объекты",
                "related": [str(obj) for obj in e.protected_objects],
            }, status=400)


def planned_order_run_now(request: HttpRequest, pk: int):
    """
    Создание рабочей задачи из плана и расчет следующего запуска.

    Для месячных интервалов соблюдает правило: всегда выбранное число,
    иначе последний день месяца.
    """
    planned_order = get_object_or_404(PlannedOrder, pk=pk)

    if request.method == "POST":
        # Определение ответственного
        responsible = (
                planned_order.responsible_default or
                HumanResource.objects.first()
        )

        if responsible:
            # Создание рабочей задачи из плана
            work_order = WorkOrder.objects.create(
                name=planned_order.name,
                responsible=responsible,
                workstation=planned_order.workstation,
                location=planned_order.location,
                description=planned_order.description,
                category=planned_order.category or WorkCategory.PM,
                labor_plan_hours=planned_order.labor_plan_hours,
                priority=planned_order.priority or Priority.MED,
                created_from_plan=planned_order,  # Исправлено: createrd → created
            )

            # Аудит создания задачи
            work_order._history_user = request.user
            work_order._change_reason = build_change_reason(
                f"создание задачи из плана #{planned_order.pk}"
            )
            work_order.save()

            # Расчет следующего запуска
            next_run = _calculate_next_planned_run(planned_order)

            # Обновление next_run с аудитом
            planned_order._history_user = request.user
            planned_order._change_reason = build_change_reason(
                "ручной запуск плана (создание задачи)"
            )
            planned_order.next_run = next_run
            planned_order.save(update_fields=["next_run"])

            messages.success(request, "Задача создана из плана.")

    return redirect("maintenance:plan_list")


class PlannedOrderDetailView(DetailView):
    """Детальная страница плановой работы."""

    model = PlannedOrder
    template_name = "maintenance/plan_detail.html"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        """Добавляет связанные рабочие задачи в контекст."""
        context = super().get_context_data(**kwargs)
        planned_order = self.object

        context["work_orders"] = (
            planned_order.work_orders
            .select_related("responsible", "workstation")
            .order_by("-created_at")
        )
        print(context)
        return context


# ============================================================================
# УТИЛИТЫ ДЛЯ ПЛАНОВЫХ РАБОТ
# ============================================================================

def _calculate_next_planned_run(planned_order: PlannedOrder) -> datetime:
    """Расчет даты следующего запуска плановой работы."""
    base = planned_order.next_run or planned_order.compute_initial_next_run()

    # Особый случай для месячных интервалов с указанием дня месяца
    if planned_order.interval_unit == IntervalUnit.MONTH and planned_order.day_of_month:
        dom = int(planned_order.day_of_month)
        base_local = timezone.localtime(base)

        next_month = base_local.date() + relativedelta(months=planned_order.interval_value)
        year2, month2 = next_month.year, next_month.month
        day2 = _clamp_dom(year2, month2, dom)
        next_date = date(year2, month2, day2)

        tz = timezone.get_default_timezone()
        next_run = timezone.make_aware(
            datetime.combine(next_date, RUN_TIME),
            tz
        )
    else:
        # Стандартный расчет интервала
        next_run = planned_order._add_interval(
            base,
            planned_order.interval_value,
            planned_order.interval_unit
        )

        # Фиксация времени для дневных/недельных/месячных интервалов
        if planned_order.interval_unit in {
            IntervalUnit.DAY,
            IntervalUnit.WEEK,
            IntervalUnit.MONTH,
        }:
            next_run_local = timezone.localtime(next_run)
            next_date = next_run_local.date()
            tz = timezone.get_default_timezone()
            next_run = timezone.make_aware(
                datetime.combine(next_date, RUN_TIME),
                tz
            )

        # Обнуление секунд и микросекунд для минутных интервалов
        if planned_order.interval_unit == IntervalUnit.MINUTE:
            next_run = next_run.replace(second=0, microsecond=0)

    return next_run


@require_GET
def planned_order_preview(request: HttpRequest) -> JsonResponse:
    """
    AJAX  preview дат запуска плановой работы.

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
    # Валидация frequency_choice
    frequency_choice = (request.GET.get("frequency_choice") or "").strip().lower()
    valid_frequencies = {"daily", "weekly", "monthly", "custom"}

    if frequency_choice not in valid_frequencies:
        return JsonResponse(
            {"ok": False, "error": "Неверное значение frequency_choice"},
            status=400
        )

    # Создание временного объекта PlannedOrder
    planned_order = PlannedOrder(is_active=True)

    # Обработка интервала для custom режима
    interval_value_raw = (request.GET.get("interval_value") or "").strip()
    interval_unit_raw = (request.GET.get("interval_unit") or "").strip()

    if interval_value_raw:
        try:
            planned_order.interval_value = int(interval_value_raw)
        except ValueError:
            return JsonResponse(
                {"ok": False, "error": "interval_value должен быть целым числом"},
                status=400
            )
    else:
        planned_order.interval_value = 1

    planned_order.interval_unit = interval_unit_raw or IntervalUnit.WEEK

    # Применение правил режимов
    if frequency_choice == "daily":
        first_run_date_str = (request.GET.get("first_run_date") or "").strip()
        if not first_run_date_str:
            return JsonResponse(
                {"ok": False, "error": "Необходимо указать first_run_date"},
                status=400
            )

        try:
            planned_order.first_run_date = datetime.strptime(
                first_run_date_str, "%Y-%m-%d"
            ).date()
        except ValueError:
            return JsonResponse(
                {"ok": False, "error": "Неверный формат first_run_date (ожидается YYYY-MM-DD)"},
                status=400
            )

        planned_order.interval_unit = IntervalUnit.DAY
        planned_order.interval_value = 1

    elif frequency_choice == "weekly":
        weekday_str = (request.GET.get("weekday") or "").strip()
        if weekday_str == "":
            return JsonResponse(
                {"ok": False, "error": "Необходимо указать weekday"},
                status=400
            )

        try:
            planned_order.weekday = int(weekday_str)
        except ValueError:
            return JsonResponse(
                {"ok": False, "error": "weekday должен быть целым числом от 0 до 6"},
                status=400
            )

        if not (0 <= planned_order.weekday <= 6):
            return JsonResponse(
                {"ok": False, "error": "weekday должен быть в диапазоне 0-6"},
                status=400
            )

        planned_order.interval_unit = IntervalUnit.WEEK
        planned_order.interval_value = 1

    elif frequency_choice == "monthly":
        day_of_month_str = (request.GET.get("day_of_month") or "").strip()
        if day_of_month_str == "":
            return JsonResponse(
                {"ok": False, "error": "Необходимо указать day_of_month"},
                status=400
            )

        try:
            planned_order.day_of_month = int(day_of_month_str)
        except ValueError:
            return JsonResponse(
                {"ok": False, "error": "day_of_month должен быть целым числом от 1 до 31"},
                status=400
            )

        if not (1 <= planned_order.day_of_month <= 31):
            return JsonResponse(
                {"ok": False, "error": "day_of_month должен быть в диапазоне 1-31"},
                status=400
            )

        planned_order.interval_unit = IntervalUnit.MONTH
        planned_order.interval_value = 1

    elif frequency_choice == "custom":
        if not interval_value_raw or not interval_unit_raw:
            return JsonResponse(
                {"ok": False, "error": "Для custom режима необходимо указать interval_value и interval_unit"},
                status=400
            )

        if planned_order.interval_value < 1:
            return JsonResponse(
                {"ok": False, "error": "interval_value должен быть ≥ 1"},
                status=400
            )

    # Расчет превью на заданное количество месяцев
    months_ahead_str = (request.GET.get("months_ahead") or "").strip()
    try:
        months_ahead = int(months_ahead_str) if months_ahead_str else 6
    except ValueError:
        months_ahead = 6

    # Защита от слишком больших значений
    months_ahead = max(1, min(months_ahead, 24))

    # Получение дат запуска
    first_run, runs = planned_order.preview_runs(months_ahead=months_ahead)

    return JsonResponse({
        "ok": True,
        "today": timezone.localdate().isoformat(),
        "first_run": _fmt_local(first_run),
        "runs": [_fmt_local(run) for run in runs],
    })

def ajax_material_search(request: HttpRequest) -> JsonResponse:
    """AJAX поиск материалов."""
    query = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)

    try:
        page = int(page)
    except (ValueError, TypeError):
        page = 1

    # Поиск материалов
    materials = Material.objects.filter(is_active=True).order_by('name')

    if query:
        materials = materials.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(description__icontains=query)
        )

    # Пагинация
    paginator = Paginator(materials, 20)
    try:
        page_obj = paginator.page(page)
    except Exception:
        page_obj = paginator.page(1)

    # Формирование результатов
    results = []
    for material in page_obj:
        result = {
            'id': material.id,
            'text': material.name,
            'sku': material.sku or '',
        }

        # Добавление URL изображения если есть
        if hasattr(material, 'image') and material.image:
            result['image_url'] = material.image.url
        elif hasattr(material, 'photo') and material.photo:
            result['image_url'] = material.photo.url
        elif hasattr(material, 'image_url') and material.image_url:
            result['image_url'] = material.image_url
        else:
            result['image_url'] = ''

        results.append(result)

    return JsonResponse({
        'results': results,
        'pagination': {
            'more': page_obj.has_next()
        }
    })


# ============================================================================
# AJAX ДЛЯ ПЛАНОВЫХ РАБОТ
# ============================================================================

@require_GET
def ajax_locations(request: HttpRequest) -> JsonResponse:
    """AJAX поиск локаций для TomSelect."""
    query = request.GET.get('q', '').strip()

    # Убрали фильтр по is_active, так как такого поля нет в Location
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
def api_workstations(request):
    """
    API endpoint для получения списка оборудования по локации.
    Используется Tom Select для динамической загрузки опций.

    GET параметры:
        location (int): ID локации для фильтрации

    Возвращает:
        JSON список объектов: [{"id": 1, "name": "Станок 1"}, ...]
    """
    location_id = request.GET.get('location')

    if not location_id:
        return JsonResponse([], safe=False)

    try:
        location_id = int(location_id)
    except (TypeError, ValueError):
        return JsonResponse([], safe=False)

    # Получаем оборудование для выбранной локации
    workstations = Workstation.objects.filter(
        location_id=location_id
    ).order_by('name').values('id', 'name')

    return JsonResponse(list(workstations), safe=False)

@require_GET
def ajax_all_job_titles(request: HttpRequest) -> JsonResponse:
    """AJAX получение всех уникальных должностей для автодополнения."""
    job_titles = HumanResource.objects.filter(
        job_title__isnull=False
    ).values_list('job_title', flat=True).distinct().order_by('job_title')

    results = [{"value": title, "text": title} for title in job_titles]

    return JsonResponse({"results": results})