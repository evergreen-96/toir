from django.contrib import admin
from .models import Workstation

@admin.register(Workstation)
class WorkstationAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "status", "location", "responsible", "created_at")
    list_filter = ("category", "status", "global_state", "location")
    search_fields = ("name", "serial_number", "inventory_number", "model", "manufacturer")
