from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from django.utils.html import format_html

from .models import Warehouse


@admin.register(Warehouse)
class WarehouseAdmin(SimpleHistoryAdmin):
    # =========================
    # LIST
    # =========================
    list_display = (
        "id",
        "name",
        "last_change",
    )

    search_fields = (
        "name",
    )

    ordering = ("name",)

    # =========================
    # HISTORY
    # =========================
    history_list_display = (
        "name",
    )

    # =========================
    # CUSTOM COLUMNS
    # =========================
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

    # =========================
    # SAVE
    # =========================
    def save_model(self, request, obj, form, change):
        if change:
            obj._change_reason = "admin: изменение склада"
        else:
            obj._change_reason = "admin: создание склада"

        obj._history_user = request.user
        super().save_model(request, obj, form, change)
