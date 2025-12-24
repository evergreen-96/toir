from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import WorkOrder, WorkOrderMaterial, PlannedOrder, File


class WorkOrderMaterialInline(admin.TabularInline):
    model = WorkOrderMaterial
    extra = 1


@admin.register(WorkOrder)
class WorkOrderAdmin(SimpleHistoryAdmin):
    list_display = (
        "name",
        "status",
        "priority",
        "workstation",
        "location",
        "responsible",
        "date_start",
        "date_finish",
    )
    list_filter = ("status", "priority", "category")
    search_fields = ("name", "description")
    inlines = [WorkOrderMaterialInline]

    def save_model(self, request, obj, form, change):
        if change:
            obj._change_reason = "admin: изменение задачи обслуживания"
        else:
            obj._change_reason = "admin: создание задачи обслуживания"

        obj._history_user = request.user
        super().save_model(request, obj, form, change)


@admin.register(PlannedOrder)
class PlannedOrderAdmin(SimpleHistoryAdmin):
    list_display = (
        "name",
        "workstation",
        "location",
        "next_run",
        "interval_value",
        "interval_unit",
        "is_active",
    )
    list_filter = ("interval_unit", "category", "is_active")
    search_fields = ("name", "description")
    fields = (
        "name", "description",
        "workstation", "location",
        "responsible_default",
        "category", "priority", "labor_plan_hours",
        "start_from", "next_run",
        "interval_value", "interval_unit",
        "is_active",
    )

    def save_model(self, request, obj, form, change):
        if change:
            obj._change_reason = "admin: изменение плановой работы"
        else:
            obj._change_reason = "admin: создание плановой работы"

        obj._history_user = request.user
        super().save_model(request, obj, form, change)


@admin.register(File)
class FileAdmin(SimpleHistoryAdmin):
    list_display = ("id", "file", "uploaded_at")

    def save_model(self, request, obj, form, change):
        if change:
            obj._change_reason = "admin: изменение файла"
        else:
            obj._change_reason = "admin: загрузка файла"

        obj._history_user = request.user
        super().save_model(request, obj, form, change)
