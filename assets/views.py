"""
assets/views.py

Рефакторинг с использованием базовых классов из core.
"""

import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from core.views import BaseListView, BaseDetailView, BaseCreateView, BaseUpdateView, BaseDeleteView
from core.audit import build_change_reason
from .models import Workstation, WorkstationStatus, WorkstationCategory, WorkstationGlobalState
from .forms import WorkstationForm
from locations.models import Location
from hr.models import HumanResource


# =============================================================================
# LIST VIEW
# =============================================================================

class WorkstationListView(BaseListView):
    """Список оборудования с фильтрацией."""

    model = Workstation
    template_name = "assets/ws_list.html"
    context_object_name = "workstations"
    paginate_by = 20
    ordering = ["name"]

    search_fields = ['name', 'type_name', 'model', 'manufacturer', 'serial_number', 'inventory_number']
    select_related = ['location', 'responsible']

    def get_queryset(self):
        """Фильтрация queryset."""
        queryset = super().get_queryset()
        queryset = self.apply_filters(queryset)

        sort_by = self.request.GET.get('sort', 'name')
        order = self.request.GET.get('order', 'asc')

        if sort_by in ['name', 'category', 'status', 'location']:
            if order == 'desc':
                sort_by = f'-{sort_by}'
            queryset = queryset.order_by(sort_by)

        return queryset

    def apply_filters(self, queryset):
        """Применение фильтров из GET-параметров."""
        filters = Q()

        category = self.request.GET.get("category")
        if category:
            filters &= Q(category=category)

        status = self.request.GET.get("status")
        if status:
            filters &= Q(status=status)

        global_state = self.request.GET.get("global_state")
        if global_state:
            filters &= Q(global_state=global_state)

        location = self.request.GET.get("location")
        if location:
            filters &= Q(location_id=location)

        responsible = self.request.GET.get("responsible")
        if responsible:
            filters &= Q(responsible_id=responsible)

        warranty = self.request.GET.get("warranty")
        if warranty == 'active':
            filters &= Q(warranty_until__gte=timezone.now().date())
        elif warranty == 'expired':
            filters &= Q(warranty_until__lt=timezone.now().date())

        return queryset.filter(filters)

    def get_context_data(self, **kwargs):
        """Добавление контекста."""
        context = super().get_context_data(**kwargs)

        context['categories'] = WorkstationCategory.choices
        context['statuses'] = WorkstationStatus.choices
        context['global_states'] = WorkstationGlobalState.choices
        context['locations'] = Location.objects.all().order_by('name')
        context['responsibles'] = HumanResource.objects.filter(is_active=True).order_by('name')

        context["filter_params"] = {
            "q": self.request.GET.get("q", ""),
            "category": self.request.GET.get("category", ""),
            "status": self.request.GET.get("status", ""),
            "global_state": self.request.GET.get("global_state", ""),
            "location": self.request.GET.get("location", ""),
            "responsible": self.request.GET.get("responsible", ""),
            "warranty": self.request.GET.get("warranty", ""),
            "sort": self.request.GET.get("sort", "name"),
            "order": self.request.GET.get("order", "asc"),
        }

        context["stats"] = {
            "total": Workstation.objects.count(),
            "active": Workstation.objects.filter(global_state=WorkstationGlobalState.ACTIVE).count(),
            "inactive": Workstation.objects.filter(global_state=WorkstationGlobalState.ARCHIVED).count(),
            "under_warranty": Workstation.objects.filter(warranty_until__gte=timezone.now().date()).count(),
        }

        return context


# =============================================================================
# DETAIL VIEW
# =============================================================================

class WorkstationDetailView(BaseDetailView):
    """Детальная информация об оборудовании."""

    model = Workstation
    template_name = "assets/ws_detail.html"
    context_object_name = "workstation"
    select_related = ['location', 'responsible', 'created_by']

    def get_context_data(self, **kwargs):
        """Добавление истории изменений."""
        context = super().get_context_data(**kwargs)

        if hasattr(self.object, 'history'):
            context['history'] = self.object.history.all()[:10]

        context['statuses'] = WorkstationStatus.choices
        context['categories'] = WorkstationCategory.choices
        context['global_states'] = WorkstationGlobalState.choices

        return context


# =============================================================================
# CREATE VIEW
# =============================================================================

class WorkstationCreateView(PermissionRequiredMixin, BaseCreateView):
    """Создание нового оборудования."""

    model = Workstation
    form_class = WorkstationForm
    template_name = "assets/ws_form.html"
    permission_required = ['assets.add_workstation']
    success_message = _('Оборудование "{object}" успешно создано')
    audit_action = "создание оборудования"

    def form_valid(self, form):
        """Добавляем создателя."""
        form.instance.created_by = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('assets:asset_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create'] = True
        context['categories'] = WorkstationCategory.choices
        context['statuses'] = WorkstationStatus.choices
        context['global_states'] = WorkstationGlobalState.choices
        return context


# =============================================================================
# UPDATE VIEW
# =============================================================================

class WorkstationUpdateView(PermissionRequiredMixin, BaseUpdateView):
    """Редактирование оборудования."""

    model = Workstation
    form_class = WorkstationForm
    template_name = "assets/ws_form.html"
    permission_required = ['assets.change_workstation']
    success_message = _('Изменения в оборудовании "{object}" сохранены')
    audit_action = "редактирование оборудования"

    def get_success_url(self):
        return reverse_lazy('assets:asset_detail', kwargs={'pk': self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create'] = False
        context['categories'] = WorkstationCategory.choices
        context['statuses'] = WorkstationStatus.choices
        context['global_states'] = WorkstationGlobalState.choices
        return context


# =============================================================================
# DELETE VIEW
# =============================================================================

class WorkstationDeleteView(PermissionRequiredMixin, BaseDeleteView):
    """Удаление оборудования."""

    model = Workstation
    permission_required = ['assets.delete_workstation']
    audit_action = "удаление оборудования"
    success_url = reverse_lazy('assets:asset_list')


# =============================================================================
# AJAX VIEWS
# =============================================================================

@require_GET
@login_required
@permission_required('assets.view_workstation', raise_exception=True)
def ajax_get_workstation_status(request):
    """Получение текущего статуса оборудования."""
    ws_id = request.GET.get("id")

    if not ws_id:
        return JsonResponse({"ok": False, "error": _("Не указан ID оборудования")}, status=400)

    try:
        ws = Workstation.objects.get(pk=ws_id)
        return JsonResponse({
            "ok": True,
            "current": ws.status,
            "current_display": ws.get_status_display(),
            "choices": dict(WorkstationStatus.choices),
            "can_change": request.user.has_perm('assets.change_workstation'),
        })
    except Workstation.DoesNotExist:
        return JsonResponse({"ok": False, "error": _("Оборудование не найдено")}, status=404)


@require_POST
@login_required
@permission_required('assets.change_workstation', raise_exception=True)
def ajax_update_workstation_status(request):
    """Обновление статуса оборудования."""
    ws_id = request.POST.get("id")
    status = request.POST.get("status")

    if not ws_id or not status:
        return JsonResponse({"ok": False, "error": _("Не указаны обязательные параметры")}, status=400)

    try:
        ws = Workstation.objects.get(pk=ws_id)

        valid_statuses = {choice[0] for choice in WorkstationStatus.choices}
        if status not in valid_statuses:
            return JsonResponse({"ok": False, "error": _("Недопустимый статус")}, status=400)

        old_status = ws.status
        old_status_display = ws.get_status_display()

        ws.status = status
        ws._history_user = request.user
        ws._change_reason = build_change_reason(f"смена статуса с {old_status_display} на {ws.get_status_display()}")
        ws.save(update_fields=["status"])

        return JsonResponse({
            "ok": True,
            "new_status": status,
            "new_status_display": ws.get_status_display(),
            "old_status": old_status,
            "old_status_display": old_status_display,
        })
    except Workstation.DoesNotExist:
        return JsonResponse({"ok": False, "error": _("Оборудование не найдено")}, status=404)


@require_GET
@login_required
@permission_required('assets.view_workstation', raise_exception=True)
def ajax_get_workstation_info(request):
    """Получение краткой информации об оборудовании."""
    ws_id = request.GET.get("id")

    if not ws_id:
        return JsonResponse({"ok": False, "error": _("Не указан ID оборудования")}, status=400)

    try:
        ws = Workstation.objects.select_related('location', 'responsible').get(pk=ws_id)
        return JsonResponse({
            "ok": True,
            "id": ws.id,
            "name": ws.name,
            "type_name": ws.type_name,
            "category": ws.get_category_display(),
            "status": ws.get_status_display(),
            "location": str(ws.location),
            "responsible": str(ws.responsible) if ws.responsible else None,
            "photo_url": ws.photo.url if ws.photo else None,
            "warranty_until": ws.warranty_until.isoformat() if ws.warranty_until else None,
            "is_under_warranty": ws.is_under_warranty,
            "age": ws.age_in_years,
        })
    except Workstation.DoesNotExist:
        return JsonResponse({"ok": False, "error": _("Оборудование не найдено")}, status=404)

@require_GET
@login_required
@permission_required('assets.view_workstation', raise_exception=True)
def ajax_type_name_autocomplete(request):
    """Автодополнение для типов оборудования (TomSelect)."""
    q = request.GET.get("q", "").strip()
    load_all = request.GET.get("load_all", "")

    qs = Workstation.objects.exclude(type_name="").exclude(type_name__isnull=True)

    if load_all == "true" or not q:
        # Загружаем все уникальные типы
        types = (
            qs.values_list("type_name", flat=True)
            .distinct()
            .order_by("type_name")[:100]
        )
    else:
        # Фильтруем по запросу
        qs = qs.filter(type_name__icontains=q)
        types = (
            qs.values_list("type_name", flat=True)
            .distinct()
            .order_by("type_name")[:20]
        )

    return JsonResponse({
        "results": [{"value": t, "text": t} for t in types]
    })


# =============================================================================
# EXPORT
# =============================================================================

@require_GET
@login_required
@permission_required('assets.view_workstation', raise_exception=True)
def export_workstations_csv(request):
    """Экспорт оборудования в CSV."""
    queryset = Workstation.objects.all().select_related('location', 'responsible')

    q = request.GET.get("q")
    if q:
        queryset = queryset.filter(Q(name__icontains=q) | Q(type_name__icontains=q) | Q(model__icontains=q))

    category = request.GET.get("category")
    if category:
        queryset = queryset.filter(category=category)

    status = request.GET.get("status")
    if status:
        queryset = queryset.filter(status=status)

    location = request.GET.get("location")
    if location:
        queryset = queryset.filter(location_id=location)

    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="workstations_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response, delimiter=';')
    writer.writerow([_("Название"), _("Тип"), _("Категория"), _("Производитель"), _("Модель"), _("Серийный номер"), _("Инвентарный номер"), _("Статус"), _("Глобальное состояние"), _("Локация"), _("Ответственный"), _("Дата ввода"), _("Гарантия до"), _("На гарантии"), _("Возраст (лет)"), _("Описание")])

    for ws in queryset:
        writer.writerow([
            ws.name,
            ws.type_name,
            ws.get_category_display(),
            ws.manufacturer,
            ws.model,
            ws.serial_number,
            ws.inventory_number,
            ws.get_status_display(),
            ws.get_global_state_display(),
            str(ws.location),
            str(ws.responsible) if ws.responsible else "",
            ws.commissioning_date.isoformat() if ws.commissioning_date else "",
            ws.warranty_until.isoformat() if ws.warranty_until else "",
            _("Да") if ws.is_under_warranty else _("Нет"),
            ws.age_in_years or "",
            ws.description[:100] + "..." if len(ws.description) > 100 else ws.description,
        ])

    return response
