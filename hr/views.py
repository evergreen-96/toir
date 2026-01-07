import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.http import require_GET

from core.views import BaseListView, BaseDetailView, BaseDeleteView
from core.mixins import AuditMixin
from .models import HumanResource
from .forms import HumanResourceForm


# =============================================================================
# LIST VIEW
# =============================================================================

class HRListView(BaseListView):
    """Список сотрудников с поиском, фильтрацией и статистикой."""

    model = HumanResource
    template_name = "hr/hr_list.html"
    context_object_name = "employees"
    paginate_by = 1
    ordering = ["name"]

    # Поиск
    search_fields = ['name', 'job_title']

    # Оптимизация
    select_related = ['manager']

    def get_queryset(self):
        """Queryset с аннотацией количества подчинённых."""
        qs = super().get_queryset()

        # Аннотируем количество подчинённых
        qs = qs.annotate(sub_count=Count('subordinates'))

        # Дополнительные фильтры
        qs = self._apply_extra_filters(qs)

        # Сортировка
        qs = self._apply_sorting(qs)

        return qs

    def _apply_extra_filters(self, qs):
        """Применяет дополнительные фильтры."""
        # Руководитель
        manager_id = self.request.GET.get("manager")
        if manager_id:
            qs = qs.filter(manager_id=manager_id)

        # Должность
        job_title = self.request.GET.get("job_title")
        if job_title:
            qs = qs.filter(job_title__icontains=job_title)

        # Активность
        is_active = self.request.GET.get("is_active")
        if is_active:
            qs = qs.filter(is_active=(is_active == 'true'))

        # Только руководители
        only_managers = self.request.GET.get("only_managers")
        if only_managers:
            qs = qs.filter(sub_count__gt=0)

        # Есть подчинённые
        has_subordinates = self.request.GET.get("has_subordinates")
        if has_subordinates:
            qs = qs.filter(sub_count__gt=0)

        return qs

    def _apply_sorting(self, qs):
        """Применяет сортировку."""
        sort_by = self.request.GET.get('sort', 'name')
        order = self.request.GET.get('order', 'asc')

        if sort_by in ['name', 'job_title']:
            if order == 'desc':
                sort_by = f'-{sort_by}'
            qs = qs.order_by(sort_by)

        return qs

    def get_context_data(self, **kwargs):
        """Добавляет фильтры и статистику."""
        context = super().get_context_data(**kwargs)

        # Параметры фильтров для формы
        context["filter_params"] = {
            "q": self.request.GET.get("q", ""),
            "manager": self.request.GET.get("manager", ""),
            "job_title": self.request.GET.get("job_title", ""),
            "only_managers": self.request.GET.get("only_managers", ""),
            "has_subordinates": self.request.GET.get("has_subordinates", ""),
            "is_active": self.request.GET.get("is_active", ""),
            "sort": self.request.GET.get("sort", "name"),
            "order": self.request.GET.get("order", "asc"),
        }

        # Данные для фильтров
        context["managers"] = HumanResource.objects.filter(
            is_active=True
        ).order_by('name')

        # Список уникальных должностей
        context["job_titles"] = HumanResource.objects.exclude(
            job_title=""
        ).values_list('job_title', flat=True).distinct()

        # Статистика
        context["stats"] = self._get_stats()

        return context

    def _get_stats(self):
        """Возвращает статистику по сотрудникам."""
        total = HumanResource.objects.count()
        active = HumanResource.objects.filter(is_active=True).count()

        managers_count = HumanResource.objects.annotate(
            sub_cnt=Count('subordinates')
        ).filter(sub_cnt__gt=0).count()

        job_titles_count = HumanResource.objects.exclude(
            job_title=""
        ).values_list('job_title', flat=True).distinct().count()

        return {
            "total": total,
            "active": active,
            "managers": managers_count,
            "job_titles": job_titles_count,
        }


# =============================================================================
# DETAIL VIEW
# =============================================================================

class HRDetailView(BaseDetailView):
    """Детальная информация о сотруднике."""

    model = HumanResource
    template_name = "hr/hr_detail.html"
    context_object_name = "employee"
    select_related = ['manager']

    def get_context_data(self, **kwargs):
        """Добавляет подчинённых и историю."""
        context = super().get_context_data(**kwargs)

        context['subordinates_count'] = self.object.subordinates.count()

        # История изменений (последние 10)
        if hasattr(self.object, 'history'):
            context['history'] = self.object.history.all()[:10]

        return context


# =============================================================================
# CREATE VIEW
# =============================================================================

class HRCreateView(LoginRequiredMixin, PermissionRequiredMixin, AuditMixin, View):
    """Создание нового сотрудника."""

    permission_required = ['hr.add_humanresource']
    template_name = "hr/hr_form.html"
    audit_action = "создание сотрудника"

    def get(self, request):
        """Отображение формы."""
        form = HumanResourceForm()

        # Предзаполнение руководителя из GET
        manager_id = request.GET.get('manager')
        manager_info = None
        initial_manager = None

        if manager_id:
            try:
                manager_instance = HumanResource.objects.get(pk=manager_id)
                initial_manager = manager_instance
                form = HumanResourceForm(initial={'manager': manager_instance})
                manager_info = {
                    'id': manager_instance.pk,
                    'name': manager_instance.name,
                    'job_title': manager_instance.job_title or 'нет должности'
                }
            except HumanResource.DoesNotExist:
                pass

        context = self._get_form_context(form, create=True)
        context.update({
            'parent_manager': manager_id,
            'manager_info': manager_info,
            'initial_manager': initial_manager,
        })

        return render(request, self.template_name, context)

    def post(self, request):
        """Обработка формы."""
        form = HumanResourceForm(request.POST)

        if form.is_valid():
            try:
                obj = form.save(commit=False)
                self.add_audit_info(obj)
                obj.save()

                # Обработка "Сохранить и добавить ещё"
                if request.POST.get('save_and_add'):
                    messages.success(request, _('Сотрудник "{}" создан').format(obj.name))
                    return redirect(f"{reverse('hr:hr_new')}?manager={obj.pk}")

                messages.success(request, _('Сотрудник "{}" создан').format(obj.name))
                return redirect('hr:hr_detail', pk=obj.pk)

            except Exception as e:
                messages.error(request, _('Ошибка: {}').format(str(e)))
        else:
            messages.error(request, _('Исправьте ошибки в форме'))

        context = self._get_form_context(form, create=True)
        return render(request, self.template_name, context)

    def _get_form_context(self, form, create=True):
        """Возвращает контекст для формы."""
        all_managers = HumanResource.objects.filter(
            is_active=True
        ).order_by('name').values('id', 'name', 'job_title')[:100]

        all_job_titles = HumanResource.objects.exclude(
            job_title=""
        ).values_list('job_title', flat=True).distinct().order_by('job_title')[:100]

        job_titles = HumanResource.objects.exclude(
            job_title__isnull=True
        ).exclude(
            job_title=""
        ).values_list('job_title', flat=True).distinct().order_by('job_title')

        return {
            'form': form,
            'create': create,
            'job_titles': job_titles,
            'all_managers': list(all_managers),
            'all_job_titles': list(all_job_titles),
        }


# =============================================================================
# UPDATE VIEW
# =============================================================================

class HRUpdateView(LoginRequiredMixin, PermissionRequiredMixin, AuditMixin, View):
    """Редактирование сотрудника."""

    permission_required = ['hr.change_humanresource']
    template_name = "hr/hr_form.html"
    audit_action = "редактирование сотрудника"

    def get(self, request, pk):
        """Отображение формы."""
        obj = get_object_or_404(HumanResource, pk=pk)
        form = HumanResourceForm(instance=obj)

        context = self._get_form_context(form, obj, create=False)
        return render(request, self.template_name, context)

    def post(self, request, pk):
        """Обработка формы."""
        obj = get_object_or_404(HumanResource, pk=pk)
        form = HumanResourceForm(request.POST, instance=obj)

        if form.is_valid():
            try:
                obj = form.save(commit=False)
                self.add_audit_info(obj)
                obj.save()

                messages.success(request, _('Изменения сохранены'))
                return redirect('hr:hr_detail', pk=obj.pk)

            except Exception as e:
                messages.error(request, _('Ошибка: {}').format(str(e)))
        else:
            messages.error(request, _('Исправьте ошибки в форме'))

        context = self._get_form_context(form, obj, create=False)
        return render(request, self.template_name, context)

    def _get_form_context(self, form, obj, create=False):
        """Возвращает контекст для формы."""
        all_managers = HumanResource.objects.filter(
            is_active=True
        ).exclude(pk=obj.pk).order_by('name').values('id', 'name', 'job_title')[:100]

        all_job_titles = HumanResource.objects.exclude(
            job_title=""
        ).values_list('job_title', flat=True).distinct().order_by('job_title')[:100]

        job_titles = HumanResource.objects.exclude(
            job_title=""
        ).values_list('job_title', flat=True).distinct()

        return {
            'form': form,
            'create': create,
            'object': obj,
            'job_titles': job_titles,
            'all_managers': list(all_managers),
            'all_job_titles': list(all_job_titles),
        }


# =============================================================================
# DELETE VIEW
# =============================================================================

class HumanResourceDeleteView(PermissionRequiredMixin, BaseDeleteView):
    """Удаление сотрудника."""

    model = HumanResource
    permission_required = ['hr.delete_humanresource']
    audit_action = "удаление сотрудника"
    success_url = reverse_lazy('hr:hr_list')


# =============================================================================
# AJAX VIEWS
# =============================================================================

@require_GET
@login_required
@permission_required('hr.view_humanresource', raise_exception=True)
def hr_manager_autocomplete(request):
    """Автодополнение для поиска руководителей (TomSelect)."""
    q = request.GET.get("q", "").strip()

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
    """Автодополнение для должностей (TomSelect)."""
    q = request.GET.get("q", "").strip()
    load_all = request.GET.get("load_all", "")

    qs = HumanResource.objects.exclude(job_title="")

    if load_all == "true" or not q:
        titles = (
            qs.values_list("job_title", flat=True)
            .distinct()
            .order_by("job_title")[:100]
        )
    else:
        qs = qs.filter(job_title__icontains=q)
        titles = (
            qs.values_list("job_title", flat=True)
            .distinct()
            .order_by("job_title")[:20]
        )

    return JsonResponse({
        "results": [{"value": title, "text": title} for title in titles]
    })


# =============================================================================
# EXPORT VIEW
# =============================================================================

@require_GET
@login_required
@permission_required('hr.view_humanresource', raise_exception=True)
def export_hr_csv(request):
    """Экспорт сотрудников в CSV."""
    # Базовый queryset
    queryset = HumanResource.objects.all().select_related('manager')

    # Применяем фильтры из запроса
    q = request.GET.get("q")
    if q:
        queryset = queryset.filter(
            Q(name__icontains=q) | Q(job_title__icontains=q)
        )

    manager = request.GET.get("manager")
    if manager:
        queryset = queryset.filter(manager_id=manager)

    job_title = request.GET.get("job_title")
    if job_title:
        queryset = queryset.filter(job_title__icontains=job_title)

    # HTTP Response
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = (
        f'attachment; filename="hr_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    )

    writer = csv.writer(response, delimiter=';')

    # Заголовки
    writer.writerow([
        _("ФИО"),
        _("Должность"),
        _("Руководитель"),
        _("Активен"),
        _("Подчинённых"),
        _("Создан"),
        _("Обновлён"),
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
