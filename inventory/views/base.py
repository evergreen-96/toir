from django.db.models import Q
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.shortcuts import get_object_or_404
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.deletion import ProtectedError
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST


class BaseInventoryView(LoginRequiredMixin):
    """Базовый класс для всех вьюх инвентаря"""
    permission_required = None

    def get_permission_required(self):
        return self.permission_required

    def get_context_data(self, **kwargs):
        """Добавляем модель в контекст"""
        context = super().get_context_data(**kwargs)
        context['model_name'] = self.model._meta.verbose_name
        context['model_name_plural'] = self.model._meta.verbose_name_plural
        return context


class BaseListView(BaseInventoryView, ListView):
    """Базовый класс для списков с поиском"""
    paginate_by = 20
    filter_form_class = None

    def get_search_query(self):
        """Возвращает поисковый запрос"""
        return self.request.GET.get("q", "").strip()

    def get_queryset_base(self):
        """Базовый queryset без поиска"""
        return super().get_queryset()

    def get_queryset(self):
        qs = self.get_queryset_base()
        search_query = self.get_search_query()

        if search_query:
            qs = self.apply_search(qs, search_query)

        return qs

    def apply_search(self, qs, search_query):
        """Применяет поиск - должен быть переопределен в дочерних классах"""
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.get_search_query()

        # Добавляем форму фильтрации если указана
        if self.filter_form_class:
            context['filter_form'] = self.filter_form_class(self.request.GET)

        return context


class BaseDetailView(BaseInventoryView, DetailView):
    """Базовый класс для детальных представлений"""
    pass


class BaseCreateUpdateView(BaseInventoryView):
    """Базовый класс для создания и редактирования"""

    def form_valid(self, form):
        """Общая логика при валидной форме"""
        from core.audit import build_change_reason

        obj = form.save(commit=False)
        obj._history_user = self.request.user
        obj._change_reason = build_change_reason(self.get_action_name())
        obj.save()
        form.save_m2m()

        messages.success(self.request, self.get_success_message())
        return super().form_valid(form)

    def get_action_name(self):
        """Название действия - должно быть переопределено"""
        raise NotImplementedError

    def get_success_message(self):
        """Сообщение об успехе - должно быть переопределено"""
        raise NotImplementedError

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['create'] = isinstance(self, CreateView)
        return context


class BaseDeleteView(BaseInventoryView, DeleteView):
    """Базовый класс для удаления с проверкой зависимостей"""

    @method_decorator(require_POST)
    def post(self, request, *args, **kwargs):
        return self.delete(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        from core.audit import build_change_reason

        self.object = self.get_object()

        try:
            self.object._history_user = request.user
            self.object._change_reason = build_change_reason(self.get_action_name())
            self.object.delete()
            return JsonResponse({"ok": True})

        except ProtectedError as e:
            related = [str(obj) for obj in e.protected_objects]
            return JsonResponse({
                "ok": False,
                "error": "Нельзя удалить: есть связанные объекты",
                "related": related,
            }, status=400)

    def get_action_name(self):
        """Название действия удаления - должно быть переопределено"""
        raise NotImplementedError