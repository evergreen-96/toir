from django.db.models import Count, Q
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, DetailView
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models.deletion import ProtectedError
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_POST

from .models import HumanResource
from .forms import HumanResourceForm
from core.audit import build_change_reason


# =======================
# Mixins
# =======================

class HRContextMixin:
    """Миксин для добавления общего контекста"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class HRPermissionMixin(PermissionRequiredMixin):
    """Миксин для проверки прав доступа к сотрудникам"""

    def get_permission_required(self):
        if self.request.method == 'GET':
            return ['hr.view_humanresource']
        elif self.request.method == 'POST':
            return ['hr.add_humanresource']
        elif self.request.method in ['PUT', 'PATCH']:
            return ['hr.change_humanresource']
        elif self.request.method == 'DELETE':
            return ['hr.delete_humanresource']
        return []


class HRAuditMixin:
    """Миксин для аудита изменений сотрудников"""

    def add_audit_info(self, obj, action):
        """Добавляет информацию для аудита"""
        obj._history_user = self.request.user
        obj._change_reason = build_change_reason(
            f"{action} сотрудника"
        )
        return obj


# =======================
# List View
# =======================

class HRListView(LoginRequiredMixin, HRContextMixin, ListView):
    """Список сотрудников с фильтрацией"""

    model = HumanResource
    template_name = "hr/hr_list.html"
    paginate_by = 20
    ordering = ["name"]
    context_object_name = "employees"

    def get_queryset(self):
        """Фильтрация и оптимизация queryset"""
        queryset = HumanResource.objects.all().select_related('manager')

        # Аннотируем количество подчиненных
        queryset = queryset.annotate(
            sub_count=Count('subordinates')
        )

        # Применяем фильтры
        queryset = self.apply_filters(queryset)

        # Сортировка
        sort_by = self.request.GET.get('sort', 'name')
        order = self.request.GET.get('order', 'asc')

        if sort_by in ['name', 'job_title']:
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
                Q(job_title__icontains=q)
            )

        # Руководитель
        manager = self.request.GET.get("manager")
        if manager:
            filters &= Q(manager_id=manager)

        # Должность
        job_title = self.request.GET.get("job_title")
        if job_title:
            filters &= Q(job_title__icontains=job_title)

        # Только руководители
        only_managers = self.request.GET.get("only_managers")
        if only_managers:
            # Используем аннотированное поле sub_count
            filters &= Q(sub_count__gt=0)

        # Активность
        is_active = self.request.GET.get("is_active")
        if is_active:
            filters &= Q(is_active=(is_active == 'true'))

        return queryset.filter(filters)

    def get_context_data(self, **kwargs):
        """Добавление дополнительного контекста"""
        context = super().get_context_data(**kwargs)

        # Параметры фильтров
        context["filter_params"] = {
            "q": self.request.GET.get("q", ""),
            "manager": self.request.GET.get("manager", ""),
            "job_title": self.request.GET.get("job_title", ""),
            "only_managers": self.request.GET.get("only_managers", ""),
            "is_active": self.request.GET.get("is_active", ""),
            "sort": self.request.GET.get("sort", "name"),
            "order": self.request.GET.get("order", "asc"),
        }

        # Данные для фильтров
        context["managers"] = HumanResource.objects.filter(
            is_active=True
        ).order_by('name')

        # Список уникальных должностей для фильтра
        job_titles = HumanResource.objects.exclude(
            job_title=""
        ).values_list('job_title', flat=True).distinct()
        context["job_titles"] = job_titles

        # Статистика
        total = HumanResource.objects.count()
        active = HumanResource.objects.filter(is_active=True).count()

        # Подсчет руководителей (у кого есть подчиненные)
        managers_count = HumanResource.objects.annotate(
            sub_cnt=Count('subordinates')
        ).filter(sub_cnt__gt=0).count()

        context["stats"] = {
            "total": total,
            "active": active,
            "managers": managers_count,
            "job_titles": job_titles.count(),
        }

        return context


# =======================
# Detail View
# =======================

class HRDetailView(LoginRequiredMixin, HRContextMixin, DetailView):
    """Детальная информация о сотруднике"""

    model = HumanResource
    template_name = "hr/hr_detail.html"
    context_object_name = "employee"

    def get_queryset(self):
        """Оптимизация запросов для детального просмотра"""
        return super().get_queryset().select_related('manager')

    def get_context_data(self, **kwargs):
        """Добавление дополнительного контекста"""
        context = super().get_context_data(**kwargs)

        # Добавляем количество подчиненных
        context['subordinates_count'] = self.object.subordinates.count()

        # Получаем историю изменений
        if self.object:
            context['history'] = self.object.history.all()[:10]

        return context


# =======================
# Create View
# =======================

class HRCreateView(LoginRequiredMixin, PermissionRequiredMixin,
                   HRContextMixin, HRAuditMixin, View):
    """Создание нового сотрудника"""

    permission_required = ['hr.add_humanresource']
    template_name = "hr/hr_form.html"

    def get(self, request):
        """Отображение формы создания"""
        form = HumanResourceForm()

        # Список должностей для автодополнения
        job_titles = HumanResource.objects.exclude(
            job_title=""
        ).values_list('job_title', flat=True).distinct()

        return render(request, self.template_name, {
            'form': form,
            'create': True,
            'job_titles': job_titles,
        })

    def post(self, request):
        """Обработка создания"""
        form = HumanResourceForm(request.POST)

        # Список должностей для автодополнения
        job_titles = HumanResource.objects.exclude(
            job_title=""
        ).values_list('job_title', flat=True).distinct()

        if form.is_valid():
            obj = form.save(commit=False)

            # Добавляем информацию для аудита
            obj = self.add_audit_info(obj, "создание")

            # Сохраняем объект
            obj.save()

            # Добавляем сообщение об успехе
            messages.success(
                request,
                _('Сотрудник "{}" успешно создан').format(obj.name)
            )

            return redirect("hr:hr_detail", pk=obj.pk)

        return render(request, self.template_name, {
            'form': form,
            'create': True,
            'job_titles': job_titles,
        })


# =======================
# Update View
# =======================

class HRUpdateView(LoginRequiredMixin, PermissionRequiredMixin,
                   HRContextMixin, HRAuditMixin, View):
    """Редактирование сотрудника"""

    permission_required = ['hr.change_humanresource']
    template_name = "hr/hr_form.html"

    def get(self, request, pk):
        """Отображение формы редактирования"""
        obj = get_object_or_404(HumanResource, pk=pk)
        form = HumanResourceForm(instance=obj)

        # Список должностей для автодополнения
        job_titles = HumanResource.objects.exclude(
            job_title=""
        ).values_list('job_title', flat=True).distinct()

        return render(request, self.template_name, {
            'form': form,
            'create': False,
            'object': obj,
            'job_titles': job_titles,
        })

    def post(self, request, pk):
        """Обработка редактирования"""
        obj = get_object_or_404(HumanResource, pk=pk)
        form = HumanResourceForm(request.POST, instance=obj)

        # Список должностей для автодополнения
        job_titles = HumanResource.objects.exclude(
            job_title=""
        ).values_list('job_title', flat=True).distinct()

        if form.is_valid():
            obj = form.save(commit=False)

            # Добавляем информацию для аудита
            obj = self.add_audit_info(obj, "редактирование")

            # Сохраняем объект
            obj.save()

            # Добавляем сообщение об успехе
            messages.success(
                request,
                _('Изменения в сотруднике "{}" сохранены').format(obj.name)
            )

            return redirect("hr:hr_detail", pk=obj.pk)

        return render(request, self.template_name, {
            'form': form,
            'create': False,
            'object': obj,
            'job_titles': job_titles,
        })


# =======================
# Delete View
# =======================

class HumanResourceDeleteView(LoginRequiredMixin, PermissionRequiredMixin,
                              HRAuditMixin, View):
    """Удаление сотрудника"""

    permission_required = ['hr.delete_humanresource']
    http_method_names = ['post']

    def post(self, request, pk):
        """Обработка POST-запроса на удаление"""
        obj = get_object_or_404(HumanResource, pk=pk)

        try:
            # Добавляем информацию для аудита
            obj = self.add_audit_info(obj, "удаление")

            # Удаляем объект
            obj.delete()

            # Добавляем сообщение об успехе
            messages.success(
                request,
                _('Сотрудник "{}" успешно удален').format(obj.name)
            )

            return JsonResponse({
                "ok": True,
                "redirect": reverse("hr:hr_list")
            })

        except ProtectedError as e:
            return JsonResponse({
                "ok": False,
                "error": _("Нельзя удалить сотрудника: есть связанные объекты"),
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
@permission_required('hr.view_humanresource', raise_exception=True)
def hr_manager_autocomplete(request):
    """Автодополнение для поиска руководителей"""
    q = request.GET.get("q", "")

    qs = HumanResource.objects.filter(is_active=True)

    if q:
        qs = qs.filter(name__icontains=q)

    qs = qs.order_by("name")[:20]

    return JsonResponse({
        "results": [
            {
                "id": x.pk,
                "text": f"{x.name} — {x.job_title}" if x.job_title else x.name
            }
            for x in qs
        ]
    })


@require_GET
@login_required
@permission_required('hr.view_humanresource', raise_exception=True)
def hr_job_title_autocomplete(request):
    """Автодополнение для поиска должностей"""
    q = request.GET.get("q", "")

    qs = (
        HumanResource.objects
        .exclude(job_title="")
        .values_list("job_title", flat=True)
        .distinct()
        .order_by("job_title")
    )

    if q:
        qs = qs.filter(job_title__icontains=q)

    qs = qs[:20]

    return JsonResponse({
        "results": [
            {"id": title, "text": title}
            for title in qs
        ]
    })


# =======================
# Export Views
# =======================

@require_GET
@login_required
@permission_required('hr.view_humanresource', raise_exception=True)
def export_hr_csv(request):
    """Экспорт сотрудников в CSV"""
    import csv
    from django.http import HttpResponse
    from django.utils import timezone

    # Применяем фильтры из запроса
    queryset = HumanResource.objects.all().select_related('manager')

    # Фильтрация
    q = request.GET.get("q")
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) |
            Q(job_title__icontains=q)
        )

    manager = request.GET.get("manager")
    if manager:
        queryset = queryset.filter(manager_id=manager)

    job_title = request.GET.get("job_title")
    if job_title:
        queryset = queryset.filter(job_title__icontains=job_title)

    # Создаем HTTP ответ
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = f'attachment; filename="hr_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    # Создаем CSV writer
    writer = csv.writer(response, delimiter=';')

    # Заголовки
    writer.writerow([
        _("ФИО"),
        _("Должность"),
        _("Руководитель"),
        _("Активен"),
        _("Количество подчиненных"),
        _("Дата создания"),
        _("Дата обновления"),
    ])

    # Данные
    for emp in queryset:
        writer.writerow([
            emp.name,
            emp.job_title or "",
            emp.manager.name if emp.manager else "",
            _("Да") if emp.is_active else _("Нет"),
            emp.subordinates.count(),
            emp.created_at.strftime("%d.%m.%Y %H:%M"),
            emp.updated_at.strftime("%d.%m.%Y %H:%M"),
        ])

    return response