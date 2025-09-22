from django.contrib import admin
from .models import WorkOrder, WorkOrderMaterial, PlannedOrder

class WorkOrderMaterialInline(admin.TabularInline):
    model = WorkOrderMaterial
    extra = 1

@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "priority", "workstation", "location", "responsible", "date_start", "date_finish")
    list_filter  = ("status", "priority", "category")
    search_fields = ("name", "description")
    inlines = [WorkOrderMaterialInline]


@admin.register(PlannedOrder)
class PlannedOrderAdmin(admin.ModelAdmin):
    list_display = ("name", "workstation", "location", "next_run", "interval_value", "interval_unit", "is_active")
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
