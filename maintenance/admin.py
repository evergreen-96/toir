from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from .models import (
    WorkOrder,
    WorkOrderMaterial,
    PlannedOrder,
    File, WorkOrderAttachment,
)


# =====================================================
# INLINE: материалы задачи
# =====================================================

class WorkOrderMaterialInline(admin.TabularInline):
    model = WorkOrderMaterial
    extra = 0


# =====================================================
# WORK ORDER
# =====================================================

@admin.register(WorkOrder)
class WorkOrderAdmin(SimpleHistoryAdmin):
    # ---------------------
    # LIST
    # ---------------------
    list_display = (
        "name",
        "status_badge",
        "priority",
        "workstation",
        "location",
        "responsible",
        "date_start",
        "date_finish",
        "last_change",
    )

    list_filter = (
        "status",
        "priority",
        "category",
    )

    search_fields = (
        "name",
        "description",
    )

    list_select_related = (
        "workstation",
        "location",
        "responsible",
    )

    ordering = ("-id",)

    inlines = [WorkOrderMaterialInline]

    # ---------------------
    # HISTORY
    # ---------------------
    history_list_display = (
        "status",
        "priority",
        "responsible",
    )

    history_list_filter = (
        "status",
        "priority",
    )

    # ---------------------
    # CUSTOM COLUMNS
    # ---------------------
    @admin.display(description="Статус")
    def status_badge(self, obj):
        color = {
            "new": "gray",
            "in_progress": "blue",
            "done": "green",
            "failed": "red",
            "canceled": "darkred",
        }.get(obj.status, "black")

        return format_html(
            '<b style="color:{}">{}</b>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description="Последнее изменение")
    def last_change(self, obj):
        h = obj.history.first()
        if not h:
            return "—"
        return format_html(
            "{}<br><small>{}</small>",
            h.history_date.strftime("%d.%m.%Y %H:%M"),
            h.history_user or "system",
        )

    # ---------------------
    # SAVE (AUDIT)
    # ---------------------
    def save_model(self, request, obj, form, change):
        if change:
            obj._change_reason = "admin: изменение задачи обслуживания"
        else:
            obj._change_reason = "admin: создание задачи обслуживания"

        obj._history_user = request.user
        super().save_model(request, obj, form, change)


# =====================================================
# PLANNED ORDER
# =====================================================

@admin.register(PlannedOrder)
class PlannedOrderAdmin(SimpleHistoryAdmin):
    # ---------------------
    # LIST
    # ---------------------
    list_display = (
        "name",
        "workstation",
        "location",
        "next_run",
        "interval_value",
        "interval_unit",
        "is_active",
        "last_change",
    )

    list_filter = (
        "interval_unit",
        "category",
        "is_active",
    )

    search_fields = (
        "name",
        "description",
    )

    list_select_related = (
        "workstation",
        "location",
        "responsible_default",
    )

    ordering = ("next_run",)

    # ---------------------
    # HISTORY
    # ---------------------
    history_list_display = (
        "interval_value",
        "interval_unit",
        "is_active",
    )

    history_list_filter = (
        "interval_unit",
        "is_active",
    )

    # ---------------------
    # CUSTOM COLUMNS
    # ---------------------
    @admin.display(description="Последнее изменение")
    def last_change(self, obj):
        h = obj.history.first()
        if not h:
            return "—"
        return format_html(
            "{}<br><small>{}</small>",
            h.history_date.strftime("%d.%m.%Y %H:%M"),
            h.history_user or "system",
        )

    # ---------------------
    # SAVE (AUDIT)
    # ---------------------
    def save_model(self, request, obj, form, change):
        if change:
            obj._change_reason = "admin: изменение плановой работы"
        else:
            obj._change_reason = "admin: создание плановой работы"

        obj._history_user = request.user
        super().save_model(request, obj, form, change)


# =====================================================
# FILE
# =====================================================

@admin.register(File)
class FileAdmin(SimpleHistoryAdmin):
    # ---------------------
    # LIST
    # ---------------------
    list_display = (
        "id",
        "file",
        "uploaded_at",
        "last_change",
    )

    ordering = ("-uploaded_at",)

    # ---------------------
    # CUSTOM COLUMNS
    # ---------------------
    @admin.display(description="Последнее изменение")
    def last_change(self, obj):
        h = obj.history.first()
        if not h:
            return "—"
        return format_html(
            "{}<br><small>{}</small>",
            h.history_date.strftime("%d.%m.%Y %H:%M"),
            h.history_user or "system",
        )

    # ---------------------
    # SAVE (AUDIT)
    # ---------------------
    def save_model(self, request, obj, form, change):
        if change:
            obj._change_reason = "admin: изменение файла"
        else:
            obj._change_reason = "admin: загрузка файла"

        obj._history_user = request.user
        super().save_model(request, obj, form, change)