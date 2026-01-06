"""
hr/admin.py

Рефакторинг с использованием базовых классов из core.
"""

from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from core.admin_base import BaseModelAdminWithActive
from .models import HumanResource


@admin.register(HumanResource)
class HumanResourceAdmin(BaseModelAdminWithActive):
    """
    Админка сотрудников.
    
    Наследует от BaseModelAdminWithActive:
    - Автоматический аудит (last_change, _history_user, _change_reason)
    - Оптимизация запросов (select_related)
    - История изменений (SimpleHistoryAdmin)
    - Бейдж активности (is_active_badge)
    """

    # =========================
    # LIST
    # =========================
    list_display = (
        "name",
        "job_title",
        "manager",
        "subordinates_count",
        "is_active_badge",
        "last_change",
    )

    list_filter = (
        "is_active",
        "job_title",
    )

    search_fields = (
        "name",
        "job_title",
    )

    ordering = ("name",)

    # Оптимизация (из BaseModelAdmin)
    select_related_fields = ['manager']

    # =========================
    # DETAIL
    # =========================
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        (_("Основная информация"), {
            "fields": (
                "name",
                "job_title",
                "manager",
                "is_active",
            )
        }),
        (_("Системная информация"), {
            "fields": (
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",),
        }),
    )

    # =========================
    # HISTORY
    # =========================
    history_list_display = (
        "job_title",
        "manager",
        "is_active",
    )

    # =========================
    # AUDIT (из BaseModelAdmin)
    # =========================
    audit_create_message = "создание сотрудника"
    audit_change_message = "изменение сотрудника"

    # =========================
    # QUERYSET
    # =========================
    def get_queryset(self, request):
        """Аннотируем количество подчинённых."""
        qs = super().get_queryset(request)
        return qs.annotate(_sub_cnt=models.Count("subordinates"))

    # =========================
    # CUSTOM COLUMNS
    # =========================
    @admin.display(description=_("Подчинённые"))
    def subordinates_count(self, obj):
        """Количество подчинённых."""
        count = getattr(obj, '_sub_cnt', 0)
        if count:
            return format_html(
                '<span class="badge bg-primary">{}</span>',
                count
            )
        return "—"
