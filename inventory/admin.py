from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin
from .models import Warehouse, Material


@admin.register(Warehouse)
class WarehouseAdmin(SimpleHistoryAdmin):
    list_display = ("id", "name", "display_location", "display_responsible", "materials_count", "last_change")
    list_display_links = ("id", "name")
    search_fields = ("name", "location__name", "responsible__name")
    list_filter = ("location",)  # УБРАЛИ stock_status отсюда
    ordering = ("name",)
    readonly_fields = ("last_change", "materials_count_display")

    fieldsets = (
        ("Основная информация", {
            "fields": ("name", "location", "responsible")
        }),
        ("Статистика", {
            "fields": ("materials_count_display",),
            "classes": ("collapse",)
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

    @admin.display(description="Материалы")
    def materials_count(self, obj):
        return obj.materials_count

    @admin.display(description="Всего материалов")
    def materials_count_display(self, obj):
        return f"{obj.materials_count} материалов"

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
        "stock_status_badge",
        "qty_available",
        "qty_reserved",
        "is_active_badge",
        "last_change"
    )
    list_display_links = ("id", "name")
    search_fields = ("name", "article", "part_number", "group", "vendor")

    # ИСПРАВЛЯЕМ list_filter - убираем stock_status, так как это свойство, а не поле
    list_filter = (
        "warehouse",
        "is_active",
        "uom",
        "group",
        # "stock_status",  # УБИРАЕМ - это свойство, а не поле модели
    )

    ordering = ("name",)
    readonly_fields = ("last_change", "qty_total_display", "stock_status_display")

    fieldsets = (
        ("Основная информация", {
            "fields": (
                "name", "group", "article", "part_number", "vendor",
                "uom", "warehouse", "is_active", "image"
            )
        }),
        ("Количественные данные", {
            "fields": ("qty_available", "qty_reserved", "qty_total_display", "min_stock_level")
        }),
        ("Статус", {
            "fields": ("stock_status_display",),
            "classes": ("collapse",)
        }),
        ("Совместимость", {
            "fields": ("suitable_for",),
            "classes": ("collapse",)
        }),
        ("Дополнительно", {
            "fields": ("notes",),
            "classes": ("collapse",)
        }),
        ("История", {
            "fields": ("last_change",),
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

    @admin.display(description="Статус запаса")
    def stock_status_display(self, obj):
        return obj.stock_status_display

    @admin.display(description="Статус")
    def stock_status_badge(self, obj):
        status_map = {
            'inactive': ('secondary', 'Неактивен'),
            'out_of_stock': ('danger', 'Отсутствует'),
            'low_stock': ('warning', 'Низкий запас'),
            'reserved': ('info', 'В резерве'),
            'in_stock': ('success', 'В наличии'),
        }
        color, text = status_map.get(obj.stock_status, ('secondary', '—'))
        return format_html('<span class="badge bg-{}">{}</span>', color, text)

    @admin.display(description="Активен")
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span class="badge bg-success">✓</span>')
        return format_html('<span class="badge bg-secondary">✗</span>')

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