from django.contrib import admin
from .models import Warehouse, Material

@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ("name",)

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("name", "uom", "qty_available", "qty_reserved", "warehouse", "suitable")
    list_filter  = ("uom", "warehouse")
    search_fields = ("name", "article", "part_number", "group")
