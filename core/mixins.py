"""
core/mixins.py

Централизованные миксины для всех приложений.
Устраняют дублирование кода между assets, hr, inventory, maintenance, locations.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.deletion import ProtectedError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST

from core.audit import build_change_reason


class AuditMixin:
    """
    Миксин для автоматического аудита изменений моделей.
    
    Использование:
        class MyCreateView(AuditMixin, CreateView):
            audit_action = "создание объекта"
    """
    
    audit_action = None  # Должен быть переопределён или используется get_audit_action()
    
    def get_audit_action(self):
        """Возвращает название действия для аудита."""
        if self.audit_action:
            return self.audit_action
        
        # Автоматическое определение действия
        view_name = self.__class__.__name__.lower()
        if 'create' in view_name:
            return f"создание {self._get_model_verbose_name()}"
        elif 'update' in view_name:
            return f"редактирование {self._get_model_verbose_name()}"
        elif 'delete' in view_name:
            return f"удаление {self._get_model_verbose_name()}"
        return "изменение"
    
    def _get_model_verbose_name(self):
        """Получает verbose_name модели."""
        if hasattr(self, 'model') and self.model:
            return self.model._meta.verbose_name
        return "объекта"
    
    def add_audit_info(self, obj):
        """Добавляет информацию аудита к объекту."""
        if hasattr(self, 'request') and self.request.user.is_authenticated:
            obj._history_user = self.request.user
        obj._change_reason = build_change_reason(self.get_audit_action())
        return obj


class FormAuditMixin(AuditMixin):
    """
    Миксин для views с формами (CreateView, UpdateView).
    Автоматически добавляет аудит при сохранении формы.
    """
    
    def form_valid(self, form):
        """Добавляет аудит перед сохранением."""
        self.object = form.save(commit=False)
        self.add_audit_info(self.object)
        self.object.save()
        # Сохраняем M2M поля если есть
        if hasattr(form, 'save_m2m'):
            form.save_m2m()
        
        return super().form_valid(form)


class SuccessMessageMixin:
    """
    Миксин для отображения сообщений об успехе.
    
    Использование:
        class MyCreateView(SuccessMessageMixin, CreateView):
            success_message = "Объект создан"
            # или
            def get_success_message(self):
                return f"Объект '{self.object}' создан"
    """
    
    success_message = None
    
    def get_success_message(self):
        """Возвращает сообщение об успехе."""
        if self.success_message:
            return self.success_message.format(object=self.object) if hasattr(self, 'object') else self.success_message
        return None
    
    def form_valid(self, form):
        """Показывает сообщение после успешного сохранения."""
        response = super().form_valid(form)
        message = self.get_success_message()
        if message:
            messages.success(self.request, message)
        return response


class DeleteViewMixin(AuditMixin):
    """
    Миксин для удаления с обработкой ProtectedError.
    Возвращает JSON для AJAX-запросов.
    
    Использование:
        class MyDeleteView(DeleteViewMixin, View):
            model = MyModel
            audit_action = "удаление объекта"
            success_url = reverse_lazy('myapp:list')  # опционально
    """
    
    model = None
    success_url = None  # URL для редиректа после удаления
    
    def get_success_url(self):
        """Возвращает URL для редиректа."""
        return self.success_url
    
    @method_decorator(require_POST)
    def post(self, request, pk):
        """Обработка DELETE запроса."""
        from django.shortcuts import get_object_or_404
        
        obj = get_object_or_404(self.model, pk=pk)
        
        try:
            self.add_audit_info(obj)
            obj.delete()
            
            response_data = {"ok": True}
            
            # Добавляем redirect если указан
            redirect_url = self.get_success_url()
            if redirect_url:
                response_data["redirect"] = str(redirect_url)
            
            return JsonResponse(response_data)
        
        except ProtectedError as e:
            related = [str(o) for o in e.protected_objects]
            return JsonResponse({
                "ok": False,
                "error": "Нельзя удалить: есть связанные объекты",
                "related": related[:10],  # Ограничиваем список
            }, status=400)


class SearchMixin:
    """
    Миксин для поиска в ListView.
    
    Использование:
        class MyListView(SearchMixin, ListView):
            search_fields = ['name', 'description']
    """
    
    search_fields = []
    search_param = 'q'
    
    def get_search_query(self):
        """Возвращает поисковый запрос."""
        return self.request.GET.get(self.search_param, '').strip()
    
    def get_queryset(self):
        """Применяет поиск к queryset."""
        from django.db.models import Q
        
        qs = super().get_queryset()
        query = self.get_search_query()
        
        if query and self.search_fields:
            q_objects = Q()
            for field in self.search_fields:
                q_objects |= Q(**{f'{field}__icontains': query})
            qs = qs.filter(q_objects)
        
        return qs
    
    def get_context_data(self, **kwargs):
        """Добавляет поисковый запрос в контекст."""
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.get_search_query()
        context['q'] = self.get_search_query()  # Для совместимости
        return context


class FilterMixin:
    """
    Миксин для фильтрации в ListView.
    
    Использование:
        class MyListView(FilterMixin, ListView):
            filter_fields = {
                'status': 'status',
                'category': 'category',
                'is_active': 'is_active',
            }
    """
    
    filter_fields = {}  # {'param_name': 'field_name'}
    
    def get_filter_params(self):
        """Возвращает параметры фильтрации из GET."""
        params = {}
        for param, field in self.filter_fields.items():
            value = self.request.GET.get(param)
            if value:
                params[field] = value
        return params
    
    def get_queryset(self):
        """Применяет фильтры к queryset."""
        qs = super().get_queryset()
        filters = self.get_filter_params()
        if filters:
            qs = qs.filter(**filters)
        return qs
    
    def get_context_data(self, **kwargs):
        """Добавляет текущие фильтры в контекст."""
        context = super().get_context_data(**kwargs)
        context['current_filters'] = {
            param: self.request.GET.get(param, '')
            for param in self.filter_fields.keys()
        }
        return context


class ModelContextMixin:
    """
    Миксин для добавления информации о модели в контекст.
    """
    
    def get_context_data(self, **kwargs):
        """Добавляет метаданные модели в контекст."""
        context = super().get_context_data(**kwargs)
        
        if hasattr(self, 'model') and self.model:
            context['model_name'] = self.model._meta.verbose_name
            context['model_name_plural'] = self.model._meta.verbose_name_plural
            context['app_label'] = self.model._meta.app_label
        
        return context


class CreateUpdateContextMixin:
    """
    Миксин для добавления флага create/update в контекст.
    """
    
    def get_context_data(self, **kwargs):
        """Добавляет флаг create в контекст."""
        context = super().get_context_data(**kwargs)
        context['create'] = not bool(getattr(self, 'object', None) and self.object.pk)
        return context


# =============================================================================
# КОМБИНИРОВАННЫЕ МИКСИНЫ (для удобства)
# =============================================================================

class BaseViewMixin(LoginRequiredMixin, ModelContextMixin):
    """
    Базовый миксин для всех views.
    Требует авторизацию и добавляет контекст модели.
    """
    pass


class BaseFormViewMixin(BaseViewMixin, FormAuditMixin, SuccessMessageMixin, CreateUpdateContextMixin):
    """
    Базовый миксин для CreateView и UpdateView.
    Включает авторизацию, аудит, сообщения об успехе.
    """
    pass
