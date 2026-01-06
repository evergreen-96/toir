"""
core/admin.py

Базовые классы для Django Admin с общей функциональностью.
Устраняет дублирование кода в admin.py всех приложений.
"""

from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin


class AuditableAdminMixin:
    """
    Миксин для админки с аудитом изменений.
    
    Автоматически:
    - Устанавливает _history_user и _change_reason при сохранении
    - Добавляет колонку "Последнее изменение"
    
    Использование:
        @admin.register(MyModel)
        class MyModelAdmin(AuditableAdminMixin, SimpleHistoryAdmin):
            list_display = (..., 'last_change')
            audit_create_message = "создание объекта"
            audit_change_message = "изменение объекта"
    """
    
    audit_create_message = "создание через админку"
    audit_change_message = "изменение через админку"
    
    def save_model(self, request, obj, form, change):
        """Сохранение с аудитом."""
        model_name = obj._meta.verbose_name
        
        if change:
            obj._change_reason = f"admin: {self.audit_change_message}"
        else:
            obj._change_reason = f"admin: {self.audit_create_message}"
        
        obj._history_user = request.user
        super().save_model(request, obj, form, change)
    
    @admin.display(description="Последнее изменение")
    def last_change(self, obj):
        """Отображает дату и автора последнего изменения."""
        if not hasattr(obj, 'history'):
            return "—"
        
        h = obj.history.first()
        if not h:
            return "—"
        
        return format_html(
            "{}<br><small class='text-muted'>{}</small>",
            h.history_date.strftime("%d.%m.%Y %H:%M"),
            h.history_user or "system",
        )


class StatusBadgeMixin:
    """
    Миксин для отображения статусов в виде бейджей.
    
    Использование:
        @admin.register(MyModel)
        class MyModelAdmin(StatusBadgeMixin, admin.ModelAdmin):
            status_field = 'status'
            status_colors = {
                'new': 'gray',
                'active': 'green',
                'closed': 'red',
            }
    """
    
    status_field = 'status'
    status_colors = {}
    
    @admin.display(description="Статус")
    def status_badge(self, obj):
        """Отображает статус в виде цветного бейджа."""
        status = getattr(obj, self.status_field, None)
        if not status:
            return "—"
        
        color = self.status_colors.get(status, 'black')
        display = obj.get_status_display() if hasattr(obj, 'get_status_display') else status
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            display,
        )


class ActiveBadgeMixin:
    """
    Миксин для отображения is_active в виде бейджа.
    """
    
    @admin.display(description="Активен", boolean=True)
    def is_active_badge(self, obj):
        """Отображает статус активности."""
        return getattr(obj, 'is_active', False)


class OptimizedQuerysetMixin:
    """
    Миксин для оптимизации запросов в админке.
    
    Использование:
        @admin.register(MyModel)
        class MyModelAdmin(OptimizedQuerysetMixin, admin.ModelAdmin):
            select_related_fields = ['location', 'responsible']
            prefetch_related_fields = ['tags', 'materials']
    """
    
    select_related_fields = []
    prefetch_related_fields = []
    
    def get_queryset(self, request):
        """Оптимизирует queryset."""
        qs = super().get_queryset(request)
        
        if self.select_related_fields:
            qs = qs.select_related(*self.select_related_fields)
        
        if self.prefetch_related_fields:
            qs = qs.prefetch_related(*self.prefetch_related_fields)
        
        return qs


# =============================================================================
# ГОТОВЫЕ БАЗОВЫЕ КЛАССЫ
# =============================================================================

class BaseModelAdmin(AuditableAdminMixin, OptimizedQuerysetMixin, SimpleHistoryAdmin):
    """
    Базовый класс для админки с полной функциональностью:
    - Аудит изменений
    - Оптимизация запросов
    - История изменений (simple_history)
    
    Использование:
        @admin.register(MyModel)
        class MyModelAdmin(BaseModelAdmin):
            list_display = ('name', 'status', 'last_change')
            select_related_fields = ['location']
    """
    pass


class BaseModelAdminWithStatus(StatusBadgeMixin, BaseModelAdmin):
    """
    Базовый класс для админки моделей со статусом.
    
    Использование:
        @admin.register(MyModel)
        class MyModelAdmin(BaseModelAdminWithStatus):
            list_display = ('name', 'status_badge', 'last_change')
            status_colors = {
                'new': 'gray',
                'active': 'green',
            }
    """
    pass


class BaseModelAdminWithActive(ActiveBadgeMixin, BaseModelAdmin):
    """
    Базовый класс для админки моделей с is_active.
    
    Использование:
        @admin.register(MyModel)
        class MyModelAdmin(BaseModelAdminWithActive):
            list_display = ('name', 'is_active_badge', 'last_change')
    """
    pass


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def get_status_color(status: str, colors_map: dict = None) -> str:
    """
    Возвращает цвет для статуса.
    
    Args:
        status: Значение статуса
        colors_map: Словарь {status: color}
    
    Returns:
        Цвет в формате CSS
    """
    default_colors = {
        # Общие статусы
        'new': '#6c757d',       # gray
        'active': '#28a745',    # green
        'inactive': '#dc3545',  # red
        'pending': '#ffc107',   # yellow
        'completed': '#28a745', # green
        'cancelled': '#dc3545', # red
        
        # Статусы работ
        'in_progress': '#007bff',  # blue
        'done': '#28a745',         # green
        'failed': '#dc3545',       # red
        
        # Статусы оборудования
        'prod': '#28a745',      # green
        'maint': '#ffc107',     # yellow
        'setup': '#17a2b8',     # cyan
        'problem': '#dc3545',   # red
    }
    
    if colors_map and status in colors_map:
        return colors_map[status]
    
    return default_colors.get(status, '#000000')


def format_status_badge(status: str, display: str, color: str = None) -> str:
    """
    Форматирует статус в виде HTML-бейджа.
    
    Args:
        status: Значение статуса
        display: Отображаемый текст
        color: CSS цвет (опционально)
    
    Returns:
        HTML строка с бейджем
    """
    if not color:
        color = get_status_color(status)
    
    return format_html(
        '<span class="badge" style="background-color: {}; color: white;">{}</span>',
        color,
        display,
    )
