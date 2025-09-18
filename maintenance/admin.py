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
    list_display = ("name", "frequency", "workstation", "location", "next_run", "is_active")
    list_filter = ("frequency", "category", "is_active")
    search_fields = ("name", "description")