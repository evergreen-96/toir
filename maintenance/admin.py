"""
maintenance/admin.py

Рефакторинг с использованием BaseModelAdmin.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from core.admin_base import BaseModelAdmin
from .models import WorkOrder, WorkOrderMaterial, PlannedOrder, File, WorkOrderAttachment


# =============================================================================
# INLINES
# =============================================================================

class WorkOrderMaterialInline(admin.TabularInline):
    """Inline для материалов задачи."""
    model = WorkOrderMaterial
    extra = 0
    autocomplete_fields = ['material']


class WorkOrderAttachmentInline(admin.TabularInline):
    """Inline для вложений задачи."""
    model = WorkOrderAttachment
    extra = 0


# =============================================================================
# WORK ORDER ADMIN
# =============================================================================

@admin.register(WorkOrder)
class WorkOrderAdmin(BaseModelAdmin):
    """Админка рабочих задач."""

    list_display = [
        'id',
        'name',
        'status_badge',
        'priority_badge',
        'category_display',
        'workstation',
        'location',
        'responsible',
        'date_start',
        'date_finish',
        'last_change',
    ]

    list_filter = ['status', 'priority', 'category', 'location']
    search_fields = ['name', 'description', 'workstation__name']
    ordering = ['-id']

    select_related_fields = ['workstation', 'location', 'responsible']

    inlines = [WorkOrderMaterialInline, WorkOrderAttachmentInline]

    fieldsets = [
        (_('Основная информация'), {
            'fields': ['name', 'description', 'category']
        }),
        (_('Оборудование и локация'), {
            'fields': ['workstation', 'location']
        }),
        (_('Исполнение'), {
            'fields': ['responsible', 'status', 'priority']
        }),
        (_('Время'), {
            'fields': ['date_start', 'date_finish', 'labor_plan_hours', 'labor_fact_hours']
        }),
        (_('Связи'), {
            'fields': ['created_from_plan'],
            'classes': ['collapse'],
        }),
    ]

    # Custom columns
    @admin.display(description=_('Статус'))
    def status_badge(self, obj):
        colors = {
            'new': '#6c757d',
            'in_progress': '#0d6efd',
            'done': '#198754',
            'failed': '#dc3545',
            'canceled': '#6c757d',
        }
        color = colors.get(obj.status, '#000')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())

    @admin.display(description=_('Приоритет'))
    def priority_badge(self, obj):
        colors = {
            'low': '#6c757d',
            'med': '#0dcaf0',
            'high': '#ffc107',
            'critical': '#dc3545',
        }
        color = colors.get(obj.priority, '#000')
        return format_html('<span style="color: {};">{}</span>', color, obj.get_priority_display())

    @admin.display(description=_('Категория'))
    def category_display(self, obj):
        return obj.get_category_display()

    def save_model(self, request, obj, form, change):
        """Сохранение с аудитом."""
        action = "изменение" if change else "создание"
        obj._change_reason = f"admin: {action} задачи обслуживания"
        obj._history_user = request.user
        super().save_model(request, obj, form, change)


# =============================================================================
# PLANNED ORDER ADMIN
# =============================================================================

@admin.register(PlannedOrder)
class PlannedOrderAdmin(BaseModelAdmin):
    """Админка плановых работ."""

    list_display = [
        'id',
        'name',
        'workstation',
        'location',
        'next_run',
        'interval_display',
        'is_active_badge',
        'responsible_default',
        'last_change',
    ]

    list_filter = ['is_active', 'interval_unit', 'category', 'location']
    search_fields = ['name', 'description', 'workstation__name']
    ordering = ['next_run']

    select_related_fields = ['workstation', 'location', 'responsible_default']

    fieldsets = [
        (_('Основная информация'), {
            'fields': ['name', 'description', 'category', 'priority']
        }),
        (_('Оборудование и локация'), {
            'fields': ['workstation', 'location']
        }),
        (_('Интервал'), {
            'fields': ['interval_value', 'interval_unit', 'next_run']
        }),
        (_('Исполнение'), {
            'fields': ['responsible_default', 'labor_plan_hours', 'is_active']
        }),
    ]

    @admin.display(description=_('Интервал'))
    def interval_display(self, obj):
        return f"{obj.interval_value} {obj.get_interval_unit_display()}"

    @admin.display(description=_('Активен'))
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">●</span> Да')
        return format_html('<span style="color: red;">●</span> Нет')

    def save_model(self, request, obj, form, change):
        """Сохранение с аудитом."""
        action = "изменение" if change else "создание"
        obj._change_reason = f"admin: {action} плановых работ"
        obj._history_user = request.user
        super().save_model(request, obj, form, change)


# =============================================================================
# FILE ADMIN
# =============================================================================

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    """Админка файлов."""

    list_display = ['id', 'file', 'uploaded_at']
    list_filter = ['uploaded_at']
    ordering = ['-uploaded_at']
    readonly_fields = ['uploaded_at']
