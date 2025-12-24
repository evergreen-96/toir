from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from .models import Workstation
from core.audit import build_change_reason   # ← ВАЖНО


@admin.register(Workstation)
class WorkstationAdmin(SimpleHistoryAdmin):
    list_display = (
        "name",
        "category",
        "status",
        "location",
        "responsible",
        "created_at",
    )
    list_filter = ("category", "status", "global_state", "location")
    search_fields = (
        "name",
        "serial_number",
        "inventory_number",
        "model",
        "manufacturer",
    )

    def save_model(self, request, obj, form, change):
        """
        Логируем:
        - кто изменил
        - что это admin
        - с какого URL
        """
        obj._history_user = request.user
        obj._change_reason = build_change_reason(
            "ручное изменение оборудования"
        )
        super().save_model(request, obj, form, change)