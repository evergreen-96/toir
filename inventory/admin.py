from django.contrib import admin
from django.utils.html import format_html_join
from .models import Warehouse, Material

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        "id", "name", "group", "uom", "warehouse",
        "suitable_for_display",   # ← заменили поле на метод
        "qty_available", "qty_reserved",
    )
    list_select_related = ("warehouse",)  # ← M2M сюда нельзя
    search_fields = ("name", "article", "part_number")
    list_filter = ("group", "uom", "warehouse")  # при желании можно добавить 'suitable_for'

    @admin.display(description="Подходит для оборудования")
    def suitable_for_display(self, obj: Material):
        items = obj.suitable_for.all()
        if not items:
            return "—"
        # аккуратный вывод через запятую
        return ", ".join(ws.name for ws in items)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # префетчим M2M, чтобы не было N+1
        return qs.prefetch_related("suitable_for", "warehouse")
