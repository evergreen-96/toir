from django.contrib import admin
from .models import Location

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "level", "parent", "responsible")
    list_filter = ("level",)
    search_fields = ("name",)