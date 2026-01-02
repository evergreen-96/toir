from django.db.models import Q
from django.http import JsonResponse, HttpResponseForbidden
from django.views import View
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.generic import ListView, DetailView, DeleteView, CreateView, UpdateView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models.deletion import ProtectedError
from django import forms
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import Workstation, WorkstationStatus, WorkstationCategory, WorkstationGlobalState
from locations.models import Location
from hr.models import HumanResource
from core.audit import build_change_reason


# =======================
# Mixins
# =======================

class WorkstationContextMixin:
    """Миксин для добавления общего контекста"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = WorkstationCategory.choices
        context['statuses'] = WorkstationStatus.choices
        context['global_states'] = WorkstationGlobalState.choices
        return context


class WorkstationPermissionMixin(PermissionRequiredMixin):
    """Миксин для проверки прав доступа к оборудованию"""

    def get_permission_required(self):
        if self.request.method == 'GET':
            return ['assets.view_workstation']
        elif self.request.method == 'POST':
            return ['assets.add_workstation']
        elif self.request.method in ['PUT', 'PATCH']:
            return ['assets.change_workstation']
        elif self.request.method == 'DELETE':
            return ['assets.delete_workstation']
        return []


class WorkstationAuditMixin:
    """Миксин для аудита изменений оборудования"""

    def add_audit_info(self, obj, action):
        """Добавляет информацию для аудита"""
        obj._history_user = self.request.user
        obj._change_reason = build_change_reason(
            f"{action} оборудования"
        )
        return obj


# =======================
# Forms
# =======================

class WorkstationForm(forms.ModelForm):
    """Форма для создания/редактирования оборудования"""

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
        widgets = {
            'commissioning_date': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'warranty_until': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'}
            ),
            'description': forms.Textarea(
                attrs={'rows': 4, 'class': 'form-control'}
            ),
            'photo': forms.FileInput(
                attrs={'class': 'form-control', 'accept': 'image/*'}
            ),
        }
        help_texts = {
            'inventory_number': _('Уникальный инвентарный номер'),
            'serial_number': _('Серийный номер от производителя'),
            'photo': _('Рекомендуемый размер: 800x600px'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Оптимизируем queryset для полей ForeignKey
        self.fields['location'].queryset = Location.objects.all().order_by('name')
        self.fields['responsible'].queryset = HumanResource.objects.filter(
            is_active=True
        ).order_by('name')

        # Добавляем CSS классы
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

        # Делаем поле названия обязательным
        self.fields['name'].required = True
        self.fields['location'].required = True
        self.fields['category'].required = True
        self.fields['global_state'].required = True
        self.fields['status'].required = True

    def clean_inventory_number(self):
        """Проверка уникальности инвентарного номера"""
        inventory_number = self.cleaned_data.get('inventory_number')

        if inventory_number:
            qs = Workstation.objects.filter(inventory_number=inventory_number)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    _('Оборудование с таким инвентарным номером уже существует')
                )

        return inventory_number

    def clean(self):
        """Дополнительная валидация формы"""
        cleaned_data = super().clean()

        # Проверка дат
        commissioning_date = cleaned_data.get('commissioning_date')
        warranty_until = cleaned_data.get('warranty_until')

        if commissioning_date and warranty_until:
            if warranty_until < commissioning_date:
                self.add_error(
                    'warranty_until',
                    _('Дата окончания гарантии не может быть раньше даты ввода в эксплуатацию')
                )

        # Проверка статуса
        global_state = cleaned_data.get('global_state')
        status = cleaned_data.get('status')

        if (global_state == WorkstationGlobalState.ARCHIVED and
                status != WorkstationStatus.DECOMMISSIONED):
            self.add_error(
                'status',
                _('Оборудование в архиве должно иметь статус "Выведено из эксплуатации"')
            )

        return cleaned_data


# =======================
# List View
# =======================

class WorkstationListView(LoginRequiredMixin, WorkstationContextMixin, ListView):
    """Список оборудования с фильтрацией"""

    model = Workstation
    template_name = "assets/ws_list.html"
    paginate_by = 20
    ordering = ["name"]
    context_object_name = "workstations"

    def get_queryset(self):
        """Фильтрация и оптимизация queryset"""
        queryset = super().get_queryset().select_related(
            'location', 'responsible'  # Убираем responsible__user
        )

        # Применяем фильтры
        queryset = self.apply_filters(queryset)

        # Сортировка по умолчанию
        sort_by = self.request.GET.get('sort', 'name')
        order = self.request.GET.get('order', 'asc')

        if sort_by in ['name', 'category', 'status', 'location']:
            if order == 'desc':
                sort_by = f'-{sort_by}'
            queryset = queryset.order_by(sort_by)

        return queryset

    def apply_filters(self, queryset):
        """Применение фильтров из GET-параметров"""
        filters = Q()

        # Поиск по тексту
        q = self.request.GET.get("q")
        if q:
            filters &= Q(
                Q(name__icontains=q) |
                Q(type_name__icontains=q) |
                Q(model__icontains=q) |
                Q(manufacturer__icontains=q) |
                Q(serial_number__icontains=q) |
                Q(inventory_number__icontains=q)
            )

        # Категория
        category = self.request.GET.get("category")
        if category:
            filters &= Q(category=category)

        # Статус
        status = self.request.GET.get("status")
        if status:
            filters &= Q(status=status)

        # Глобальное состояние
        global_state = self.request.GET.get("global_state")
        if global_state:
            filters &= Q(global_state=global_state)

        # Локация
        location = self.request.GET.get("location")
        if location:
            filters &= Q(location_id=location)

        # Ответственный
        responsible = self.request.GET.get("responsible")
        if responsible:
            filters &= Q(responsible_id=responsible)

        # Гарантия
        warranty = self.request.GET.get("warranty")
        if warranty == 'active':
            filters &= Q(warranty_until__gte=timezone.now().date())
        elif warranty == 'expired':
            filters &= Q(warranty_until__lt=timezone.now().date())

        return queryset.filter(filters)

    def get_context_data(self, **kwargs):
        """Добавление дополнительного контекста"""
        context = super().get_context_data(**kwargs)

        # Параметры фильтров
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

        # Данные для фильтров
        context["locations"] = Location.objects.all().order_by('name')
        context["responsibles"] = HumanResource.objects.filter(
            is_active=True
        ).order_by('name')  # Убираем select_related('user')

        # Статистика
        context["stats"] = {
            "total": Workstation.objects.count(),
            "active": Workstation.objects.filter(
                global_state=WorkstationGlobalState.ACTIVE
            ).count(),
            "inactive": Workstation.objects.filter(
                global_state=WorkstationGlobalState.ARCHIVED
            ).count(),
            "under_warranty": Workstation.objects.filter(
                warranty_until__gte=timezone.now().date()
            ).count(),
        }

        return context


# =======================
# Detail View
# =======================

class WorkstationDetailView(LoginRequiredMixin, WorkstationContextMixin, DetailView):
    """Детальная информация об оборудовании"""

    model = Workstation
    template_name = "assets/ws_detail.html"
    context_object_name = "workstation"

    def get_queryset(self):
        """Оптимизация запросов для детального просмотра"""
        # УБИРАЕМ prefetch_related('history') - это вызывает ошибку
        return super().get_queryset().select_related(
            'location', 'responsible', 'created_by'
        )

    def get_context_data(self, **kwargs):
        """Добавление истории изменений"""
        context = super().get_context_data(**kwargs)
        # Получаем историю через запрос, а не через prefetch
        if self.object:
            context['history'] = self.object.history.all()[:10]  # Последние 10 изменений
        return context


# =======================
# Create View
# =======================

class WorkstationCreateView(LoginRequiredMixin, PermissionRequiredMixin,
                            WorkstationContextMixin, WorkstationAuditMixin, CreateView):
    """Создание нового оборудования"""

    model = Workstation
    form_class = WorkstationForm
    template_name = "assets/ws_form.html"
    permission_required = ['assets.add_workstation']

    def form_valid(self, form):
        """Обработка валидной формы"""
        self.object = form.save(commit=False)

        # Добавляем создателя
        self.object.created_by = self.request.user

        # Добавляем информацию для аудита
        self.object = self.add_audit_info(self.object, "создание")

        # Сохраняем объект
        self.object.save()

        # Добавляем сообщение об успехе
        messages.success(
            self.request,
            _('Оборудование "{}" успешно создано').format(self.object.name)
        )

        return redirect(self.get_success_url())

    def get_success_url(self):
        """URL для перенаправления после успешного создания"""
        return reverse("assets:asset_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        """Добавление флага создания"""
        context = super().get_context_data(**kwargs)
        context["create"] = True
        return context


# =======================
# Update View
# =======================

class WorkstationUpdateView(LoginRequiredMixin, PermissionRequiredMixin,
                            WorkstationContextMixin, WorkstationAuditMixin, UpdateView):
    """Редактирование оборудования"""

    model = Workstation
    form_class = WorkstationForm
    template_name = "assets/ws_form.html"
    permission_required = ['assets.change_workstation']

    def form_valid(self, form):
        """Обработка валидной формы"""
        self.object = form.save(commit=False)

        # Добавляем информацию для аудита
        self.object = self.add_audit_info(self.object, "редактирование")

        # Сохраняем объект
        self.object.save()

        # Добавляем сообщение об успехе
        messages.success(
            self.request,
            _('Изменения в оборудовании "{}" сохранены').format(self.object.name)
        )

        return redirect(self.get_success_url())

    def get_success_url(self):
        """URL для перенаправления после успешного обновления"""
        return reverse("assets:asset_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        """Добавление флага редактирования"""
        context = super().get_context_data(**kwargs)
        context["create"] = False
        return context


# =======================
# Delete View
# =======================

class WorkstationDeleteView(LoginRequiredMixin, PermissionRequiredMixin,
                            WorkstationAuditMixin, View):
    """Удаление оборудования"""

    permission_required = ['assets.delete_workstation']
    http_method_names = ['post']

    def post(self, request, pk):
        """Обработка POST-запроса на удаление"""
        obj = get_object_or_404(Workstation, pk=pk)

        try:
            # Добавляем информацию для аудита
            obj = self.add_audit_info(obj, "удаление")

            # Удаляем объект
            obj.delete()

            # Добавляем сообщение об успехе
            messages.success(
                request,
                _('Оборудование "{}" успешно удалено').format(obj.name)
            )

            return JsonResponse({
                "ok": True,
                "redirect": reverse("assets:asset_list")
            })

        except ProtectedError as e:
            return JsonResponse({
                "ok": False,
                "error": _("Нельзя удалить оборудование: есть связанные объекты"),
                "related": [str(o) for o in e.protected_objects],
            }, status=400)

        except Exception as e:
            return JsonResponse({
                "ok": False,
                "error": str(e),
            }, status=500)


# =======================
# AJAX Views
# =======================

@require_GET
@login_required
@permission_required('assets.view_workstation', raise_exception=True)
def ajax_get_workstation_status(request):
    """Получение текущего статуса оборудования"""
    ws_id = request.GET.get("id")

    if not ws_id:
        return JsonResponse({
            "ok": False,
            "error": _("Не указан ID оборудования")
        }, status=400)

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
        return JsonResponse({
            "ok": False,
            "error": _("Оборудование не найдено")
        }, status=404)


@require_POST
@login_required
@permission_required('assets.change_workstation', raise_exception=True)
def ajax_update_workstation_status(request):
    """Обновление статуса оборудования"""
    ws_id = request.POST.get("id")
    status = request.POST.get("status")

    if not ws_id or not status:
        return JsonResponse({
            "ok": False,
            "error": _("Не указаны обязательные параметры")
        }, status=400)

    try:
        ws = Workstation.objects.get(pk=ws_id)

        # Проверяем, что статус допустим
        valid_statuses = {choice[0] for choice in WorkstationStatus.choices}
        if status not in valid_statuses:
            return JsonResponse({
                "ok": False,
                "error": _("Недопустимый статус")
            }, status=400)

        # Обновляем статус
        old_status = ws.status
        old_status_display = ws.get_status_display()

        ws.status = status

        # Добавляем информацию для аудита
        ws._history_user = request.user
        ws._change_reason = build_change_reason(
            f"смена статуса с {old_status_display} на {ws.get_status_display()}"
        )

        ws.save(update_fields=["status"])

        return JsonResponse({
            "ok": True,
            "new_status": status,
            "new_status_display": ws.get_status_display(),
            "old_status": old_status,
            "old_status_display": old_status_display,
        })

    except Workstation.DoesNotExist:
        return JsonResponse({
            "ok": False,
            "error": _("Оборудование не найдено")
        }, status=404)


@require_GET
@login_required
@permission_required('assets.view_workstation', raise_exception=True)
def ajax_get_workstation_info(request):
    """Получение краткой информации об оборудовании"""
    ws_id = request.GET.get("id")

    if not ws_id:
        return JsonResponse({
            "ok": False,
            "error": _("Не указан ID оборудования")
        }, status=400)

    try:
        ws = Workstation.objects.select_related(
            'location', 'responsible'  # Убираем responsible__user
        ).get(pk=ws_id)

        data = {
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
        }

        return JsonResponse(data)

    except Workstation.DoesNotExist:
        return JsonResponse({
            "ok": False,
            "error": _("Оборудование не найдено")
        }, status=404)


# =======================
# Export Views
# =======================

@require_GET
@login_required
@permission_required('assets.view_workstation', raise_exception=True)
def export_workstations_csv(request):
    """Экспорт оборудования в CSV"""
    import csv
    from django.http import HttpResponse

    # Применяем фильтры из запроса
    queryset = Workstation.objects.all().select_related(
        'location', 'responsible'  # Убираем responsible__user
    )

    # Фильтрация (упрощенная версия)
    q = request.GET.get("q")
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) |
            Q(type_name__icontains=q) |
            Q(model__icontains=q)
        )

    category = request.GET.get("category")
    if category:
        queryset = queryset.filter(category=category)

    status = request.GET.get("status")
    if status:
        queryset = queryset.filter(status=status)

    location = request.GET.get("location")
    if location:
        queryset = queryset.filter(location_id=location)

    # Создаем HTTP ответ
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="workstations_{}.csv"'.format(
        timezone.now().strftime("%Y%m%d_%H%M%S")
    )

    # Создаем CSV writer
    writer = csv.writer(response, delimiter=';')

    # Заголовки
    writer.writerow([
        _("Название"),
        _("Тип"),
        _("Категория"),
        _("Производитель"),
        _("Модель"),
        _("Серийный номер"),
        _("Инвентарный номер"),
        _("Статус"),
        _("Глобальное состояние"),
        _("Локация"),
        _("Ответственный"),
        _("Дата ввода"),
        _("Гарантия до"),
        _("На гарантии"),
        _("Возраст (лет)"),
        _("Описание"),
    ])

    # Данные
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