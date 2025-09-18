from django.contrib import admin
from .models import HumanResource

@admin.register(HumanResource)
class HumanResourceAdmin(admin.ModelAdmin):
    list_display = ("name", "job_title")
    search_fields = ("name", "job_title")