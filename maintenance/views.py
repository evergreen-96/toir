from __future__ import annotations

from datetime import datetime, time, timedelta, date
import calendar

from dateutil.relativedelta import relativedelta

from django import forms
from django.contrib import messages
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST, require_GET
from django.views.generic import ListView, DetailView, DeleteView

from assets.models import Workstation
from hr.models import HumanResource
from .forms import WorkOrderMaterialFormSet, WorkOrderForm

from .models import (
    WorkOrder,
    WorkOrderStatus,
    Priority,
    WorkCategory,
    PlannedOrder,
    IntervalUnit,
    WorkOrderMaterial,
    WorkOrderFile
)

# Плановые работы всегда в 00:00:01
RUN_TIME = time(0, 0, 1)


# =========================
# Helpers
# =========================
def _last_day_of_month(y: int, m: int) -> int:
    return calendar.monthrange(y, m)[1]


def _clamp_dom(y: int, m: int, dom: int) -> int:
    return min(dom, _last_day_of_month(y, m))


def _fmt_local(dt) -> str:
    """aware dt -> 'YYYY-MM-DD HH:MM:SS' (local tz)"""
    return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M:%S")


# =========================
# HOME
# =========================
from django.utils import timezone
from django.db.models import Count

from maintenance.models import (
    WorkOrder, PlannedOrder,
    WorkOrderStatus, WorkCategory
)
from assets.models import (
    Workstation,
    WorkstationStatus,
    WorkstationGlobalState
)


def home(request):
    today = timezone.localdate()

    stats = {
        "total": WorkOrder.objects.exclude(
            status__in=[WorkOrderStatus.DONE, WorkOrderStatus.CANCELED]
        ).count(),

        "new": WorkOrder.objects.filter(
            status=WorkOrderStatus.NEW,
            created_at__date=today
        ).count(),

        "in_progress": WorkOrder.objects.filter(
            status=WorkOrderStatus.IN_PROGRESS
        ).count(),

        "done": WorkOrder.objects.filter(
            status=WorkOrderStatus.DONE,
            date_finish=today
        ).count(),

        "failed": WorkOrder.objects.filter(
            status=WorkOrderStatus.FAILED
        ).count(),
    }

    # ---------- Доступность оборудования ----------
    ws_qs = Workstation.objects.filter(
        global_state=WorkstationGlobalState.ACTIVE
    )

    total_ws = ws_qs.count()
    in_prod = ws_qs.filter(status=WorkstationStatus.PROD).count()
    emergency = ws_qs.filter(status=WorkstationStatus.PROBLEM).count()
    not_working = ws_qs.filter(
        status__in=[WorkstationStatus.MAINT, WorkstationStatus.SETUP]
    ).count()

    availability = {
        "pct": round((in_prod / total_ws * 100), 1) if total_ws else 0,
        "in_prod": in_prod,
        "emergency": emergency,
        "not_working": not_working,
    }

    # ---------- Выполнено сегодня ----------
    done_today = WorkOrder.objects.filter(
        status=WorkOrderStatus.DONE,
        date_finish=today
    )

    done_stats = {
        "pm": done_today.filter(category=WorkCategory.PM).count(),
        "emergency": done_today.filter(category=WorkCategory.EMERGENCY).count(),
    }

    # ---------- Выполнено по людям ----------
    done_by_people = (
        done_today
        .values("responsible_id", "responsible__name")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")
    )

    # ---------- Заявки по категориям ----------
    orders_by_category = (
        WorkOrder.objects
        .filter(created_at__date=today)
        .values("category")
        .annotate(cnt=Count("id"))
    )

    # ---------- Ближайшие планы ----------
    upcoming = (
        PlannedOrder.objects
        .filter(
            is_active=True,
            next_run__isnull=False,
            next_run__gte=timezone.now()
        )
        .order_by("next_run")[:10]
    )

    return render(request, "maintenance/home.html", {
        "stats": stats,
        "availability": availability,
        "done_stats": done_stats,
        "done_by_people": done_by_people,
        "orders_by_category": orders_by_category,
        "upcoming": upcoming,
    })


# =========================
# WORK ORDERS
# =========================
class WorkOrderListView(ListView):
    model = WorkOrder
    template_name = "maintenance/wo_list.html"
    paginate_by = 20
    ordering = ["-id"]

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("responsible", "workstation", "location")
        ).order_by('-id')

        q = self.request.GET.get("q", "")
        status = self.request.GET.get("status", "")
        prio = self.request.GET.get("priority", "")
        cat = self.request.GET.get("category", "")

        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(description__icontains=q)
            )
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

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["allowed_transitions"] = self.object.get_allowed_transitions()
        ctx["files"] = self.object.attachments.all()
        return ctx


def workorder_update(request, pk: int):
    from .forms import WorkOrderForm, WorkOrderMaterialFormSet

    wo = get_object_or_404(WorkOrder, pk=pk)

    if request.method == "POST":
        form = WorkOrderForm(request.POST, request.FILES, instance=wo)
        formset = WorkOrderMaterialFormSet(request.POST, instance=wo)
        if form.is_valid() and formset.is_valid():
            wo = form.save()

            # Автоматически устанавливаем location из workstation если не задан
            if wo.workstation and not wo.location:
                wo.location = wo.workstation.location
                wo.save(update_fields=["location"])
            for f in form.cleaned_data.get("files", []):
                WorkOrderFile.objects.create(work_order=wo, file=f)
            # Сохраняем formset
            instances = formset.save(commit=False)
            for instance in instances:
                instance.work_order = wo
                instance.save()

            for obj in formset.deleted_objects:
                obj.delete()

            messages.success(request, "Изменения сохранены.")
            return redirect("maintenance:wo_detail", pk=wo.pk)
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
            print("Form errors:", form.errors)
            print("Formset errors:", formset.errors)
    else:
        form = WorkOrderForm(instance=wo)
        formset = WorkOrderMaterialFormSet(instance=wo)

    return render(
        request,
        "maintenance/wo_form.html",
        {"form": form, "formset": formset, "create": False, "wo": wo},
    )


def workorder_create(request):
    from .forms import WorkOrderForm, WorkOrderMaterialFormSet

    if request.method == "POST":
        form = WorkOrderForm(request.POST, request.FILES)
        formset = WorkOrderMaterialFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            wo = form.save(commit=False)

            if wo.workstation and not wo.location:
                wo.location = wo.workstation.location

            wo.save()

            # 🔑 СОХРАНЕНИЕ ФАЙЛОВ
            for f in form.cleaned_data.get("files", []):
                WorkOrderFile.objects.create(work_order=wo, file=f)

            formset.instance = wo
            formset.save()

            messages.success(request, "Задача создана.")
            return redirect("maintenance:wo_detail", pk=wo.pk)
        else:
            messages.error(request, "Пожалуйста, исправьте ошибки в форме.")
            print("Form errors:", form.errors)
            print("Formset errors:", formset.errors)

    else:
        form = WorkOrderForm()
        formset = WorkOrderMaterialFormSet()

    return render(
        request,
        "maintenance/wo_form.html",
        {
            "form": form,
            "formset": formset,
            "create": True,
        },
    )


class WorkOrderDeleteView(View):
    def post(self, request, pk):
        obj = get_object_or_404(WorkOrder, pk=pk)

        try:
            # удалить файлы физически
            for att in obj.attachments.all():
                att.file.delete(save=False)

            obj.delete()
            return JsonResponse({"ok": True})

        except ProtectedError as e:
            return JsonResponse({
                "ok": False,
                "error": "Нельзя удалить: есть связанные объекты",
                "related": [str(o) for o in e.protected_objects],
            }, status=400)


@require_POST
def wo_set_status(request, pk, status):
    wo = get_object_or_404(WorkOrder, pk=pk)

    try:
        wo.set_status(status)
    except ValueError:
        messages.error(request, "Недопустимый переход статуса.")
        return redirect("maintenance:wo_detail", pk=pk)

    messages.success(
        request,
        f"Статус изменён на «{wo.get_status_display()}»."
    )
    return redirect("maintenance:wo_detail", pk=pk)


def get_workstations_by_location(request):
    location_id = request.GET.get("location_id")

    if not location_id:
        return JsonResponse({"ok": True, "items": []})

    qs = Workstation.objects.filter(location_id=location_id).values("id", "name")
    items = [{"id": w["id"], "text": w["name"]} for w in qs]

    return JsonResponse({"ok": True, "items": items})


# =========================
# PLANNED ORDERS: FORM
# (у тебя сейчас форма лежит в views.py — оставляю так же)
# =========================
class PlannedOrderForm(forms.ModelForm):
    frequency_choice = forms.ChoiceField(
        label="Периодичность работ",
        choices=[
            ("daily", "Ежедневно"),
            ("weekly", "Еженедельно"),
            ("monthly", "Ежемесячно"),
            ("custom", "По заданному интервалу"),
        ],
        widget=forms.RadioSelect,
        required=False,  # важно
    )
    # Переопределяем model-fields, чтобы MinValueValidator модели
    # НЕ падал на None при пустом POST
    interval_value = forms.IntegerField(
        required=False,
        min_value=1,
        widget=forms.HiddenInput(),
    )

    interval_unit = forms.ChoiceField(
        required=False,
        choices=IntervalUnit.choices,
        widget=forms.HiddenInput(),
    )
    WEEKDAYS = [
        (0, "Понедельник"),
        (1, "Вторник"),
        (2, "Среда"),
        (3, "Четверг"),
        (4, "Пятница"),
        (5, "Суббота"),
        (6, "Воскресенье"),
    ]

    first_run_date = forms.DateField(
        label="Дата первого обслуживания",
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    weekday = forms.ChoiceField(
        label="Проводить работы каждый",
        choices=WEEKDAYS,
        required=False,
    )

    day_of_month = forms.IntegerField(
        label="Проводить работы каждое (число месяца)",
        required=False,
        min_value=1,
        max_value=31,
    )

    class Meta:
        model = PlannedOrder
        fields = [
            "frequency_choice",
            "name",
            "description",
            "workstation",
            "location",
            "responsible_default",
            "category",
            "priority",
            "labor_plan_hours",
            "interval_value",
            "interval_unit",
            "first_run_date",
            "weekday",
            "day_of_month",
            "is_active",
            "interval_value",
            "interval_unit",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "interval_value": forms.HiddenInput(),
            "interval_unit": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # === делаем ответственного обязательным ===
        self.fields["responsible_default"].required = True

        self.fields["interval_value"].required = False
        self.fields["interval_unit"].required = False

        if self.instance.pk:
            if self.instance.interval_unit == IntervalUnit.DAY and self.instance.interval_value == 1:
                self.fields["frequency_choice"].initial = "daily"
            elif self.instance.interval_unit == IntervalUnit.WEEK and self.instance.interval_value == 1:
                self.fields["frequency_choice"].initial = "weekly"
            elif self.instance.interval_unit == IntervalUnit.MONTH and self.instance.interval_value == 1:
                self.fields["frequency_choice"].initial = "monthly"
            else:
                self.fields["frequency_choice"].initial = "custom"

    def clean(self):
        cleaned = super().clean()

        # =====================================================
        # Защита от полностью пустой формы
        # =====================================================
        if not self.has_changed():
            raise forms.ValidationError(
                "Форма пуста. Заполните основные параметры плана."
            )

        freq = cleaned.get("frequency_choice")

        if not freq:
            raise forms.ValidationError(
                "Выберите периодичность работ."
            )

        # =====================================================
        # Валидация по режимам
        # =====================================================
        if freq == "daily":
            if not cleaned.get("first_run_date"):
                self.add_error("first_run_date", "Укажите дату первого обслуживания")
            cleaned["interval_unit"] = IntervalUnit.DAY
            cleaned["interval_value"] = 1

        elif freq == "weekly":
            if cleaned.get("weekday") in (None, ""):
                self.add_error("weekday", "Выберите день недели")
            cleaned["interval_unit"] = IntervalUnit.WEEK
            cleaned["interval_value"] = 1

        elif freq == "monthly":
            if not cleaned.get("day_of_month"):
                self.add_error("day_of_month", "Укажите число месяца")
            cleaned["interval_unit"] = IntervalUnit.MONTH
            cleaned["interval_value"] = 1

        elif freq == "custom":
            iv = cleaned.get("interval_value")
            iu = cleaned.get("interval_unit")

            if iv in (None, ""):
                self.add_error("interval_value", "Обязательное поле")
            elif iv < 1:
                self.add_error("interval_value", "Значение должно быть ≥ 1")

            if not iu:
                self.add_error("interval_unit", "Обязательное поле")

        return cleaned

    def save(self, commit=True):
        """
        При создании или изменении расписания пересчитываем next_run,
        чтобы при редактировании план не оставался со старым next_run.
        """
        obj = super().save(commit=False)

        schedule_fields = {
            "frequency_choice",
            "first_run_date",
            "weekday",
            "day_of_month",
            "interval_value",
            "interval_unit",
            "is_active",
        }
        schedule_changed = (not obj.pk) or any(f in self.changed_data for f in schedule_fields)

        if obj.is_active and schedule_changed:
            obj.next_run = obj.compute_initial_next_run()

        if commit:
            obj.save()
            self.save_m2m()
        return obj


# =========================
# PLANNED ORDERS: VIEWS
# =========================
class PlannedOrderListView(ListView):
    model = PlannedOrder
    template_name = "maintenance/plan_list.html"
    ordering = ["next_run"]
    paginate_by = 50


def planned_order_create(request):
    if request.method == "POST":
        form = PlannedOrderForm(request.POST)

        # ===== защита от пустой отправки =====
        if not form.has_changed():
            messages.warning(
                request,
                "Форма пуста. Заполните основные параметры плана."
            )
        elif form.is_valid():
            form.save()
            messages.success(request, "План создан.")
            return redirect("maintenance:plan_list")

    else:
        form = PlannedOrderForm()

    return render(
        request,
        "maintenance/plan_form.html",
        {
            "form": form,
            "create": True,
        },
    )


def planned_order_update(request, pk: int):
    obj = get_object_or_404(PlannedOrder, pk=pk)

    if request.method == "POST":
        form = PlannedOrderForm(request.POST, instance=obj)

        # =====================================================
        # Защита: нет изменений / пустая отправка
        # =====================================================
        if not form.has_changed():
            messages.warning(
                request,
                "Нет изменений для сохранения."
            )

        elif form.is_valid():
            form.save()
            messages.success(request, "План сохранён.")
            return redirect("maintenance:plan_list")

        else:
            # полезно при отладке, можно убрать позже
            print("FORM ERRORS:", form.errors)

    else:
        form = PlannedOrderForm(instance=obj)

    return render(
        request,
        "maintenance/plan_form.html",
        {
            "form": form,
            "create": False,
            "obj": obj,
        },
    )


class PlannedOrderDeleteView(View):
    def post(self, request, pk):
        obj = get_object_or_404(PlannedOrder, pk=pk)

        try:
            obj.delete()
            return JsonResponse({"ok": True})

        except ProtectedError as e:
            return JsonResponse({
                "ok": False,
                "error": "Нельзя удалить: есть связанные объекты",
                "related": [str(o) for o in e.protected_objects],
            }, status=400)


def planned_order_run_now(request, pk: int):
    """
    "Создать сейчас": создаём WorkOrder из плана и двигаем next_run вперёд.
    Для MONTH + day_of_month соблюдаем правило: всегда выбранное число, иначе последний день месяца.
    """
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
                createrd_from_plan=obj
            )

            base = obj.next_run or obj.compute_initial_next_run()

            # Рассчитываем следующий запуск
            if obj.interval_unit == IntervalUnit.MONTH and obj.day_of_month:
                dom = int(obj.day_of_month)
                base_local = timezone.localtime(base)

                nxt_month = base_local.date() + relativedelta(months=obj.interval_value)
                y2, m2 = nxt_month.year, nxt_month.month
                d2 = _clamp_dom(y2, m2, dom)
                nxt_date = date(y2, m2, d2)

                tz = timezone.get_default_timezone()
                nxt = timezone.make_aware(datetime.combine(nxt_date, RUN_TIME), tz)

            else:
                nxt = obj._add_interval(base, obj.interval_value, obj.interval_unit)

                # Для day/week/month — фиксируем 00:00:01 (чтобы не было "дрейфа" по времени)
                if obj.interval_unit in {IntervalUnit.DAY, IntervalUnit.WEEK, IntervalUnit.MONTH}:
                    nxt_local = timezone.localtime(nxt)
                    nxt_date = nxt_local.date()
                    tz = timezone.get_default_timezone()
                    nxt = timezone.make_aware(datetime.combine(nxt_date, RUN_TIME), tz)

                # Для minute — просто убираем микросекунды/секунды (как у тебя было)
                if obj.interval_unit == IntervalUnit.MINUTE:
                    nxt = nxt.replace(second=0, microsecond=0)

            obj.next_run = nxt
            obj.save(update_fields=["next_run"])
            messages.success(request, "Задача создана из плана.")

    return redirect("maintenance:plan_list")


# =========================
# PLANNED ORDERS: PREVIEW ENDPOINT (AJAX)
# =========================
@require_GET
def planned_order_preview(request):
    """
    GET params:
      frequency_choice: daily|weekly|monthly|custom
      first_run_date: YYYY-MM-DD
      weekday: 0..6
      day_of_month: 1..31
      interval_value, interval_unit (for custom)

    Ответ:
      { ok, today, first_run, runs[] }
    """
    freq = (request.GET.get("frequency_choice") or "").strip().lower()
    if freq not in {"daily", "weekly", "monthly", "custom"}:
        return JsonResponse({"ok": False, "error": "bad frequency_choice"}, status=400)

    # interval для custom берём из GET
    interval_value_raw = (request.GET.get("interval_value") or "").strip()
    interval_unit_raw = (request.GET.get("interval_unit") or "").strip()

    # Собираем временный PlannedOrder (без сохранения)
    obj = PlannedOrder(is_active=True)

    # дефолт — чтобы не падать на пустом custom
    if interval_value_raw:
        try:
            obj.interval_value = int(interval_value_raw)
        except ValueError:
            return JsonResponse({"ok": False, "error": "interval_value must be int"}, status=400)
    else:
        obj.interval_value = 1

    if interval_unit_raw:
        obj.interval_unit = interval_unit_raw
    else:
        obj.interval_unit = IntervalUnit.WEEK

    # Применяем правила режимов (как в UI)
    if freq == "daily":
        frd = (request.GET.get("first_run_date") or "").strip()
        if not frd:
            return JsonResponse({"ok": False, "error": "first_run_date required"}, status=400)
        try:
            obj.first_run_date = datetime.strptime(frd, "%Y-%m-%d").date()
        except ValueError:
            return JsonResponse({"ok": False, "error": "first_run_date format YYYY-MM-DD"}, status=400)
        obj.interval_unit = IntervalUnit.DAY
        obj.interval_value = 1

    elif freq == "weekly":
        wd = (request.GET.get("weekday") or "").strip()
        if wd == "":
            return JsonResponse({"ok": False, "error": "weekday required"}, status=400)
        try:
            obj.weekday = int(wd)
        except ValueError:
            return JsonResponse({"ok": False, "error": "weekday must be int 0..6"}, status=400)
        if not (0 <= obj.weekday <= 6):
            return JsonResponse({"ok": False, "error": "weekday must be 0..6"}, status=400)
        obj.interval_unit = IntervalUnit.WEEK
        obj.interval_value = 1

    elif freq == "monthly":
        dom = (request.GET.get("day_of_month") or "").strip()
        if dom == "":
            return JsonResponse({"ok": False, "error": "day_of_month required"}, status=400)
        try:
            obj.day_of_month = int(dom)
        except ValueError:
            return JsonResponse({"ok": False, "error": "day_of_month must be int 1..31"}, status=400)
        if not (1 <= obj.day_of_month <= 31):
            return JsonResponse({"ok": False, "error": "day_of_month must be 1..31"}, status=400)
        obj.interval_unit = IntervalUnit.MONTH
        obj.interval_value = 1

    elif freq == "custom":
        # custom: обязательно и interval_value и interval_unit
        if not interval_value_raw or not interval_unit_raw:
            return JsonResponse({"ok": False, "error": "interval_value and interval_unit required for custom"},
                                status=400)
        if obj.interval_value < 1:
            return JsonResponse({"ok": False, "error": "interval_value must be >= 1"}, status=400)

    # Считаем превью на 2 месяца
    months_ahead_raw = (request.GET.get("months_ahead") or "").strip()
    try:
        months_ahead = int(months_ahead_raw) if months_ahead_raw else 6
    except ValueError:
        months_ahead = 6
    months_ahead = max(1, min(months_ahead, 24))  # защита: 1..24

    first_run, runs = obj.preview_runs(months_ahead=months_ahead)

    return JsonResponse({
        "ok": True,
        "today": timezone.localdate().isoformat(),
        "first_run": _fmt_local(first_run),
        "runs": [_fmt_local(x) for x in runs],
    })


class PlannedOrderDetailView(DetailView):
    model = PlannedOrder
    template_name = "maintenance/plan_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx["work_orders"] = (
            self.object.work_orders
            .select_related("responsible", "workstation")
            .order_by("-created_at")
        )

        return ctx

@require_POST
def workorder_file_delete(request, pk):
    file_obj = get_object_or_404(WorkOrderFile, pk=pk)

    # физически удаляем файл
    file_obj.file.delete(save=False)
    file_obj.delete()

    return JsonResponse({"ok": True})