from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin
from .models import Warehouse, Material


@admin.register(Warehouse)
class WarehouseAdmin(SimpleHistoryAdmin):
    list_display = ("id", "name", "display_location", "display_responsible", "last_change")
    list_display_links = ("id", "name")
    search_fields = ("name", "location__name", "responsible__name")
    list_filter = ("location",)
    ordering = ("name",)
    readonly_fields = ("last_change",)

    fieldsets = (
        ("Основная информация", {
            "fields": ("name", "location", "responsible")
        }),
        ("История", {
            "fields": ("last_change",),
            "classes": ("collapse",)
        }),
    )

    history_list_display = ("name", "location", "responsible")

    @admin.display(description="Локация")
    def display_location(self, obj):
        return obj.location or "—"

    @admin.display(description="Ответственный")
    def display_responsible(self, obj):
        return obj.responsible or "—"

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

    def save_model(self, request, obj, form, change):
        action = "изменение" if change else "создание"
        obj._change_reason = f"admin: {action} склада"
        obj._history_user = request.user
        super().save_model(request, obj, form, change)


@admin.register(Material)
class MaterialAdmin(SimpleHistoryAdmin):
    list_display = (
        "id",
        "name",
        "article",
        "display_warehouse",
        "qty_available",
        "qty_reserved",
        "is_active",
        "last_change"
    )
    list_display_links = ("id", "name")
    search_fields = ("name", "article", "part_number", "group", "vendor")
    list_filter = ("warehouse", "is_active", "uom", "group")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at", "last_change", "qty_total_display")

    fieldsets = (
        ("Основная информация", {
            "fields": (
                "name", "group", "article", "part_number", "vendor",
                "uom", "warehouse", "is_active", "image"
            )
        }),
        ("Количественные данные", {
            "fields": ("qty_available", "qty_reserved", "qty_total_display")
        }),
        ("Совместимость", {
            "fields": ("suitable_for",),
            "classes": ("collapse",)
        }),
        ("Даты", {
            "fields": ("created_at", "updated_at", "last_change"),
            "classes": ("collapse",)
        }),
    )

    filter_horizontal = ("suitable_for",)
    history_list_display = ("name", "article", "warehouse", "qty_available", "is_active")

    @admin.display(description="Склад")
    def display_warehouse(self, obj):
        return obj.warehouse or "—"

    @admin.display(description="Всего")
    def qty_total_display(self, obj):
        return obj.qty_total

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

    def save_model(self, request, obj, form, change):
        action = "изменение" if change else "создание"
        obj._change_reason = f"admin: {action} материала"
        obj._history_user = request.user
        super().save_model(request, obj, form, change)