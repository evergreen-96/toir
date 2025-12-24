from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from django.utils.html import format_html
from .models import Workstation
from core.audit import build_change_reason


@admin.register(Workstation)
class WorkstationAdmin(SimpleHistoryAdmin):
    # =========================
    # LIST
    # =========================
    list_display = (
        "name",
        "category",
        "status_badge",
        "location",
        "responsible",
        "global_state",
        "last_change",
    )

    list_filter = (
        "global_state",
        "category",
        "status",
        "location",
    )

    search_fields = (
        "name",
        "serial_number",
        "inventory_number",
        "model",
        "manufacturer",
    )

    list_select_related = (
        "location",
        "responsible",
    )

    ordering = ("name",)

    # =========================
    # DETAIL
    # =========================
    readonly_fields = (
        "created_at",
    )

    fieldsets = (
        ("Основная информация", {
            "fields": (
                "name",
                "category",
                "type_name",
                "manufacturer",
                "model",
                "photo",
            )
        }),
        ("Состояние", {
            "fields": (
                "global_state",
                "status",
                "location",
                "responsible",
            )
        }),
        ("Эксплуатация", {
            "fields": (
                "commissioning_date",
                "warranty_until",
                "inventory_number",
                "serial_number",
            )
        }),
        ("Описание", {
            "fields": ("description",)
        }),
        ("Служебное", {
            "fields": ("created_at",)
        }),
    )

    # =========================
    # HISTORY
    # =========================
    history_list_display = (
        "status",
        "location",
        "responsible",
    )

    history_list_filter = (
        "status",
        "global_state",
    )

    # =========================
    # SAVE
    # =========================
    def save_model(self, request, obj, form, change):
        """
        Логируем изменения из admin
        """
        obj._history_user = request.user
        obj._change_reason = build_change_reason(
            "admin: ручное изменение оборудования"
        )
        super().save_model(request, obj, form, change)

    # =========================
    # CUSTOM COLUMNS
    # =========================
    @admin.display(description="Статус")
    def status_badge(self, obj):
        color = {
            "prod": "green",
            "problem": "red",
            "maint": "orange",
            "setup": "gray",
        }.get(obj.status, "black")

        return format_html(
            '<b style="color:{}">{}</b>',
            color,
            obj.get_status_display()
        )

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
