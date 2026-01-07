"""
assets/admin.py

Рефакторинг с использованием базовых классов из core.admin_base.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from core.admin_base import BaseModelAdmin
from .models import Workstation


@admin.register(Workstation)
class WorkstationAdmin(BaseModelAdmin):
    """Админка оборудования."""

    # =========================
    # LIST
    # =========================
    list_display = [
        'name',
        'category_display',
        'status_display',
        'global_state_display',
        'get_location_name',
        'get_responsible_name',
        'get_warranty_status',
        'last_change',
    ]

    list_filter = ['category', 'status', 'global_state', 'location']
    search_fields = ['name', 'inventory_number', 'serial_number', 'type_name', 'model', 'manufacturer']
    ordering = ['name']

    # Оптимизация запросов
    select_related_fields = ['location', 'responsible', 'created_by']

    # =========================
    # FORM
    # =========================
    fieldsets = [
        (_('Основная информация'), {
            'fields': ['name', 'category', 'type_name', 'photo']
        }),
        (_('Детали'), {
            'fields': ['manufacturer', 'model', 'serial_number', 'inventory_number']
        }),
        (_('Состояние'), {
            'fields': ['global_state', 'status', 'location', 'responsible']
        }),
        (_('Эксплуатация'), {
            'fields': ['commissioning_date', 'warranty_until', 'description']
        }),
        (_('Системная информация'), {
            'fields': ['created_by', 'created_at', 'updated_at'],
            'classes': ['collapse'],
        }),
    ]

    readonly_fields = ['created_at', 'updated_at', 'created_by']

    # =========================
    # CUSTOM COLUMNS
    # =========================
    @admin.display(description=_('Категория'))
    def category_display(self, obj):
        return obj.get_category_display()

    @admin.display(description=_('Статус'))
    def status_display(self, obj):
        colors = {
            'prod': 'green',
            'maint': 'orange',
            'repair': 'red',
            'idle': 'gray',
            'decommissioned': 'darkgray',
        }
        color = colors.get(obj.status, 'black')
        return format_html('<span style="color: {};">{}</span>', color, obj.get_status_display())

    @admin.display(description=_('Состояние'))
    def global_state_display(self, obj):
        colors = {
            'active': 'green',
            'archived': 'gray',
        }
        color = colors.get(obj.global_state, 'black')
        return format_html('<span style="color: {};">{}</span>', color, obj.get_global_state_display())

    @admin.display(description=_('Локация'), ordering='location__name')
    def get_location_name(self, obj):
        return obj.location.name if obj.location else '—'

    @admin.display(description=_('Ответственный'))
    def get_responsible_name(self, obj):
        return str(obj.responsible) if obj.responsible else '—'

    @admin.display(description=_('Гарантия'))
    def get_warranty_status(self, obj):
        if not obj.warranty_until:
            return format_html('<span class="text-muted">—</span>')

        today = timezone.now().date()
        if obj.warranty_until >= today:
            days = (obj.warranty_until - today).days
            return format_html(
                '<span style="color: green;">✓ {} дн.</span>',
                days
            )
        else:
            return format_html('<span style="color: red;">✗ Истекла</span>')

    # =========================
    # SAVE (AUDIT)
    # =========================
    def save_model(self, request, obj, form, change):
        """Сохранение с аудитом."""
        if not change:
            obj.created_by = request.user

        action = "изменение" if change else "создание"
        obj._change_reason = f"admin: {action} оборудования"
        obj._history_user = request.user
        super().save_model(request, obj, form, change)
