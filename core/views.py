"""
core/views.py

Базовые классы для views с общей функциональностью.
Все приложения могут наследоваться от этих классов.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView

from core.mixins import (
    AuditMixin,
    FormAuditMixin,
    SuccessMessageMixin,
    DeleteViewMixin,
    SearchMixin,
    FilterMixin,
    ModelContextMixin,
    CreateUpdateContextMixin,
)


# =============================================================================
# БАЗОВЫЕ КЛАССЫ
# =============================================================================

class BaseListView(LoginRequiredMixin, SearchMixin, FilterMixin, ModelContextMixin, ListView):
    """
    Базовый класс для списков с:
    - Авторизацией
    - Поиском
    - Фильтрацией
    - Пагинацией
    - Контекстом модели
    
    Использование:
        class MyListView(BaseListView):
            model = MyModel
            template_name = 'myapp/list.html'
            paginate_by = 20
            search_fields = ['name', 'description']
            filter_fields = {'status': 'status', 'category': 'category'}
            ordering = ['-created_at']
    """
    
    paginate_by = 20
    ordering = ['-id']
    
    def get_queryset(self):
        """Оптимизированный queryset."""
        qs = super().get_queryset()
        
        # Применяем select_related если указано
        if hasattr(self, 'select_related') and self.select_related:
            qs = qs.select_related(*self.select_related)
        
        # Применяем prefetch_related если указано
        if hasattr(self, 'prefetch_related') and self.prefetch_related:
            qs = qs.prefetch_related(*self.prefetch_related)
        
        return qs


class BaseDetailView(LoginRequiredMixin, ModelContextMixin, DetailView):
    """
    Базовый класс для детального просмотра с:
    - Авторизацией
    - Контекстом модели
    - Оптимизацией запросов
    
    Использование:
        class MyDetailView(BaseDetailView):
            model = MyModel
            template_name = 'myapp/detail.html'
            select_related = ['location', 'responsible']
    """
    
    select_related = []
    prefetch_related = []
    
    def get_queryset(self):
        """Оптимизированный queryset."""
        qs = super().get_queryset()
        
        if self.select_related:
            qs = qs.select_related(*self.select_related)
        
        if self.prefetch_related:
            qs = qs.prefetch_related(*self.prefetch_related)
        
        return qs


class BaseCreateView(
    LoginRequiredMixin,
    FormAuditMixin,
    SuccessMessageMixin,
    CreateUpdateContextMixin,
    ModelContextMixin,
    CreateView
):
    """
    Базовый класс для создания объектов с:
    - Авторизацией
    - Аудитом
    - Сообщениями об успехе
    - Контекстом модели
    
    Использование:
        class MyCreateView(BaseCreateView):
            model = MyModel
            form_class = MyForm
            template_name = 'myapp/form.html'
            success_url = reverse_lazy('myapp:list')
            success_message = "Объект создан"
            audit_action = "создание объекта"
    """
    pass


class BaseUpdateView(
    LoginRequiredMixin,
    FormAuditMixin,
    SuccessMessageMixin,
    CreateUpdateContextMixin,
    ModelContextMixin,
    UpdateView
):
    """
    Базовый класс для редактирования объектов с:
    - Авторизацией
    - Аудитом
    - Сообщениями об успехе
    - Контекстом модели
    
    Использование:
        class MyUpdateView(BaseUpdateView):
            model = MyModel
            form_class = MyForm
            template_name = 'myapp/form.html'
            success_message = "Изменения сохранены"
            audit_action = "редактирование объекта"
    """
    pass


class BaseDeleteView(LoginRequiredMixin, DeleteViewMixin, View):
    """
    Базовый класс для удаления объектов с:
    - Авторизацией
    - Аудитом
    - Обработкой ProtectedError
    - JSON ответом для AJAX
    
    Использование:
        class MyDeleteView(BaseDeleteView):
            model = MyModel
            audit_action = "удаление объекта"
    """
    pass


# =============================================================================
# AJAX VIEWS
# =============================================================================

class BaseAjaxView(LoginRequiredMixin, View):
    """
    Базовый класс для AJAX views.
    Всегда возвращает JSON.
    
    Использование:
        class MyAjaxView(BaseAjaxView):
            def get_data(self, request):
                return {'items': [...]}
            
            # или для обработки ошибок:
            def get(self, request):
                try:
                    data = self.get_data(request)
                    return self.success_response(data)
                except Exception as e:
                    return self.error_response(str(e))
    """
    
    def success_response(self, data=None, **kwargs):
        """Возвращает успешный JSON ответ."""
        response_data = {'ok': True}
        if data:
            response_data.update(data)
        response_data.update(kwargs)
        return JsonResponse(response_data)
    
    def error_response(self, error, status=400, **kwargs):
        """Возвращает JSON ответ с ошибкой."""
        response_data = {'ok': False, 'error': error}
        response_data.update(kwargs)
        return JsonResponse(response_data, status=status)
    
    def get_data(self, request):
        """Переопределите для получения данных."""
        raise NotImplementedError
    
    def get(self, request, *args, **kwargs):
        """Обработка GET запроса."""
        try:
            data = self.get_data(request)
            return self.success_response(data)
        except Exception as e:
            return self.error_response(str(e))


class BaseSearchAjaxView(BaseAjaxView):
    """
    Базовый класс для AJAX поиска (для TomSelect, Select2).
    
    Использование:
        class MySearchView(BaseSearchAjaxView):
            model = MyModel
            search_fields = ['name', 'code']
            value_field = 'id'
            text_field = 'name'
            
            # Опционально:
            def get_queryset(self):
                return super().get_queryset().filter(is_active=True)
    """
    
    model = None
    search_fields = ['name']
    value_field = 'id'
    text_field = 'name'
    limit = 50
    
    def get_queryset(self):
        """Возвращает базовый queryset."""
        return self.model.objects.all()
    
    def filter_queryset(self, qs, query):
        """Фильтрует queryset по поисковому запросу."""
        from django.db.models import Q
        
        if not query:
            return qs
        
        q_objects = Q()
        for field in self.search_fields:
            q_objects |= Q(**{f'{field}__icontains': query})
        
        return qs.filter(q_objects)
    
    def get_item_data(self, obj):
        """Возвращает данные для одного элемента."""
        return {
            'value': getattr(obj, self.value_field),
            'text': getattr(obj, self.text_field),
        }
    
    def get_data(self, request):
        """Возвращает результаты поиска."""
        query = request.GET.get('q', '').strip()
        
        qs = self.get_queryset()
        qs = self.filter_queryset(qs, query)
        qs = qs[:self.limit]
        
        results = [self.get_item_data(obj) for obj in qs]
        
        return {'results': results}


# =============================================================================
# ФУНКЦИОНАЛЬНЫЕ ХЕЛПЕРЫ
# =============================================================================

def ajax_response(ok=True, **kwargs):
    """
    Простая функция для создания JSON ответа.
    
    Использование:
        return ajax_response(ok=True, data={'id': 1})
        return ajax_response(ok=False, error='Not found', status=404)
    """
    status = kwargs.pop('status', 200 if ok else 400)
    response_data = {'ok': ok}
    response_data.update(kwargs)
    return JsonResponse(response_data, status=status)


def require_ajax(view_func):
    """
    Декоратор для views, которые должны вызываться только через AJAX.
    
    Использование:
        @require_ajax
        def my_view(request):
            return JsonResponse({'ok': True})
    """
    from functools import wraps
    from django.http import HttpResponseBadRequest
    
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return HttpResponseBadRequest('AJAX request required')
        return view_func(request, *args, **kwargs)
    
    return wrapper
