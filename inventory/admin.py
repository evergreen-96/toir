from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Warehouse, Material


@admin.register(Warehouse)
class WarehouseAdmin(SimpleHistoryAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

    def save_model(self, request, obj, form, change):
        if change:
            obj._change_reason = "admin: изменение склада"
        else:
            obj._change_reason = "admin: создание склада"

        obj._history_user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Material)
class MaterialAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "name",
        "group",
        "uom",
        "warehouse",
        "suitable_for_display",
        "qty_available",
        "qty_reserved",
    )
    list_select_related = ("warehouse",)
    search_fields = ("name", "article", "part_number")
    list_filter = ("group", "uom", "warehouse")

    @admin.display(description="Подходит для оборудования")
    def suitable_for_display(self, obj: Material):
        items = obj.suitable_for.all()
        if not items:
            return "—"
        return ", ".join(ws.name for ws in items)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("suitable_for")

    def save_model(self, request, obj, form, change):
        if change:
            obj._change_reason = "admin: изменение материала"
        else:
            obj._change_reason = "admin: создание материала"

        obj._history_user = request.user
        super().save_model(request, obj, form, change)
