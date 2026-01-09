"""
Inventory Admin - Склады и Материалы
====================================
"""

from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin

from core.admin_base import BaseModelAdminWithActive
from .models import Warehouse, Material


# =============================================================================
# WAREHOUSE ADMIN
# =============================================================================

@admin.register(Warehouse)
class WarehouseAdmin(BaseModelAdminWithActive):
    """Админка складов."""
    
    list_display = (
        "id",
        "name",
        "display_location",
        "display_responsible",
        "materials_count_badge",
        "last_change",
    )
    list_display_links = ("id", "name")
    search_fields = ("name", "location__name", "responsible__name")
    list_filter = ("location",)
    ordering = ("name",)
    readonly_fields = ("last_change", "materials_summary")
    
    fieldsets = (
        ("Основная информация", {
            "fields": ("name", "location", "responsible")
        }),
        ("Статистика", {
            "fields": ("materials_summary",),
            "classes": ("collapse",)
        }),
        ("История", {
            "fields": ("last_change",),
            "classes": ("collapse",)
        }),
    )
    
    @admin.display(description="Локация")
    def display_location(self, obj):
        return obj.location.name if obj.location else "—"
    
    @admin.display(description="Ответственный")
    def display_responsible(self, obj):
        return obj.responsible.name if obj.responsible else "—"
    
    @admin.display(description="Материалы")
    def materials_count_badge(self, obj):
        count = obj.materials_count
        if count > 0:
            return format_html(
                '<span class="badge bg-primary">{}</span>',
                count
            )
        return format_html('<span class="text-muted">0</span>')
    
    @admin.display(description="Сводка по материалам")
    def materials_summary(self, obj):
        summary = obj.get_materials_summary()
        return format_html(
            '<div class="readonly">'
            'Всего: <strong>{}</strong><br>'
            'Доступно: <strong>{}</strong><br>'
            'В резерве: <strong>{}</strong>'
            '</div>',
            summary["total_count"],
            summary["total_available"],
            summary["total_reserved"],
        )


# =============================================================================
# MATERIAL ADMIN
# =============================================================================

@admin.register(Material)
class MaterialAdmin(BaseModelAdminWithActive):
    """Админка материалов."""
    
    list_display = (
        "id",
        "name",
        "article",
        "display_warehouse",
        "stock_status_badge",
        "qty_available",
        "qty_reserved",
        "is_active_badge",
        "last_change",
    )
    list_display_links = ("id", "name")
    search_fields = ("name", "article", "part_number", "group", "vendor")
    list_filter = ("warehouse", "is_active", "uom", "group")
    ordering = ("name",)
    readonly_fields = ("last_change", "qty_total_display", "stock_status_display_readonly")
    filter_horizontal = ("suitable_for",)
    
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
        ("Статус запаса", {
            "fields": ("stock_status_display_readonly",),
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
    
    @admin.display(description="Склад")
    def display_warehouse(self, obj):
        return obj.warehouse.name if obj.warehouse else "—"
    
    @admin.display(description="Всего")
    def qty_total_display(self, obj):
        return obj.qty_total
    
    @admin.display(description="Статус запаса")
    def stock_status_display_readonly(self, obj):
        return obj.stock_status_display
    
    @admin.display(description="Статус")
    def stock_status_badge(self, obj):
        status_map = {
            "inactive": ("secondary", "Неактивен"),
            "out_of_stock": ("danger", "Отсутствует"),
            "low_stock": ("warning", "Низкий запас"),
            "reserved": ("info", "В резерве"),
            "in_stock": ("success", "В наличии"),
        }
        color, text = status_map.get(obj.stock_status, ("secondary", "—"))
        return format_html('<span class="badge bg-{}">{}</span>', color, text)
    
    @admin.display(description="Активен", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active
